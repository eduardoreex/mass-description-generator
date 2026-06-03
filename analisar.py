"""
Analisa a planilha e mostra o que pode/nao pode ser processado.
Uso: python analisar.py input/arquivo.xlsx
"""
import sys
import re
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import openpyxl

if len(sys.argv) < 2:
    print("Uso: python analisar.py input/arquivo.xlsx")
    sys.exit(1)

filepath = sys.argv[1]
FILHO = re.compile(r"-([1-9]\d?(/\d{1,2})?|[A-Za-zÀ-ú][A-Za-zÀ-ú0-9\s/]*)$")

wb = openpyxl.load_workbook(filepath, read_only=True)
ws = wb.active
rows = list(ws.iter_rows(values_only=True))
headers = [str(h).strip() if h is not None else "" for h in rows[0]]

def col(nome):
    for i, h in enumerate(headers):
        if nome.lower() in h.lower():
            return i
    return None

sku_idx  = col("SKU")
url_idx  = col("URL imagem 1")
desc_idx = col("complementar")

if None in (sku_idx, url_idx, desc_idx):
    print("Colunas nao encontradas. Colunas disponiveis:")
    for i, h in enumerate(headers):
        if h:
            print(f"  {i:>3}: {h}")
    sys.exit(1)

pais_com_url_sem_desc  = 0   # vai gerar
pais_com_url_com_desc  = 0   # vai atualizar
pais_sem_url_sem_desc  = 0   # impossivel — precisa de foto
pais_sem_url_com_desc  = 0   # ja tem, mas sem foto pra atualizar
filhos                 = 0

for row in rows[1:]:
    if len(row) <= max(sku_idx, url_idx, desc_idx):
        continue
    sku  = str(row[sku_idx]  or "").strip()
    url  = str(row[url_idx]  or "").strip()
    desc = str(row[desc_idx] or "").strip()

    if FILHO.search(sku):
        filhos += 1
        continue

    tem_url  = bool(url and url.startswith("http"))
    tem_desc = bool(desc and len(desc) > 20)

    if tem_url and not tem_desc:
        pais_com_url_sem_desc += 1
    elif tem_url and tem_desc:
        pais_com_url_com_desc += 1
    elif not tem_url and not tem_desc:
        pais_sem_url_sem_desc += 1
    else:
        pais_sem_url_com_desc += 1

wb.close()

SEP = "=" * 55
print(f"\n{SEP}")
print(f"  Analise: {filepath}")
print(SEP)
print(f"  Total de linhas           : {len(rows)-1}")
print(f"  Filhos (ignorados)        : {filhos}")
print()
print(f"  PAIS COM IMAGEM:")
print(f"    Sem descricao ainda     : {pais_com_url_sem_desc}  <- NOVOS (vai gerar)")
print(f"    Ja tem descricao        : {pais_com_url_com_desc}  <- ATUALIZA com novo template")
print()
print(f"  PAIS SEM IMAGEM:")
print(f"    Sem descricao           : {pais_sem_url_sem_desc}  <- nao processa (precisa de foto)")
print(f"    Ja tem descricao        : {pais_sem_url_com_desc}  <- nao processa (precisa de foto)")
print()
total_processavel = pais_com_url_sem_desc + pais_com_url_com_desc
print(f"  TOTAL A PROCESSAR         : {total_processavel}")
print(f"  Custo estimado            : US$ {total_processavel * 0.012:.2f}")
print(SEP)
print()
