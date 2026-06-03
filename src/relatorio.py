"""
Gera o log_execucao_*.txt ao final de cada execução.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Relatorio:
    inicio: datetime = field(default_factory=datetime.now)

    # Contadores gerais
    total_linhas:   int = 0
    total_pais:     int = 0
    total_filhos:   int = 0

    # Resultados
    processados:            list = field(default_factory=list)  # (sku, nome, chamada_80)
    pulados_sem_url:        list = field(default_factory=list)  # (sku, nome)
    pulados_download_falhou: list = field(default_factory=list) # (sku, nome, motivo)
    pulados_validacao_falhou: list = field(default_factory=list) # (sku, nome, erros)
    pulados_nao_joia:       list = field(default_factory=list)  # (sku, nome)
    pulados_ja_tem_desc:    list = field(default_factory=list)  # (sku, nome)  ← não sobrescreve

    # Tokens e custo
    tokens_input:  int = 0
    tokens_output: int = 0

    def add_processado(self, sku: str, nome: str, chamada: str) -> None:
        self.processados.append((sku, nome, chamada[:80]))

    def add_pulado_sem_url(self, sku: str, nome: str) -> None:
        self.pulados_sem_url.append((sku, nome))

    def add_pulado_download(self, sku: str, nome: str, motivo: str) -> None:
        self.pulados_download_falhou.append((sku, nome, motivo))

    def add_pulado_validacao(self, sku: str, nome: str, erros: list) -> None:
        self.pulados_validacao_falhou.append((sku, nome, erros))

    def add_pulado_nao_joia(self, sku: str, nome: str) -> None:
        self.pulados_nao_joia.append((sku, nome))

    def add_pulado_ja_tem_desc(self, sku: str, nome: str) -> None:
        self.pulados_ja_tem_desc.append((sku, nome))

    def salvar(self, output_dir: str) -> str:
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        ts = self.inicio.strftime("%Y%m%d_%H%M%S")
        caminho = Path(output_dir) / f"log_execucao_{ts}.txt"
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(self._gerar_texto())
        return str(caminho)

    def imprimir_resumo(self) -> None:
        print(self._gerar_resumo_terminal())

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _custo_estimado_usd(self) -> float:
        # claude-sonnet-4-6: $3/M input, $15/M output
        return (self.tokens_input * 3 + self.tokens_output * 15) / 1_000_000

    def _gerar_texto(self) -> str:
        fim = datetime.now()
        duracao = fim - self.inicio
        linhas = []
        sep = "=" * 70

        linhas += [
            sep,
            "RELATORIO DE EXECUCAO — Gerador de Descricao Reex",
            sep,
            f"Início:   {self.inicio.strftime('%d/%m/%Y %H:%M:%S')}",
            f"Fim:      {fim.strftime('%d/%m/%Y %H:%M:%S')}",
            f"Duração:  {str(duracao).split('.')[0]}",
            "",
            "TOTAIS",
            "-" * 40,
            f"  Total de linhas na planilha : {self.total_linhas}",
            f"  Produtos PAI identificados  : {self.total_pais}",
            f"  Produtos FILHO (ignorados)  : {self.total_filhos}",
            "",
            "RESULTADO DOS PAIS",
            "-" * 40,
            f"  [OK]  Processados com sucesso  : {len(self.processados)}",
            f"  [--]  Pulados - sem URL imagem : {len(self.pulados_sem_url)}",
            f"  [--]  Pulados - falha download : {len(self.pulados_download_falhou)}",
            f"  [--]  Pulados - HTML invalido  : {len(self.pulados_validacao_falhou)}",
            f"  [--]  Pulados - nao processavel : {len(self.pulados_nao_joia)}",
            f"  [--]  Pulados - ja tem descricao: {len(self.pulados_ja_tem_desc)}",
        ]

        if self.processados:
            linhas += ["", "DETALHES — PROCESSADOS COM SUCESSO", "-" * 40]
            for sku, nome, chamada in self.processados:
                linhas.append(f"  [{sku}] {nome}")
                linhas.append(f"    → \"{chamada}...\"")

        if self.pulados_sem_url:
            linhas += ["", "DETALHES — SEM URL DE IMAGEM", "-" * 40]
            for sku, nome in self.pulados_sem_url:
                linhas.append(f"  [{sku}] {nome}")

        if self.pulados_download_falhou:
            linhas += ["", "DETALHES — FALHA NO DOWNLOAD", "-" * 40]
            for sku, nome, motivo in self.pulados_download_falhou:
                linhas.append(f"  [{sku}] {nome}")
                linhas.append(f"    Motivo: {motivo}")

        if self.pulados_validacao_falhou:
            linhas += ["", "DETALHES — VALIDAÇÃO HTML FALHOU", "-" * 40]
            for sku, nome, erros in self.pulados_validacao_falhou:
                linhas.append(f"  [{sku}] {nome}")
                for e in erros:
                    linhas.append(f"    • {e}")

        if self.pulados_nao_joia:
            linhas += ["", "DETALHES — NAO PROCESSAVEL (revisar manualmente)", "-" * 40]
            for sku, nome in self.pulados_nao_joia:
                linhas.append(f"  [{sku}] {nome}")

        # Custo de API
        if self.tokens_input > 0 or self.tokens_output > 0:
            custo = self._custo_estimado_usd()
            linhas += [
                "",
                "CUSTO DA API",
                "-" * 40,
                f"  Tokens input:  {self.tokens_input:,}",
                f"  Tokens output: {self.tokens_output:,}",
                f"  Custo estimado: US$ {custo:.4f}",
            ]

        linhas.append(sep)
        return "\n".join(linhas) + "\n"

    def _gerar_resumo_terminal(self) -> str:
        return (
            f"\n{'=' * 50}\n"
            f"  Processados: {len(self.processados)}\n"
            f"  Pulados (sem URL):       {len(self.pulados_sem_url)}\n"
            f"  Pulados (download):      {len(self.pulados_download_falhou)}\n"
            f"  Pulados (HTML inválido): {len(self.pulados_validacao_falhou)}\n"
            f"  Pulados (nao processavel): {len(self.pulados_nao_joia)}\n"
            f"{'=' * 50}\n"
        )
