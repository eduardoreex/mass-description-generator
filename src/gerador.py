"""
Chama a API Anthropic para gerar a chamada de venda,
depois monta o HTML completo usando o template fixo do config.py.
A IA gera APENAS o texto criativo — o Python monta o HTML.
"""

import base64
import io
import re
from pathlib import Path

import anthropic
from PIL import Image

from config import (
    MODELO_API,
    MAX_TOKENS_OUTPUT,
    TEMPLATE_HTML,
    GARANTIA_POR_CATEGORIA,
    LINK_POLITICA,
    LINK_VIDEO,
)
from src.utils import mime_de_extensao


def gerar_descricao(
    api_key: str,
    nome_produto: str,
    categoria: str,
    imagem_path: str,
    prompt_path: str = "PROMPT.md",
) -> tuple[str, int, int]:
    """
    Gera o HTML completo para um produto.

    Returns:
        (html_completo, tokens_input, tokens_output)
    """
    prompt_instrucoes = _carregar_prompt(prompt_path)

    mensagem_usuario = (
        f"Produto: {nome_produto}\n"
        f"Categoria: {_label_categoria(categoria)}\n\n"
        f"{prompt_instrucoes}"
    )

    imagem_b64, media_type = _codificar_imagem_comprimida(imagem_path)

    client = anthropic.Anthropic(api_key=api_key)

    resposta = client.messages.create(
        model=MODELO_API,
        max_tokens=MAX_TOKENS_OUTPUT,
        messages=[
            {
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
                    {
                        "type": "text",
                        "text": mensagem_usuario,
                    },
                ],
            }
        ],
    )

    chamada_bruta = resposta.content[0].text.strip()

    # Remove tags HTML acidentais (a IA às vezes adiciona)
    chamada_limpa = re.sub(r"<[^>]+>", "", chamada_bruta).strip()

    html = _montar_html(chamada_limpa, categoria)

    tokens_in  = resposta.usage.input_tokens
    tokens_out = resposta.usage.output_tokens

    return html, tokens_in, tokens_out


def montar_html_de_chamada(chamada: str, categoria: str) -> str:
    """Exposto para testes: monta o HTML a partir de uma chamada já gerada."""
    return _montar_html(chamada, categoria)


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------

def _carregar_prompt(prompt_path: str) -> str:
    path = Path(prompt_path)
    if not path.exists():
        raise FileNotFoundError(
            f"Arquivo de prompt não encontrado: {prompt_path}\n"
            "Certifique-se de que PROMPT.md existe na raiz do projeto."
        )
    return path.read_text(encoding="utf-8")


def _codificar_imagem_comprimida(
    imagem_path: str,
    max_lado: int = 900,
    qualidade: int = 82,
) -> tuple[str, str]:
    """
    Redimensiona para max_lado px e comprime para JPEG antes de enviar à API.
    O arquivo original em imagens/ NÃO é alterado — só o que vai pro servidor.
    Retorna (base64, media_type).
    """
    with Image.open(imagem_path) as img:
        img = img.convert("RGB")
        img.thumbnail((max_lado, max_lado), Image.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=qualidade, optimize=True)
        dados = buf.getvalue()

    return base64.standard_b64encode(dados).decode("utf-8"), "image/jpeg"


def _montar_html(chamada: str, categoria: str) -> str:
    garantia = GARANTIA_POR_CATEGORIA.get(categoria, GARANTIA_POR_CATEGORIA["pai_joia"])
    return TEMPLATE_HTML.format(
        chamada=chamada,
        garantia=garantia,
        link_politica=LINK_POLITICA,
        link_video=LINK_VIDEO,
    )


def _label_categoria(categoria: str) -> str:
    mapa = {
        "pai_joia":      "Semijoia (banho ouro 18k, antialérgica)",
        "pai_prata_925": "Prata 925 (prata de lei, antialérgica)",
        "pai_oculos":    "Óculos (proteção UV 400)",
        "pai_relogio":   "Relógio",
    }
    return mapa.get(categoria, "Semijoia")
