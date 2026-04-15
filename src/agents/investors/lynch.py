import datetime
from textwrap import dedent
from typing import Literal
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools
from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.portfolio.persona_interface import PortfolioPersonaInput, PortfolioPersonaOutput
from src.utils import get_model, calc_cagr

SYSTEM_PROMPT = dedent("""
Você é PETER LYNCH, um dos maiores gestores de fundos mútuos da história, conhecido pelo seu tempo à frente do Magellan Fund da Fidelity.
Você popularizou o conceito de GARP (Growth At a Reasonable Price) e "investir naquilo que você conhece".

## SUA FILOSOFIA
- Busca empresas com grande tração de consumo e entendimento de mercado prático.
- Valoriza PEG Ratio (P/L ÷ Crescimento do Lucro) amigável — idealmente abaixo de 1.0.
- Balanços conservadores e caixa sólido são fundamentais.
- Odeia empresas que perdem escopo diversificando fora do nicho original ("Diworsification").
- Classifica empresas em: Fast Grower, Stalwart, Turnaround, Cyclical, Asset Play, Slow Grower.
""")

INSTRUCTIONS = dedent("""
## SUA TAREFA
1. Classifique a tese do ativo (Fast Grower, Stalwart, Turnaround, Cyclical, Asset Play, Slow Grower).
2. Avalie o PEG Ratio calculado. Se PEG < 1.0: muito atrativo. Entre 1 e 2: razoável. Acima de 2: caro para o crescimento.
3. Verifique se as receitas e lucros comprovam o "selo" dado.
4. Avalie se há risco de "Diworsification" (expansão fora do core).
5. Conclua com decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR.

Use argumentos verbais coesos e bem fundamentados nos dados fornecidos.
""")

_EMPTY = BaseAgentOutput(content="Não Fornecido", sentiment="NEUTRAL", confidence=0)


def _validate_lynch_market(portfolio_data: PortfolioPersonaInput):
    br_weight = float(portfolio_data.market_weights.get('BR', 0.0))
    if br_weight > 0:
        raise ValueError('Persona Lynch suporta apenas carteira US no modo portfólio.')


def _analyze_portfolio(portfolio_data: PortfolioPersonaInput) -> BaseAgentOutput:
    _validate_lynch_market(portfolio_data)
    recommendation = _portfolio_recommendation(portfolio_data)
    top = ', '.join(f'{h.ticker} ({h.weight:.1f}%)' for h in portfolio_data.top_holdings[:3]) or 'Sem dados'
    risk = portfolio_data.risks[0] if portfolio_data.risks else 'Risco principal não identificado.'
    garp_view = (
        'Vejo uma base razoável de crescimento sustentável com disciplina de preço.'
        if portfolio_data.overall_score >= 7
        else 'A carteira ainda não está equilibrando bem crescimento e preço razoável (GARP).'
    )
    content = dedent(f"""
    ## Avaliação Estratégica da Carteira
    No meu framework, o portfólio marca **{portfolio_data.overall_score:.1f}/10** com sentimento **{portfolio_data.portfolio_sentiment}**.
    Principais posições: {top}.
    {garp_view}

    ## Riscos Principais
    Maior risco identificado: {risk}
    Vou manter atenção especial em concentração e em sinais que indiquem crescimento sem sustentação.

    ## Conclusão
    Minha recomendação é **{recommendation}**.
    O ideal é priorizar empresas que cresçam com consistência e valuation ainda justificável.
    """).strip()
    parsed = PortfolioPersonaOutput(
        content=content,
        sentiment=portfolio_data.portfolio_sentiment,
        confidence=max(0, min(100, int(round(portfolio_data.weighted_confidence)))),
        recommendation=recommendation,
    )
    return BaseAgentOutput(content=parsed.content, sentiment=parsed.sentiment, confidence=parsed.confidence)


def _portfolio_recommendation(portfolio_data: PortfolioPersonaInput) -> Literal['MANTER', 'OBSERVAR', 'REBALANCEAR']:
    if portfolio_data.overall_score >= 7.0 and portfolio_data.max_asset_weight <= 35:
        return 'MANTER'
    if portfolio_data.overall_score < 5.0 or portfolio_data.max_asset_weight > 40:
        return 'REBALANCEAR'
    return 'OBSERVAR'


def analyze(
    ticker: str = '',
    earnings_release_analysis: BaseAgentOutput = _EMPTY,
    financial_analysis: BaseAgentOutput = _EMPTY,
    valuation_analysis: BaseAgentOutput = _EMPTY,
    news_analysis: BaseAgentOutput = _EMPTY,
    macro_analysis: BaseAgentOutput = _EMPTY,
    technical_analysis: BaseAgentOutput = _EMPTY,
    market: str | None = None,
    analysis_mode: Literal['ticker', 'portfolio'] = 'ticker',
    portfolio_data: PortfolioPersonaInput | None = None,
) -> BaseAgentOutput:
    if analysis_mode == 'portfolio':
        if portfolio_data is None:
            raise ValueError('portfolio_data é obrigatório quando analysis_mode="portfolio".')
        return _analyze_portfolio(portfolio_data)

    today = datetime.date.today()
    year_start = today.year - 5

    company_name = stocks.name(ticker, market=market)
    segment = stocks.details(ticker, market=market).get('segmento_de_atuacao', 'N/A')
    multiples = stocks.multiples(ticker, market=market)
    latest = multiples[0] if multiples else {}

    dre_year = stocks.income_statement(ticker, year_start, today.year, 'annual', market=market)
    cagr_5y_lucro = calc_cagr(dre_year, 'lucro_liquido', 5) if len(dre_year) >= 2 else None

    # PEG Ratio: P/L dividido pela taxa de crescimento do lucro (em %)
    pl = latest.get('p_l', 0.0) or 0.0
    peg_ratio = None
    peg_label = 'N/A (dados insuficientes)'
    if cagr_5y_lucro and cagr_5y_lucro > 0 and pl > 0:
        peg_ratio = round(pl / (cagr_5y_lucro * 100), 2)
        if peg_ratio < 1.0:
            peg_label = f"{peg_ratio} — MUITO ATRATIVO (PEG < 1.0)"
        elif peg_ratio < 2.0:
            peg_label = f"{peg_ratio} — RAZOÁVEL (1.0 ≤ PEG < 2.0)"
        else:
            peg_label = f"{peg_ratio} — CARO para o crescimento (PEG ≥ 2.0)"

    prompt = dedent(f"""
    Dado o contexto, analise a empresa como Peter Lynch faria.
    Nome: {company_name}
    Ticker: {ticker}
    Setor: {segment}

    ## MÉTRICAS CALCULADAS (PRÉ-LLM)
    P/L Atual: {pl}
    CAGR Lucro Líquido 5 anos: {f"{cagr_5y_lucro:.1%}" if cagr_5y_lucro else "N/A"}
    PEG Ratio: {peg_label}
    DY: {latest.get('dy', 'N/A')}
    ROE: {latest.get('roe', 'N/A')}

    ## HISTÓRICO FINANCEIRO (5 anos)
    {dre_year}

    ## OPINIÕES DOS ANALISTAS PERIFÉRICOS
    **Earnings Release:** {earnings_release_analysis.content}
    **Dados Financeiros:** {financial_analysis.content}
    **Valuation:** {valuation_analysis.content}
    **Notícias:** {news_analysis.content}
    **Ambiente Macro:** {macro_analysis.content}
    **Análise Técnica:** {technical_analysis.content}

    Forneça sua conclusão rigorosa baseada nos cruzamentos destes dados.
    """)

    agent = Agent(
        model=get_model(temperature=0.4),
        system_message=SYSTEM_PROMPT,
        instructions=INSTRUCTIONS,
        tools=[ReasoningTools(think=True, analyze=True)],
        response_model=BaseAgentOutput,
        retries=3
    )
    r = agent.run(f"Data de Hoje: {today.isoformat()}\n\n" + prompt)
    return r.content
