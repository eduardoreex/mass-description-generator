"""
Ponto de entrada da linha de comando.
Uso: python -m src.main --input input/produtos.xls [opcoes]
"""

import argparse
import os
import re
import sys
import io
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

# Garante UTF-8 no terminal Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from src.leitor        import ler_planilha
from src.classificador import classificar_planilha, eh_pai, eh_filho, eh_nao_processavel, eh_sem_sku
from src.baixador      import baixar_imagem
from src.gerador       import gerar_descricao
from src.validador     import validar_html
from src.escritor      import salvar_planilha
from src.relatorio     import Relatorio
from src.utils         import verde, amarelo, vermelho, cinza
from src.batch         import submeter_lote, aguardar_e_coletar, montar_htmls

_LARGURA = 62
_SEP     = "=" * _LARGURA
_SEP2    = "-" * _LARGURA

# Lock global para impressao thread-safe
_print_lock = threading.Lock()

def _p(*args, **kwargs):
    with _print_lock:
        print(*args, **kwargs)


class RateLimiter:
    """Garante no máximo `max_rpm` chamadas de API por minuto."""
    def __init__(self, max_rpm: int):
        self._intervalo = 60.0 / max_rpm   # segundos mínimos entre chamadas
        self._lock      = threading.Lock()
        self._ultimo    = 0.0

    def aguardar(self):
        with self._lock:
            agora    = time.time()
            passado  = agora - self._ultimo
            if passado < self._intervalo:
                espera = self._intervalo - passado
                time.sleep(espera)
            self._ultimo = time.time()


def main(argv=None):
    load_dotenv()
    args  = _parse_args(argv)
    api_key = os.getenv("ANTHROPIC_API_KEY", "")

    if not args.dry_run and not api_key:
        _cabecalho()
        print(vermelho("  ERRO: ANTHROPIC_API_KEY nao definida."))
        print("  Crie o arquivo .env com: ANTHROPIC_API_KEY=sk-ant-...\n")
        sys.exit(1)

    # ----------------------------------------------------------------
    # Cabecalho
    # ----------------------------------------------------------------
    _cabecalho()
    modo = amarelo("  DRY-RUN  (sem chamadas de API)") if args.dry_run else verde("  PRODUCAO")
    print(f"  Modo     : {modo}")
    print(f"  Planilha : {Path(args.input).name}")
    print(f"  Workers  : {args.workers}  (paralelo)  |  Limite: {args.rpm} req/min")
    print(f"  Inicio   : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(_SEP2)

    # ----------------------------------------------------------------
    # 1. Ler e classificar planilha
    # ----------------------------------------------------------------
    print(f"\n  Lendo planilha...")
    dados  = ler_planilha(args.input)
    linhas = classificar_planilha(dados)

    relatorio = Relatorio()
    relatorio.total_linhas = len(linhas)
    relatorio.total_filhos = sum(1 for l in linhas if eh_filho(l["categoria"]))
    relatorio.total_pais   = sum(1 for l in linhas if eh_pai(l["categoria"]))
    sem_sku                = sum(1 for l in linhas if eh_sem_sku(l["categoria"]))

    print(f"  Total    : {relatorio.total_linhas} linhas")
    print(f"  Pais     : {relatorio.total_pais}  |  Filhos: {relatorio.total_filhos}  |  Sem SKU: {sem_sku}")

    # ----------------------------------------------------------------
    # 2. Filtrar pais
    # ----------------------------------------------------------------
    pais = [l for l in linhas if eh_pai(l["categoria"])]

    if args.only_skus:
        skus_alvo = {s.strip().upper() for s in args.only_skus.split(",")}
        pais = [p for p in pais if p["sku"].upper() in skus_alvo]
        print(f"  Filtro   : --only-skus -> {len(pais)} selecionados")

    if args.limit:
        pais = pais[: args.limit]
        print(f"  Filtro   : --limit {args.limit} -> {len(pais)} pais")

    # Pre-filtra caixinhas e sem-URL antes de entrar no pool
    processaveis = []
    for p in pais:
        if eh_sem_sku(p["categoria"]):
            continue  # linha sem SKU — ignora silenciosamente
        if eh_nao_processavel(p["categoria"]):
            _p(f"  {amarelo('PULADO')} {p['sku']} — nao processavel")
            relatorio.add_pulado_nao_joia(p["sku"], p["nome"])
        elif not p["url_imagem"].strip():
            _p(f"  {amarelo('PULADO')} {p['sku']} — sem URL imagem 1")
            relatorio.add_pulado_sem_url(p["sku"], p["nome"])
        else:
            processaveis.append(p)

    total = len(processaveis)

    if args.dry_run:
        print(f"\n{_SEP}")
        print(f"  {total} produto(s) seriam processados")
        print(_SEP)
        for p in processaveis:
            print(f"  [sim] {p['sku']}  {p['nome'][:50]}")
        print(f"\n{amarelo('  [dry-run] Nenhum arquivo foi gerado.')}")
        _finalizar(relatorio, None, None, None)
        return

    # ----------------------------------------------------------------
    # Modo BATCH — sem limite de RPM, 50% mais barato
    # ----------------------------------------------------------------
    if args.batch:
        _executar_batch(
            processaveis, dados, relatorio, api_key, args, total, t_inicio=time.time()
        )
        return

    print(f"\n{_SEP}")
    print(f"  Processando {total} produto(s) — {args.workers} em paralelo")
    print(_SEP)

    # ----------------------------------------------------------------
    # 3. Processamento paralelo
    # ----------------------------------------------------------------
    descricoes     = {}
    relatorio_lock = threading.Lock()
    contador       = [0]
    t_inicio       = time.time()
    rate_limiter   = RateLimiter(max_rpm=args.rpm)

    def processar(produto):
        sku  = produto["sku"]
        nome = produto["nome"]
        cat  = produto["categoria"]
        t0   = time.time()

        _p(f"\n  > {cinza(sku)}  {nome[:45]}")

        # Download da imagem
        imagem_path, erro_download = baixar_imagem(
            url=produto["url_imagem"],
            sku=sku,
            pasta_cache="imagens",
            force_redownload=args.no_cache,
        )
        if not imagem_path:
            _p(f"    {vermelho('img FALHOU')} — {erro_download}")
            with relatorio_lock:
                relatorio.add_pulado_download(sku, nome, erro_download)
            return sku, None

        kb = Path(imagem_path).stat().st_size // 1024

        # Chamada API com retry para rate limit (429)
        html = tk_in = tk_out = None
        for tentativa in range(1, 4):           # até 3 tentativas
            rate_limiter.aguardar()             # respeita o limite de RPM
            try:
                html, tk_in, tk_out = gerar_descricao(
                    api_key=api_key,
                    nome_produto=nome,
                    categoria=cat,
                    imagem_path=imagem_path,
                    prompt_path=args.prompt,
                )
                break                           # sucesso — sai do loop
            except Exception as e:
                msg = str(e)
                if "429" in msg and tentativa < 3:
                    espera = 15 * tentativa     # 15s, 30s
                    _p(f"    {amarelo(f'rate limit — aguardando {espera}s (tentativa {tentativa}/3)')}")
                    time.sleep(espera)
                else:
                    _p(f"    {vermelho('API FALHOU')} — {msg[:120]}")
                    with relatorio_lock:
                        relatorio.add_pulado_download(sku, nome, f"API: {msg[:80]}")
                    return sku, None

        if html is None:
            return sku, None

        # Validar HTML
        valido, erros_html = validar_html(html)
        if not valido:
            _p(f"    {vermelho('HTML INVALIDO')} — {erros_html[0]}")
            with relatorio_lock:
                relatorio.add_pulado_validacao(sku, nome, erros_html)
            return sku, None

        elapsed = time.time() - t0
        with relatorio_lock:
            relatorio.add_processado(sku, nome, _extrair_chamada(html))
            relatorio.tokens_input  += tk_in
            relatorio.tokens_output += tk_out
            contador[0] += 1
            n = contador[0]

        pct = int(n * 100 / total)
        _p(f"    {verde('[OK]')}  img {kb}KB  api {elapsed:.1f}s  [{n}/{total}] {pct}%")
        return sku, html

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(processar, p): p for p in processaveis}
        for future in as_completed(futures):
            sku, html = future.result()
            if html:
                with relatorio_lock:
                    descricoes[sku] = html

    # ----------------------------------------------------------------
    # 4. Salvar resultado
    # ----------------------------------------------------------------
    print(f"\n{_SEP}")
    output_path = backup_path = alteracoes = None

    if descricoes:
        print(f"  Salvando {len(descricoes)} descricao(oes)...")
        output_path, backup_path, alteracoes = salvar_planilha(
            dados_originais=dados,
            descricoes=descricoes,
            output_dir="output",
            backup_dir="backups",
        )
        print(f"  Arquivo  : {verde(str(output_path))}")
        print(f"  Backup   : {cinza(str(backup_path))}")
        print(f"  Celulas  : {alteracoes} alterada(s)")
    else:
        print(amarelo("  Nenhuma descricao gerada — planilha nao salva."))

    _finalizar(relatorio, output_path, backup_path, t_inicio)


# ---------------------------------------------------------------------------
# Modo Batch
# ---------------------------------------------------------------------------

def _executar_batch(processaveis, dados, relatorio, api_key, args, total, t_inicio):
    print(f"\n{_SEP}")
    print(f"  MODO BATCH — {total} produto(s) enviados de uma vez")
    print(f"  Sem limite de RPM  |  50% mais barato  |  aguarda resultado")
    print(_SEP)

    # 1. Baixar todas as imagens em paralelo
    print(f"\n  Baixando {total} imagem(ns) em paralelo...")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    com_imagem = []
    for p in processaveis:
        caminho, erro = baixar_imagem(
            url=p["url_imagem"], sku=p["sku"],
            pasta_cache="imagens", force_redownload=args.no_cache,
        )
        if caminho:
            com_imagem.append({**p, "imagem_path": caminho})
            kb = Path(caminho).stat().st_size // 1024
            print(f"  [img] {p['sku']:<20} {kb}KB")
        else:
            print(f"  {vermelho('FALHOU')} {p['sku']} — {erro}")
            relatorio.add_pulado_download(p["sku"], p["nome"], erro)

    if not com_imagem:
        print(vermelho("  Nenhuma imagem baixada — abortando."))
        _finalizar(relatorio, None, None, t_inicio)
        return

    # 2. Submeter lote
    print(f"\n  Submetendo lote de {len(com_imagem)} produto(s) à API...")
    try:
        batch_id = submeter_lote(api_key, com_imagem, args.prompt)
    except Exception as e:
        print(vermelho(f"  ERRO ao submeter lote: {e}"))
        _finalizar(relatorio, None, None, t_inicio)
        return

    print(f"  Lote enviado!  ID: {cinza(batch_id)}")
    print(f"  Aguardando processamento (verifico a cada 20s)...")
    print(f"  O contador fica em 0 ate a Anthropic terminar tudo — normal.\n")
    _t_batch = time.time()

    # 3. Aguardar e coletar
    def _cb(status, concluidos, ttl):
        decorrido = int(time.time() - _t_batch)
        min_, seg  = divmod(decorrido, 60)
        if concluidos == 0:
            print(f"  processando...  {min_:02d}:{seg:02d} aguardando Anthropic")
        else:
            pct = int(concluidos * 100 / ttl) if ttl else 0
            print(f"  {verde('[OK]')} {concluidos}/{ttl} {pct}%  ({min_:02d}:{seg:02d})")

    try:
        resultados_brutos = aguardar_e_coletar(api_key, batch_id, len(com_imagem), _cb)
    except Exception as e:
        print(vermelho(f"  ERRO ao aguardar lote: {e}"))
        _finalizar(relatorio, None, None, t_inicio)
        return

    # 4. Montar e validar HTMLs
    resultados_html = montar_htmls(resultados_brutos, com_imagem)
    descricoes = {}
    for sku, (html, erros) in resultados_html.items():
        nome = next((p["nome"] for p in com_imagem if p["sku"] == sku), sku)
        if erros:
            print(f"  {vermelho('HTML INVALIDO')} {sku} — {erros[0]}")
            relatorio.add_pulado_validacao(sku, nome, erros)
        else:
            descricoes[sku] = html
            relatorio.add_processado(sku, nome, _extrair_chamada(html))

    # 5. Salvar
    print(f"\n{_SEP}")
    output_path = backup_path = None
    if descricoes:
        print(f"  Salvando {len(descricoes)} descricao(oes)...")
        output_path, backup_path, alteracoes = salvar_planilha(
            dados_originais=dados,
            descricoes=descricoes,
            output_dir="output",
            backup_dir="backups",
        )
        print(f"  Arquivo  : {verde(str(output_path))}")
        print(f"  Backup   : {cinza(str(backup_path))}")
        print(f"  Celulas  : {alteracoes} alterada(s)")
    else:
        print(amarelo("  Nenhuma descricao valida — planilha nao salva."))

    _finalizar(relatorio, output_path, backup_path, t_inicio)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finalizar(relatorio, output_path, backup_path, t_inicio):
    log_path = relatorio.salvar("output")
    duracao  = f"{time.time() - t_inicio:.0f}s" if t_inicio else "—"

    total_pulados = (
        len(relatorio.pulados_sem_url)
        + len(relatorio.pulados_download_falhou)
        + len(relatorio.pulados_validacao_falhou)
        + len(relatorio.pulados_nao_joia)
    )

    print(_SEP2)
    print(f"  {'OK':>8} : {len(relatorio.processados)}")
    print(f"  {'Pulados':>8} : {total_pulados}")
    print(f"  {'Tempo':>8} : {duracao}")
    if relatorio.tokens_input:
        custo = (relatorio.tokens_input * 3 + relatorio.tokens_output * 15) / 1_000_000
        print(f"  {'Custo':>8} : US$ {custo:.4f}  ({relatorio.tokens_input:,} / {relatorio.tokens_output:,} tokens)")
    print(f"  {'Log':>8} : {log_path}")
    print(_SEP)
    print()


def _cabecalho():
    print(f"\n{_SEP}")
    print(f"  Gerador de Descricao Reex")
    print(_SEP)


def _extrair_chamada(html: str) -> str:
    m = re.match(r"<p[^>]*>(.*?)</p>", html, re.DOTALL)
    return m.group(1).strip() if m else html[:80]


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Gerador de Descricao Reex — descricoes automaticas via IA",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  python -m src.main --input input/produtos.xls --dry-run
  python -m src.main --input input/produtos.xls --limit 5
  python -m src.main --input input/produtos.xls --workers 6
  python -m src.main --input input/produtos.xls --only-skus SKU001,SKU002
        """,
    )

    parser.add_argument("--input",     required=True,
        help="Planilha exportada do Tiny (.xls ou .xlsx)")
    parser.add_argument("--dry-run",   action="store_true",
        help="Simula sem chamar a API")
    parser.add_argument("--limit",     type=int, metavar="N",
        help="Processa so os primeiros N produtos pai")
    parser.add_argument("--only-skus", metavar="SKU1,SKU2,...",
        help="Processa so esses SKUs (virgula separados)")
    parser.add_argument("--prompt",    default="PROMPT.md", metavar="PATH",
        help="Arquivo de prompt (padrao: PROMPT.md)")
    parser.add_argument("--no-cache",  action="store_true",
        help="Forca novo download das imagens")
    parser.add_argument("--batch",     action="store_true",
        help="Modo batch: envia tudo de uma vez, sem limite de RPM, 50pct mais barato")
    parser.add_argument("--workers",   type=int, default=4, metavar="N",
        help="Quantos produtos processar em paralelo (padrao: 4)")
    parser.add_argument("--rpm",       type=int, default=5, metavar="N",
        help="Limite de chamadas de API por minuto (padrao: 5 — maximo da conta basica Anthropic)")

    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
