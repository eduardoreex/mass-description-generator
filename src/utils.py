"""Helpers gerais usados por múltiplos módulos."""

import sys
from pathlib import Path


def verde(texto: str) -> str:
    return f"\033[92m{texto}\033[0m" if _suporta_cor() else texto


def amarelo(texto: str) -> str:
    return f"\033[93m{texto}\033[0m" if _suporta_cor() else texto


def vermelho(texto: str) -> str:
    return f"\033[91m{texto}\033[0m" if _suporta_cor() else texto


def cinza(texto: str) -> str:
    return f"\033[90m{texto}\033[0m" if _suporta_cor() else texto


def _suporta_cor() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def normalizar_sku(sku: str) -> str:
    return str(sku).strip().upper()


def extensao_de_content_type(content_type: str) -> str:
    mapa = {
        "image/jpeg": ".jpg",
        "image/jpg":  ".jpg",
        "image/png":  ".png",
        "image/gif":  ".gif",
        "image/webp": ".webp",
    }
    ct = content_type.split(";")[0].strip().lower()
    return mapa.get(ct, ".jpg")


def mime_de_extensao(caminho: str) -> str:
    ext = Path(caminho).suffix.lower()
    mapa = {
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
        ".gif":  "image/gif",
        ".webp": "image/webp",
    }
    return mapa.get(ext, "image/jpeg")
