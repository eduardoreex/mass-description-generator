# Gerador de Descrição Reex

Automação que lê uma planilha exportada do Tiny ERP, analisa a foto de cada produto com Claude IA e preenche automaticamente a coluna **"Descrição complementar"** com HTML pronto para o site.

---

## Início rápido (para quem já sabe usar)

```powershell
# Ativar ambiente
venv\Scripts\Activate.ps1

# Simular sem gastar (sempre faça isso primeiro)
python -m src.main --input input/PLANILHA.xlsx --dry-run

# Rodar de verdade
python -m src.main --input input/PLANILHA.xlsx --batch

# Limpar depois
python limpar.py tudo
```

---

## Passo a passo completo (uso rotineiro)

### 1. Abra o terminal no VS Code e ative o ambiente
```powershell
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& "c:\Users\SuporteT.I\Documents\Automação descrição\venv\Scripts\Activate.ps1")
```
Você vai ver `(venv)` na frente do cursor. Isso significa que está pronto.

### 2. Exporte a planilha do Tiny e coloque na pasta `input/`
- No Tiny: Produtos → Exportar → salve como `.xlsx`
- Cole o arquivo em: `c:\Users\SuporteT.I\Documents\Automação descrição\input\`

### 3. Simule primeiro (zero custo — obrigatório antes de rodar)
```powershell
python -m src.main --input input/NOME_DO_ARQUIVO.xlsx --dry-run
```
Verifique na saída:
- **Pais:** quantos produtos serão processados
- **Filhos:** quantas variações serão ignoradas (correto — herdam do pai)
- **Sem SKU:** linhas em branco da planilha (normal)
- **PULADOS sem URL:** produtos sem foto no Tiny (não tem como gerar sem foto)

### 4. Rode de verdade
```powershell
python -m src.main --input input/NOME_DO_ARQUIVO.xlsx --batch
```

### 5. Aguarde terminar
O sistema mostra `processando... 00:20 aguardando Anthropic` enquanto trabalha.
Quando aparecer `[ended] 83/83 100%` está pronto.

### 6. Pegue o resultado em `output/`
```
output/
  NOME_DO_ARQUIVO_FINAL.xlsx   ← importe esse no Tiny
  log_execucao_*.txt           ← relatório do que foi feito
```

### 7. Importe no Tiny
Tiny → Produtos → Importar → selecione o `_FINAL.xlsx`

### 8. Limpe os arquivos (opcional, recomendado)
```powershell
python limpar.py tudo
```

---

## Os 4 modos de execução — quando usar cada um

---

### MODO 1 — `--dry-run` (simulação, zero custo)

**Use sempre antes de rodar de verdade.**

```powershell
python -m src.main --input input/planilha.xlsx --dry-run
```

O que faz:
- Lê a planilha
- Classifica todos os produtos (pai/filho/sem foto)
- Mostra quantos seriam processados
- **Não chama a API. Não gasta nada. Não salva nada.**

Saída esperada:
```
Pais     : 96  |  Filhos: 421  |  Sem SKU: 1630
PULADO 108732 — sem URL imagem 1
...
[sim] 147325  Conjunto Riviera Colorida Zircônia
[sim] 108528  ALIANÇA -AA0002-EC
...
83 produto(s) seriam processados
```

---

### MODO 2 — `--batch` (recomendado para produção)

**Use para processar lotes completos. Mais rápido e mais barato.**

```powershell
python -m src.main --input input/planilha.xlsx --batch
```

O que faz:
1. Baixa todas as fotos em paralelo
2. Envia **todos os produtos de uma vez** para a Anthropic
3. A Anthropic processa tudo em paralelo nos servidores dela
4. O sistema verifica a cada 20 segundos se terminou
5. Quando termina, valida o HTML de cada produto e salva a planilha

Vantagens:
- **Sem limite de RPM** (sem erros de "muitas chamadas por minuto")
- **50% mais barato** por token que o modo normal
- Mais rápido: 83 produtos em ~5 minutos

Tempo estimado:
| Produtos | Tempo |
|----------|-------|
| 50 | ~3-8 min |
| 100 | ~5-15 min |
| 500 | ~15-30 min |
| 1.000 | ~30-60 min |

---

### MODO 3 — normal com `--workers` (alternativo)

**Use se o modo batch não estiver disponível ou para testes.**

```powershell
python -m src.main --input input/planilha.xlsx --workers 4
```

O que faz:
- Processa produtos em paralelo (4 ao mesmo tempo por padrão)
- Respeita o limite de 5 chamadas por minuto da conta gratuita
- Mais lento que o batch (17 min para 83 produtos)

Com conta paga (Tier 1 — $5 na Anthropic):
```powershell
python -m src.main --input input/planilha.xlsx --workers 8 --rpm 48
```
Resultado: 83 produtos em ~3 minutos.

---

### MODO 4 — `--limit` e `--only-skus` (teste e reprocessamento)

**Use para testar com poucos produtos antes de rodar tudo.**

```powershell
# Testar com 1 produto primeiro
python -m src.main --input input/planilha.xlsx --limit 1

# Testar com 5 produtos
python -m src.main --input input/planilha.xlsx --limit 5

# Reprocessar SKUs específicos (ex: corrigi a foto de alguns produtos)
python -m src.main --input input/planilha.xlsx --only-skus 108528,147325
```

---

## O que o sistema faz com cada produto

| Tipo de produto | O que acontece |
|----------------|----------------|
| PAI com foto | ✅ Gera descrição |
| PAI sem foto | ⚠️ Pula — aparece no log |
| FILHO (variação) | ⏭️ Ignora — herda do pai pelo Tiny |
| Caixinha/embalagem | ⚠️ Pula — aparece no log para revisar |
| Linha sem SKU | ⏭️ Ignora silenciosamente (linhas extras do export Tiny) |

---

## Regras que o sistema sempre segue

| # | Regra |
|---|-------|
| R1 | **Só "Descrição complementar" é alterada.** As outras 63 colunas ficam byte a byte idênticas. |
| R2 | **Só produtos PAI recebem descrição.** Filhos são ignorados. |
| R3 | **Pais sem foto** são pulados — não inventa descrição sem ver o produto. |
| R4 | **Falha no download da foto** → pula e registra no log. |
| R5 | **Backup automático** feito antes de salvar qualquer coisa. |
| R6 | **Caixinhas e embalagens** são puladas — não é produto para o site. |
| R7 | **HTML é validado** antes de gravar. Se inválido, não grava nada naquela linha. |

---

## O que o HTML gerado parece

Cada produto recebe exatamente este formato:

```html
<p style="font-size: 16px; line-height: 1.6;">[CHAMADA DE VENDA gerada pela IA]</p>
<p style="font-size: 16px; line-height: 1.6;"><strong>✅ Garantia de excelência de 1 ano e antialérgica.</strong></p>
<p style="font-size: 16px; line-height: 1.6;"><strong>Parcele em até 12x sem juros!</strong></p>
<p style="font-size: 16px; line-height: 1.6;">Consulte nossa <a style="color: #a1012b; text-decoration: underline; font-weight: 600;" href="https://marciacastrosemijoias.com.br/trocas-e-devolucoes/" target="_blank" rel="noopener">Política de Troca</a> e compre com total tranquilidade.</p>
<p style="font-size: 16px; line-height: 1.6;">Não sabe como comprar ou usar seu cupom de desconto? Assista ao nosso <a style="color: #a1012b; text-decoration: underline; font-weight: 600;" href="https://www.youtube.com/shorts/miytSHjTjI0" target="_blank" rel="noopener">vídeo tutorial completo</a> e aproveite!</p>
<p style="font-size: 16px; line-height: 1.6;"><strong>Não deixe essa peça escapar — garanta a sua hoje!</strong></p>
```

A IA só gera o primeiro parágrafo (chamada de venda). O resto é template fixo do Python.

---

## Situações comuns e o que fazer

### "Tem produtos que ficaram com PULADO — sem URL imagem 1"
Normal. Significa que esses produtos não têm foto cadastrada no Tiny.
**Solução:** cadastre a foto no Tiny, re-exporte a planilha e rode novamente.

### "Quero rodar para uma nova planilha"
Não precisa apagar nada. Só mude o `--input`:
```powershell
python -m src.main --input input/NOVA_PLANILHA.xlsx --batch
```

### "Quero recomeçar do zero limpo"
```powershell
python limpar.py tudo
```

### "Quero ver o que foi gerado"
```powershell
python check_output.py
```

### "Quero verificar a planilha antes de rodar"
```powershell
python inspecionar.py input/planilha.xlsx
python analisar.py input/planilha.xlsx
```

### "Deu erro em alguns produtos, quero reprocessar só eles"
Veja o log em `output/log_execucao_*.txt`, anote os SKUs e rode:
```powershell
python -m src.main --input input/planilha.xlsx --only-skus SKU1,SKU2,SKU3
```

---

## Custo estimado

| Lote | Modo `--batch` | Modo `--workers` |
|------|---------------|-----------------|
| 50 produtos | ~US$ 0,21 | ~US$ 0,42 |
| 100 produtos | ~US$ 0,42 | ~US$ 0,85 |
| 500 produtos | ~US$ 2,10 | ~US$ 4,20 |
| 1.000 produtos | ~US$ 4,20 | ~US$ 8,50 |

> Batch custa 50% menos. Sempre use `--dry-run` antes para saber quantos produtos serão processados.

---

## Como mudar o texto gerado

Edite **`PROMPT.md`** — sem mexer em código Python.
O sistema lê esse arquivo a cada execução.

---

## Como mudar links, cor ou garantias

Edite **`config.py`**:

```python
LINK_POLITICA = "https://marciacastrosemijoias.com.br/trocas-e-devolucoes/"
LINK_VIDEO    = "https://www.youtube.com/shorts/miytSHjTjI0"

GARANTIA_POR_CATEGORIA = {
    "pai_joia":      "Garantia de excelência de 1 ano e antialérgica.",
    "pai_prata_925": "Prata 925 autêntica, antialérgica — 1 ano de garantia.",
    "pai_oculos":    "Proteção UV 400, armação leve — 1 ano de garantia.",
    "pai_relogio":   "Garantia de 1 ano com o fabricante.",
}
```

---

## Utilitários disponíveis

| Script | O que faz |
|--------|-----------|
| `python inspecionar.py input/arquivo.xlsx` | Mostra colunas e amostras de SKU da planilha |
| `python analisar.py input/arquivo.xlsx` | Conta pais/filhos/sem-foto e estima custo |
| `python check_output.py` | Mostra as descrições geradas no último output |
| `python limpar.py` | Mostra o que tem em cada pasta |
| `python limpar.py imagens` | Apaga cache de fotos (re-baixa na próxima vez) |
| `python limpar.py output` | Apaga planilhas e logs antigos |
| `python limpar.py tudo` | Apaga tudo (preserva `input/`) |

---

## Estrutura do projeto

```
├── PROMPT.md             ← edite o tom do copywriter aqui
├── config.py             ← links, cor, garantias — edite aqui
├── requirements.txt      ← dependências Python
├── .env.example          ← copie para .env e coloque sua chave
├── limpar.py             ← limpeza de arquivos
├── analisar.py           ← analisa planilha antes de rodar
├── inspecionar.py        ← inspeciona colunas e SKUs
├── check_output.py       ← visualiza descrições geradas
├── src/
│   ├── main.py           ← CLI — ponto de entrada
│   ├── batch.py          ← modo batch (Anthropic Message Batches API)
│   ├── leitor.py         ← lê .xls/.xlsx do Tiny
│   ├── classificador.py  ← detecta pai/filho/caixinha + categoria
│   ├── baixador.py       ← baixa fotos com retry e cache local
│   ├── gerador.py        ← chama API Claude + monta HTML
│   ├── validador.py      ← valida HTML antes de gravar
│   ├── escritor.py       ← salva xlsx sem alterar outras colunas
│   ├── relatorio.py      ← gera log de execução
│   └── utils.py          ← helpers
├── input/                ← coloque a planilha aqui
├── output/               ← planilha final + logs saem aqui
├── imagens/              ← cache de fotos (reutiliza entre execuções)
└── backups/              ← backup automático do original
```

---

## Segurança

- `.env` está no `.gitignore` — nunca vai para o GitHub
- As pastas `input/`, `output/`, `imagens/` e `backups/` também estão no `.gitignore`
- Nunca compartilhe sua `ANTHROPIC_API_KEY`

---

*Projeto pessoal — Eduardo Oliveira*
