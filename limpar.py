"""
Utilitario de limpeza — limpar.py
Uso: python limpar.py [opcao]

Opcoes:
  python limpar.py imagens     -> apaga cache de imagens (re-baixa na proxima vez)
  python limpar.py logs        -> apaga logs de execucao antigos
  python limpar.py output      -> apaga planilhas _FINAL.xlsx antigas
  python limpar.py backups     -> apaga backups antigos
  python limpar.py tudo        -> apaga tudo acima (nao toca em input/)
  python limpar.py             -> mostra o que tem em cada pasta (sem apagar nada)
"""

import sys
import os
from pathlib import Path


def tamanho_humano(bytes_: int) -> str:
    for unidade in ("B", "KB", "MB", "GB"):
        if bytes_ < 1024:
            return f"{bytes_:.0f} {unidade}"
        bytes_ /= 1024
    return f"{bytes_:.1f} GB"


def listar_pasta(pasta: str, padrao: str = "*") -> list[Path]:
    return sorted(Path(pasta).glob(padrao)) if Path(pasta).exists() else []


def mostrar_status():
    pastas = {
        "imagens":  ("imagens",  "*"),
        "output":   ("output",   "*"),
        "backups":  ("backups",  "*"),
        "input":    ("input",    "*"),
    }

    print("\n  Status das pastas\n  " + "-" * 40)
    for nome, (pasta, padrao) in pastas.items():
        arquivos = listar_pasta(pasta, padrao)
        total = sum(f.stat().st_size for f in arquivos if f.is_file())
        print(f"  {nome:<10} {len(arquivos):>4} arquivo(s)   {tamanho_humano(total):>8}")
        for f in arquivos[:5]:
            print(f"             • {f.name}")
        if len(arquivos) > 5:
            print(f"             ... e mais {len(arquivos)-5}")
    print()


def apagar(pasta: str, padrao: str = "*", descricao: str = "") -> int:
    arquivos = listar_pasta(pasta, padrao)
    arquivos = [f for f in arquivos if f.is_file()]
    if not arquivos:
        print(f"  {pasta}/  — vazia, nada a apagar")
        return 0

    print(f"\n  Apagando {len(arquivos)} arquivo(s) de {pasta}/ ({descricao})...")
    total_bytes = 0
    for f in arquivos:
        total_bytes += f.stat().st_size
        f.unlink()
        print(f"    - {f.name}")
    print(f"  Liberado: {tamanho_humano(total_bytes)}")
    return len(arquivos)


def confirmar(mensagem: str) -> bool:
    resp = input(f"  {mensagem} [s/N]: ").strip().lower()
    return resp in ("s", "sim", "y", "yes")


# ---------------------------------------------------------------------------

opcao = sys.argv[1].lower() if len(sys.argv) > 1 else ""

print("\n" + "=" * 50)
print("  Gerador de Descricao Reex — Limpeza")
print("=" * 50)

if not opcao:
    mostrar_status()
    print("  Use: python limpar.py [imagens|logs|output|backups|tudo]")

elif opcao == "imagens":
    print("\n  As imagens serao re-baixadas na proxima execucao.")
    if confirmar("Confirma apagar cache de imagens?"):
        apagar("imagens", "*", "cache de fotos")

elif opcao == "logs":
    if confirmar("Confirma apagar logs de execucao?"):
        apagar("output", "log_execucao_*.txt", "logs")

elif opcao == "output":
    print("\n  ATENCAO: so apague depois de importar as planilhas no Tiny!")
    if confirmar("Confirma apagar planilhas _FINAL.xlsx e logs de output/?"):
        apagar("output", "*", "resultados gerados")

elif opcao == "backups":
    print("\n  ATENCAO: so apague depois de confirmar que tudo funcionou.")
    if confirmar("Confirma apagar backups?"):
        apagar("backups", "*", "backups dos originais")

elif opcao == "tudo":
    print("\n  Vai apagar: imagens/, output/, backups/")
    print("  NAO apaga: input/ (suas planilhas originais)")
    if confirmar("Confirma limpeza completa?"):
        apagar("imagens", "*", "cache de fotos")
        apagar("output",  "*", "resultados")
        apagar("backups", "*", "backups")
        print("\n  Limpeza concluida!")

else:
    print(f"\n  Opcao desconhecida: '{opcao}'")
    print("  Use: imagens | logs | output | backups | tudo")

print()
