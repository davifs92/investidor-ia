# Auditoria do Projeto: Roadmap vs Implementação Real

## Resumo Executivo

O agente anterior entregou uma base arquitetural sólida e cobrindo a maioria dos requisitos técnicos do ROADMAP. Contudo, há **gaps críticos, bugs e inconsistências** que precisam ser endereçados antes de considerar o projeto "pronto".

---

## ✅ O que foi implementado corretamente

| Requisito | Status | Evidência |
|---|---|---|
| **1.1** Paralelismo com `asyncio.gather` | ✅ Completo | `generate.py` L62-89 |
| **1.2** Agno multi-LLM via `.env` | ✅ Completo | `settings.py`, `utils.py` |
| **1.3** RAG com LanceDB/PdfKnowledgeBase | ✅ Implementado | `earnings_release.py` + `knowledge/pdf_kb.py` |
| **1.4** Facade multi-mercado (MarketRouter) | ✅ Arquitetura correta | `market_router.py`, `data_providers/br/` e `us/` |
| **1.5** InvestMCP como MCPTools do Agno | ✅ Integrado | `technical.py` + `mcp_servers/investmcp/` |
| **2.2** Analista Macroeconômico bifurcado | ✅ Implementado | `macro.py` (BR=BCB, US=placeholder) |
| **2.3** Analista Técnico via MCP | ✅ Implementado | `technical.py` |
| **2.4** Seletor de mercado na UI | ✅ Implementado | `generate.py` L192-197 |
| **Prompt Engineering** | ✅ Refatorado | system_message vs user_prompt separados em todos os 10 agentes |

---

## 🔴 Gaps Críticos (Blockers)

### GAP-01: `FRED API` no macro.py é um hardcode, não usa a API real
**Arquivo:** `src/agents/analysts/macro.py` L16-18
```python
def get_fed_funds():
    # Placeholder para FRED API sem apiKey...
    return "5.25 (Estimativa Atual)"  # ← DADO ESTÁTICO! Nunca atualiza.
```
**Impacto:** O analista macro de ativos americanos sempre retorna `5.25%` independente da data. O ROADMAP especificou explicitamente o endpoint FRED. Sem FRED_API_KEY no `.env`.

**Solução sugerida:** Implementar `get_fed_funds()` real chamando `api.stlouisfed.org/fred/series/observations?series_id=FEDFUNDS&api_key={FRED_API_KEY}&limit=1&sort_order=desc`. Adicionar `FRED_API_KEY` ao `.env.example`.

---

### GAP-02: `earnings_release_pdf_path` para tickers US lança `ValueError` sem fallback gracioso
**Arquivo:** `src/data_providers/us/provider.py` L132-135

```python
def earnings_release_pdf_path(self, ticker: str) -> str:
    raise ValueError(f"Earnings Release para o ticker US {ticker} não implementado ainda")
```

**Impacto:** Qualquer análise de ativo americano (ex: `AAPL`) **vai falhar** no passo `earnings_release.analyze(ticker)`. O `generate.py` não protege contra esse erro. O fluxo assíncrono vai retornar uma exceção não-capturada.

**Evidência:** `earnings_release.py` L10-15 tenta `stocks.earnings_release_pdf_path(ticker)` e tem um `except Exception` que captura, retornando `BaseAgentOutput(content='Erro...', sentiment='NEUTRAL', confidence=0)`. OK, captura, mas degrada silenciosamente sem informar o usuário.

**Solução sugerida:** Implementar integração básica com SEC EDGAR conforme o ROADMAP especificou, ou no mínimo exibir um aviso claro na UI quando o ticker for americano.

---

### GAP-03: Duplicação de seções no prompt do Graham e Buffett
**Arquivos:** `graham.py` L186-196, `buffett.py` L153-173

```python
## DADOS FINANCEIROS DISPONÍVEIS
{dre_year}

## CRITÉRIOS CLÁSSICOS CALCULADOS
{classic_criteria}

## DADOS FINANCEIROS DISPONÍVEIS     ← DUPLICADO!
{dre_year}

## CRITÉRIOS CLÁSSICOS CALCULADOS   ← DUPLICADO!
{classic_criteria}
```

**Impacto:** Dobra o uso de tokens na janela de contexto sem adicionar valor. Pode confundir o LLM com dados redundantes. Regressão introduzida pelo agente anterior.

---

### GAP-04: `valuation.py` usa `stocks.screener()` que pode retornar lista vazia para tickers US
**Arquivo:** `src/agents/analysts/valuation.py` L11-26

O `screener()` no provider US retorna `[]` (linha 124-125 do `us/provider.py`). O código depois cria um `pl.DataFrame([])` e tenta fazer `.filter(...)` e `.mean()`, o que gera **valores completamente vazios/nulos** passados para o LLM. Não há guard clause para esse caso.

**Impacto:** O analista de valuation entrega dados sem sentido para ativos americanos.

---

### GAP-05: `news.py` usa apenas `einvestidor.estadao.com.br` — não funciona para tickers americanos
**Arquivo:** `src/agents/analysts/news.py` L22-26

A pesquisa de notícias usa `site:einvestidor.estadao.com.br` hardcoded. Para `AAPL`, `MSFT`, etc., não retornará notícias relevantes.

**Solução sugerida:** Bifurcar a busca como já feito no `macro.py`: se `.SA`, busca no einvestidor; caso contrário, busca em `site:reuters.com OR site:bloomberg.com OR site:finance.yahoo.com`.

---

### GAP-06: `barsi.py` é chamado para tickers US (não há bloqueio na UI)
**Arquivo:** `src/settings.py` L26-36

O `INVESTORS_US` não inclui Barsi, mas o `generate.py` não valida se o investor selecionado é compatível com o mercado do ticker digitado. Se alguém seleciona mercado Brasil e digita `AAPL`, vai tentar rodar `barsi.analyze("AAPL")` — que não faz sentido conceitualmente.

---

## 🟡 Gaps Médios (Quality Issues)

### GAP-07: `macro.py` não puxa IPCA e atas do COPOM (ROADMAP 2.2)
O ROADMAP especificou: "Decisões recentes do COPOM e níveis atuais de IPCA e SELIC". O código atual pega **apenas a SELIC**. IPCA e atas do COPOM foram omitidos.

**Endpoints BCB disponíveis:**
- IPCA: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json`

---

### GAP-08: `lynch.py` está superficial — não carrega dados financeiros
Comparando com Buffett (carrega DRE, cálculo de crescimento, dividendos) e Graham (calcula NCAV, múltiplos), Lynch **não carrega nenhum dado financeiro** — apenas recebe as análises dos outros agentes e a `company_name`.

O ROADMAP 2.1 pede para Lynch focar em PEG Ratio (P/L ÷ crescimento), mas o `PEG` nunca é calculado. É a persona mais vazia do projeto.

---

### GAP-09: `get_model()` não tem `API_KEY` verificado no `settings.py`
**Arquivo:** `src/settings.py` L38-39

```python
API_KEY = config('LLM_PROVIDER', default='gemini')  # ← PROVAVELMENTE BUG, lê o PROVIDER, não a key!
```

Isso é provavelmente um bug de copiar-e-colar. O `generate.py` L31 verifica `if not API_KEY` e para a execução. Mas `API_KEY` nunca vai ser falsy porque está lendo `LLM_PROVIDER`, não a chave real.

---

### GAP-10: `BaseDataProvider.income_statement` retorna `dict` na assinatura mas providers retornam `list[dict]`
**Arquivo:** `src/data_providers/base.py` L14-21

```python
def income_statement(...) -> dict:  # ← type hint errado
```

Todos os providers reais retornam `list[dict]`. Viola o contrato do `BaseDataProvider`.

---

### GAP-11: `earnings_release.py` importa `datetime` dentro da função — padrão inconsistente
**Arquivo:** `src/agents/analysts/earnings_release.py` L59

`import datetime` foi colocado no meio da função. Deve estar no topo do arquivo.

---

## 🟢 Melhorias de Produto (Nice to Have)

### MELHORIA-01: PDF Export (Req. 2.5) — não implementado
O ROADMAP menciona `markdown2 + xhtml2pdf` para exportar relatórios como PDF. **Não foi implementado**. Estava listado como `pages/reports.py` no projeto mas parece ser apenas visualização.

### MELHORIA-02: Barsi desabilitado automaticamente ao selecionar mercado EUA
O ROADMAP 2.4 pede: "Ao selecionar EUA, desabilitar automaticamente o analista Barsi". Isso está **parcialmente implementado** (Barsi não aparece no `INVESTORS_US`), mas não há feedback visual claro ao usuário explicando o motivo.

### MELHORIA-03: Testes de integração para US providers são inexistentes
Os testes existentes (`test_data_providers.py`, `test_generate_parallel.py`) cobrem apenas o fluxo BR. Não há nenhum teste para `USDataProvider` + `MarketRouter` com tickers americanos.

### MELHORIA-04: Cache não tem TTL definido
**Arquivo:** `src/cache.py` (487 bytes)
O decorador `@cache_it` não parece ter TTL. Dados de yfinance ficam em cache indefinitamente, o que pode causar análises com dados desatualizados.

---

## Prioridade de Correção Sugerida

| Prioridade | Gap | Esforço |
|---|---|---|
| 🔴 P0 | GAP-03 (duplicação de prompt Buffett/Graham) | 10min |
| 🔴 P0 | GAP-09 (API_KEY lendo variável errada) | 5min |
| 🔴 P0 | GAP-05 (news.py sem bifurcação BR/US) | 1h |
| 🔴 P1 | GAP-01 (FRED API hardcoded) | 2h |
| 🔴 P1 | GAP-04 (valuation sem screener US) | 1h |
| 🟡 P2 | GAP-08 (Lynch sem dados financeiros/PEG) | 2h |
| 🟡 P2 | GAP-07 (macro sem IPCA/COPOM) | 1h |
| 🟡 P2 | GAP-10 (type hints errados no BaseDataProvider) | 15min |
| 🟡 P2 | GAP-11 (import datetime dentro de função) | 5min |
| 🟢 P3 | MELHORIA-01 (PDF export) | 3h |
| 🟢 P3 | MELHORIA-03 (testes US) | 2h |
| 🟢 P3 | MELHORIA-04 (cache TTL) | 1h |
