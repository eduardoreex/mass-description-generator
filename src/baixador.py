"""
Baixa imagens de produtos com cache local e retry automático.
Regras R3 e R4 do plano:
  - Pais sem URL → pular (tratado pelo chamador)
  - Falha no download → pular + registrar motivo
"""

import time
import requests
from pathlib import Path

from config import (
    TIMEOUT_DOWNLOAD_SEGUNDOS,
    MAX_TENTATIVAS_DOWNLOAD,
    TAMANHO_MINIMO_IMAGEM_BYTES,
)
from src.utils import extensao_de_content_type


def baixar_imagem(
    url: str,
    sku: str,
    pasta_cache: str,
    force_redownload: bool = False,
) -> tuple[str | None, str | None]:
    """
    Baixa a imagem e salva em pasta_cache/{sku}.ext.
    Se já estiver em cache e for válida, reutiliza.

    Retorna:
        (caminho_arquivo, None)    → sucesso
        (None, mensagem_de_erro)   → falha
    """
    pasta = Path(pasta_cache)
    pasta.mkdir(parents=True, exist_ok=True)

    # Verifica cache
    if not force_redownload:
        cached = _buscar_em_cache(pasta, sku)
        if cached:
            return str(cached), None

    if not url or not url.strip().startswith("http"):
        return None, "URL inválida ou vazia"

    # Tentativas com backoff exponencial
    ultimo_erro = "Erro desconhecido"
    for tentativa in range(MAX_TENTATIVAS_DOWNLOAD + 1):
        if tentativa > 0:
            time.sleep(2 ** (tentativa - 1))

        caminho, erro = _tentar_download(url, sku, pasta)
        if caminho:
            return caminho, None
        ultimo_erro = erro

    return None, f"Falhou após {MAX_TENTATIVAS_DOWNLOAD + 1} tentativas: {ultimo_erro}"


# ---------------------------------------------------------------------------
# Internos
# ---------------------------------------------------------------------------

def _buscar_em_cache(pasta: Path, sku: str) -> Path | None:
    for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        candidato = pasta / f"{sku}{ext}"
        if candidato.exists() and candidato.stat().st_size >= TAMANHO_MINIMO_IMAGEM_BYTES:
            return candidato
    return None


def _tentar_download(url: str, sku: str, pasta: Path) -> tuple[str | None, str]:
    try:
        resp = requests.get(
            url,
            timeout=TIMEOUT_DOWNLOAD_SEGUNDOS,
            stream=True,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()

        content_type = resp.headers.get("content-type", "image/jpeg")
        if "text/html" in content_type or "text/plain" in content_type:
            return None, f"Servidor retornou HTML ao invés de imagem (URL possivelmente errada)"

        ext = extensao_de_content_type(content_type)

        # Se a extensão vier na URL, prefere a da URL
        from urllib.parse import urlparse
        url_path = urlparse(url).path
        url_ext = Path(url_path).suffix.lower()
        if url_ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
            ext = url_ext if url_ext != ".jpeg" else ".jpg"

        destino = pasta / f"{sku}{ext}"

        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)

        tamanho = destino.stat().st_size
        if tamanho < TAMANHO_MINIMO_IMAGEM_BYTES:
            destino.unlink(missing_ok=True)
            return None, f"Imagem muito pequena ({tamanho} bytes — mínimo {TAMANHO_MINIMO_IMAGEM_BYTES})"

        return str(destino), ""

    except requests.exceptions.Timeout:
        return None, f"Timeout após {TIMEOUT_DOWNLOAD_SEGUNDOS}s"
    except requests.exceptions.HTTPError as e:
        return None, f"HTTP {e.response.status_code}: {e.response.reason}"
    except requests.exceptions.ConnectionError:
        return None, "Erro de conexão"
    except Exception as e:
        return None, str(e)
