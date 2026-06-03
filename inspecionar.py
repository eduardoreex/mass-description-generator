"""
Inspeciona a planilha e mostra as colunas encontradas + amostras de SKU.
Uso: python inspecionar.py input/arquivo.xlsx
"""
import sys, io, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
import openpyxl

filepath = sys.argv[1] if len(sys.argv) > 1 else "input/produtosx.xlsx"
wb = openpyxl.load_workbook(filepath, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
headers = [str(h).strip() if h is not None else "" for h in rows[0]]

SEP = "=" * 60
print(f"\n{SEP}")
print(f"  Arquivo: {filepath}   ({len(rows)-1} linhas de dados)")
print(SEP)
print(f"\n  COLUNAS ENCONTRADAS ({len(headers)} total):")
for i, h in enumerate(headers):
    if h:
        print(f"    [{i:>2}] {h}")

# Encontra coluna SKU
sku_idx = None
for candidato in ["Código (SKU)", "Codigo (SKU)", "SKU", "Código", "Codigo"]:
    for i, h in enumerate(headers):
        if h == candidato:
            sku_idx = i
            break
    if sku_idx is not None:
        break

if sku_idx is None:
    print("\n  ERRO: Nao encontrou coluna de SKU!")
    sys.exit(1)

print(f"\n  Coluna SKU usada: [{sku_idx}] '{headers[sku_idx]}'")

# Amostras
FILHO = re.compile(r"-([1-9]\d?(/\d{1,2})?|[A-Za-zÀ-ú][A-Za-zÀ-ú0-9\s/]*)$")
pais, filhos = [], []
for row in rows[1:]:
    if sku_idx >= len(row): continue
    sku = str(row[sku_idx] or "").strip()
    if not sku or sku == "None": continue
    (filhos if FILHO.search(sku) else pais).append(sku)

print(f"\n  RESULTADO DA CLASSIFICACAO:")
print(f"    Pais   : {len(pais)}")
print(f"    Filhos : {len(filhos)}")

print(f"\n  AMOSTRAS DE PAIS (primeiros 10):")
for s in pais[:10]: print(f"    {s}")

print(f"\n  AMOSTRAS DE FILHOS (primeiros 10):")
for s in filhos[:10]: print(f"    {s}")

# Verifica se parece errado
if len(pais) > len(filhos) * 3:
    print(f"\n  ATENCAO: muitos mais pais do que filhos!")
    print(f"  Isso pode indicar que o padrao de SKU filho nao esta sendo")
    print(f"  reconhecido. Veja as amostras acima.")

print(SEP)
wb.close()
