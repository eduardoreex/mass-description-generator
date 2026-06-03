"""
Modo Batch — envia todos os produtos de uma vez para a API Anthropic.
Sem limite de RPM, 50% mais barato, processa em paralelo nos servidores.
Tempo estimado: 5-15 min para 100 produtos, 30-60 min para 1000.
"""

import re
import time
import io
import base64

import anthropic
from PIL import Image

from config import MODELO_API, MAX_TOKENS_OUTPUT
from src.gerador import _carregar_prompt, _montar_html, _label_categoria
from src.validador import validar_html


def submeter_lote(
    api_key: str,
    produtos: list[dict],           # [{sku, nome, categoria, imagem_path}, ...]
    prompt_path: str = "PROMPT.md",
) -> str:
    """
    Envia todos os produtos de uma vez.
    Retorna o batch_id para acompanhamento.
    """
    prompt_text = _carregar_prompt(prompt_path)
    client = anthropic.Anthropic(api_key=api_key)

    requests = []
    for p in produtos:
        imagem_b64, media_type = _comprimir(p["imagem_path"])
        mensagem = (
            f"Produto: {p['nome']}\n"
            f"Categoria: {_label_categoria(p['categoria'])}\n\n"
            f"{prompt_text}"
        )
        requests.append({
            "custom_id": p["sku"],
            "params": {
                "model": MODELO_API,
                "max_tokens": MAX_TOKENS_OUTPUT,
                "messages": [{
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type":       "base64",
                                "media_type": media_type,
                                "data":       imagem_b64,
                            },
                        },
                        {"type": "text", "text": mensagem},
                    ],
                }],
            },
        })

    batch = client.messages.batches.create(requests=requests)
    return batch.id


def aguardar_e_coletar(
    api_key: str,
    batch_id: str,
    total: int,
    callback,           # callback(status, concluidos, total)
    intervalo: int = 20,
) -> dict[str, str]:
    """
    Aguarda o lote terminar e devolve {sku: chamada_de_venda}.
    """
    client = anthropic.Anthropic(api_key=api_key)

    while True:
        batch = client.messages.batches.retrieve(batch_id)
        c = batch.request_counts
        concluidos = c.succeeded + c.errored + c.canceled + c.expired
        callback(batch.processing_status, concluidos, total)

        if batch.processing_status == "ended":
            break
        time.sleep(intervalo)

    resultados = {}
    for result in client.messages.batches.results(batch_id):
        if result.result.type == "succeeded":
            texto = result.result.message.content[0].text.strip()
            # Remove tags HTML acidentais
            texto = re.sub(r"<[^>]+>", "", texto).strip()
            resultados[result.custom_id] = texto

    return resultados


def montar_htmls(
    resultados_brutos: dict[str, str],
    produtos: list[dict],
) -> dict[str, tuple[str, list]]:
    """
    Para cada SKU com resultado, monta o HTML e valida.
    Retorna {sku: (html, erros)} — erros vazio = OK.
    """
    cat_por_sku = {p["sku"]: p["categoria"] for p in produtos}
    saida = {}
    for sku, chamada in resultados_brutos.items():
        cat  = cat_por_sku.get(sku, "pai_joia")
        html = _montar_html(chamada, cat)
        _, erros = validar_html(html)
        saida[sku] = (html, erros)
    return saida


# ---------------------------------------------------------------------------
# Helper interno
# ---------------------------------------------------------------------------

def _comprimir(imagem_path: str, max_lado: int = 900, qualidade: int = 82):
    with Image.open(imagem_path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_lado, max_lado), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=qualidade, optimize=True)
        dados = buf.getvalue()
    return base64.standard_b64encode(dados).decode("utf-8"), "image/jpeg"
