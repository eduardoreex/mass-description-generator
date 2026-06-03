"""
Valida o HTML gerado antes de gravar na planilha.
Regra R7: se falhar qualquer verificação, não grava e marca para retry.
"""

import re


def validar_html(html: str) -> tuple[bool, list[str]]:
    """
    Verifica se o HTML atende a todas as regras do template.

    Returns:
        (True, [])          → HTML válido, pode gravar
        (False, [erros...]) → HTML inválido, NÃO gravar
    """
    erros = []

    # 6 <p> abertas e 6 </p>
    p_open  = len(re.findall(r"<p[^>]*>", html, re.IGNORECASE))
    p_close = len(re.findall(r"</p>",    html, re.IGNORECASE))
    if p_open != 6 or p_close != 6:
        erros.append(f"Esperado 6 <p>…</p>, encontrado {p_open} abertas / {p_close} fechadas")

    # 2 <a ...> e 2 </a>  (style pode vir antes do href)
    a_open  = len(re.findall(r"<a\b",  html, re.IGNORECASE))
    a_close = len(re.findall(r"</a>",  html, re.IGNORECASE))
    if a_open != 2 or a_close != 2:
        erros.append(f"Esperado 2 <a>…</a>, encontrado {a_open} abertas / {a_close} fechadas")

    # 3 <strong> e 3 </strong>
    s_open  = len(re.findall(r"<strong[^>]*>", html, re.IGNORECASE))
    s_close = len(re.findall(r"</strong>",      html, re.IGNORECASE))
    if s_open != 3 or s_close != 3:
        erros.append(f"Esperado 3 <strong>…</strong>, encontrado {s_open} abertas / {s_close} fechadas")

    # Contém ✅
    if "✅" not in html:
        erros.append("Falta o emoji ✅ no HTML")

    # Contém a cor #a1012b
    if "#a1012b" not in html:
        erros.append("Falta a cor #a1012b no HTML")

    # Chamada de venda (primeiro <p>, com ou sem atributos style) tem entre 200 e 800 chars
    match = re.match(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    if match:
        chamada = match.group(1).strip()
        tamanho = len(chamada)
        if tamanho < 200:
            erros.append(
                f"Chamada de venda muito curta: {tamanho} chars (mínimo 200). "
                f"Trecho: \"{chamada[:80]}...\""
            )
        elif tamanho > 800:
            erros.append(
                f"Chamada de venda muito longa: {tamanho} chars (máximo 800)"
            )
    else:
        erros.append("Não foi possível extrair o primeiro <p> para verificar a chamada de venda")

    return len(erros) == 0, erros
