import openpyxl, glob, os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

files = glob.glob("output/*.xlsx")
if not files:
    print("Nenhum arquivo em output/")
    exit()
latest = max(files, key=os.path.getmtime)
print(f"Arquivo: {latest}\n")

wb = openpyxl.load_workbook(latest, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
headers = [str(h) if h else "" for h in rows[0]]

sku_idx  = next((i for i, h in enumerate(headers) if "SKU" in h), None)
nome_idx = next((i for i, h in enumerate(headers) if h.strip() in ("Descricao", "Descrição")), None)
desc_idx = next((i for i, h in enumerate(headers) if "complementar" in h.lower()), None)

print(f"Total linhas de dados : {len(rows)-1}")
print(f"Coluna desc complementar: idx={desc_idx} nome='{headers[desc_idx]}'\n")

gerados = 0
for row in rows[1:]:
    desc = str(row[desc_idx] or "").strip() if desc_idx is not None else ""
    if desc and len(desc) > 50:
        sku  = str(row[sku_idx]  or "") if sku_idx  is not None else "?"
        nome = str(row[nome_idx] or "") if nome_idx is not None else "?"
        gerados += 1
        print(f"{'='*60}")
        print(f"SKU : {sku}")
        print(f"Nome: {nome}")
        print(f"{'='*60}")
        print(desc[:800])
        print()

print(f"\n>>> {gerados} produto(s) com descricao gerada no arquivo <<<")
wb.close()
