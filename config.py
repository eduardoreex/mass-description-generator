"""
Constantes globais do projeto.
Edite aqui para mudar links, cor, garantias e modelo de IA.
"""

# --- Links da loja ---
LINK_POLITICA = "https://marciacastrosemijoias.com.br/trocas-e-devolucoes/"
LINK_VIDEO    = "https://www.youtube.com/shorts/miytSHjTjI0"

# --- Identidade visual ---
COR_DESTAQUE = "#a1012b"

# --- Textos de garantia por categoria (vem após ✅ no template) ---
GARANTIA_POR_CATEGORIA = {
    "pai_joia":      "Garantia de excelência de 1 ano e antialérgica.",
    "pai_oculos":    "Proteção UV 400, armação leve e antialérgica — 1 ano de garantia.",
    "pai_prata_925": "Prata 925 autêntica, antialérgica — 1 ano de garantia.",
    "pai_relogio":   "Garantia de 1 ano com o fabricante.",
}

# --- Template HTML fixo — formato exato usado pela loja ---
# Estrutura: 6 <p style>, 2 <a href>, 3 <strong>, ✅, #a1012b
_A_STYLE = 'style="color: #a1012b; text-decoration: underline; font-weight: 600;"'
_P = 'style="font-size: 16px; line-height: 1.6;"'

TEMPLATE_HTML = (
    f'<p {_P}>{{chamada}}</p>\n'
    f'<p {_P}><strong>✅ {{garantia}}</strong></p>\n'
    f'<p {_P}><strong>Parcele em até 12x sem juros!</strong></p>\n'
    f'<p {_P}>Consulte nossa <a {_A_STYLE} href="{{link_politica}}" target="_blank" rel="noopener">'
    f'Política de Troca</a> e compre com total tranquilidade.</p>\n'
    f'<p {_P}>Não sabe como comprar ou usar seu cupom de desconto? Assista ao nosso '
    f'<a {_A_STYLE} href="{{link_video}}" target="_blank" rel="noopener">'
    f'vídeo tutorial completo</a> e aproveite!</p>\n'
    f'<p {_P}><strong>Não deixe essa peça escapar — garanta a sua hoje!</strong></p>'
)

# --- Palavras que identificam itens não-joia (pular + log) ---
PALAVRAS_NAOIJOIA = [
    "caixinha", "embalagem", "estojo de presente", "estojo presente",
    "porta-joia", "porta joia", "portajoia", "display", "suporte",
    "kit embalagem", "sacola", "tag", "etiqueta",
]

# --- API Anthropic ---
MODELO_API = "claude-sonnet-4-6"
MAX_TOKENS_OUTPUT = 1024

# --- Download de imagens ---
TIMEOUT_DOWNLOAD_SEGUNDOS = 20
MAX_TENTATIVAS_DOWNLOAD = 2
TAMANHO_MINIMO_IMAGEM_BYTES = 1024  # 1 KB — imagem menor que isso é inválida
