"""
Classifica cada linha da planilha como:
  - sem_sku            → linha sem SKU preenchido (ignorar silenciosamente)
  - filho              → variação de um pai (ignorar)
  - caixinha_acessorio → embalagem/display (pular com aviso)
  - pai_joia           → processar (semijoia padrão)
  - pai_prata_925      → processar (garantia especial)
  - pai_oculos         → processar (garantia especial)
  - pai_relogio        → processar (garantia especial)

Detecção de filho usa DUAS estratégias (em ordem):
  1. Coluna "Código do pai" preenchida → filho com certeza (nativo do Tiny)
  2. Regex no sufixo do SKU → fallback para exports sem essa coluna
"""

import re
from config import PALAVRAS_NAOIJOIA

# Regex para detectar SKU filho pelo sufixo.
# Aceita: -1 a -99, -36/38, -Dourado, -P, -GG, -Aro 12
# Rejeita: -001, -789 (numeração sequencial de pais)
_REGEX_FILHO = re.compile(
    r"-([1-9]\d?(/\d{1,2})?|[A-Za-zÀ-ú][A-Za-zÀ-ú0-9\s/]*)$"
)

_PALAVRAS_PRATA  = ["prata 925", " ap90", "925", "prata de lei"]
_PREFIXOS_OCULOS = ["óculo", "oculos", "óculos"]
_PALAVRAS_RELOGIO = ["relógio", "relogio", "watch"]


def classificar_linha(sku: str, nome: str, codigo_pai: str = "") -> str:
    """
    Retorna a categoria da linha.

    Args:
        sku:        coluna "Código (SKU)"
        nome:       coluna "Descrição"
        codigo_pai: coluna "Código do pai" (opcional — vazio para pais)
    """
    sku        = str(sku).strip()
    nome       = str(nome).strip()
    codigo_pai = str(codigo_pai).strip()

    # 0. SKU vazio → linha sem produto (ignora)
    if not sku or sku.lower() in ("none", "-"):
        return "sem_sku"

    # 1. "Código do pai" preenchido → é filho com certeza
    if codigo_pai and codigo_pai.lower() not in ("none", "0", ""):
        return "filho"

    # 2. Regex no sufixo do SKU → segundo critério de filho
    if _REGEX_FILHO.search(sku):
        return "filho"

    # 3. Caixinha / acessório
    nome_lower = nome.lower()
    for palavra in PALAVRAS_NAOIJOIA:
        if palavra in nome_lower:
            return "caixinha_acessorio"

    # 4. Detecta categoria do pai
    if _contem_alguma(nome_lower, _PALAVRAS_RELOGIO):
        return "pai_relogio"
    if _contem_alguma(nome_lower, _PREFIXOS_OCULOS):
        return "pai_oculos"
    if _contem_alguma(nome_lower, _PALAVRAS_PRATA):
        return "pai_prata_925"

    return "pai_joia"


def eh_pai(categoria: str) -> bool:
    return categoria.startswith("pai_")


def eh_filho(categoria: str) -> bool:
    return categoria == "filho"


def eh_nao_processavel(categoria: str) -> bool:
    return categoria == "caixinha_acessorio"


def eh_sem_sku(categoria: str) -> bool:
    return categoria == "sem_sku"


def classificar_planilha(dados: dict) -> list[dict]:
    ci       = dados["col_index"]
    col_sku  = ci["Código (SKU)"]
    col_nome = ci["Descrição"]
    col_url  = ci["URL imagem 1"]
    col_desc = ci["Descrição complementar"]
    # "Código do pai" é opcional — nem todas as versões do Tiny exportam
    col_pai  = ci.get("Código do pai", None)

    resultado = []
    for i, row in enumerate(dados["rows"]):
        def cel(idx):
            return row[idx] if idx is not None and idx < len(row) else ""

        sku        = cel(col_sku)
        nome       = cel(col_nome)
        url        = cel(col_url)
        desc       = cel(col_desc)
        codigo_pai = cel(col_pai) if col_pai is not None else ""

        categoria = classificar_linha(sku, nome, codigo_pai)

        resultado.append({
            "linha_index":            i,
            "sku":                    str(sku).strip(),
            "nome":                   str(nome).strip(),
            "url_imagem":             str(url).strip(),
            "descricao_complementar": str(desc).strip(),
            "categoria":              categoria,
        })

    return resultado


def _contem_alguma(texto: str, lista: list[str]) -> bool:
    return any(p in texto for p in lista)
