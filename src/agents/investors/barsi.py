import datetime
from textwrap import dedent
from typing import Literal

import polars as pl
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.portfolio.persona_interface import PortfolioPersonaInput, PortfolioPersonaOutput
from src.utils import calc_cagr, get_model


SYSTEM_PROMPT = dedent("""
Você é **LUIZ BARSI**, conhecido como o "Bilionário dos Dividendos" e o maior investidor pessoa física da bolsa brasileira. 
Sua estratégia de investimento é focada na construção de uma "carteira previdenciária" através de ações que pagam dividendos consistentes e crescentes ao longo do tempo.  

## **FILOSOFIA DE INVESTIMENTO**  
- Você busca **empresas sólidas** que atuam em setores perenes e essenciais da economia.  
- Você valoriza **empresas que pagam dividendos consistentes e crescentes**, criando uma renda passiva substancial.  
- Você investe com **horizonte de longo prazo**, ignorando volatilidades de curto prazo e focando na geração de renda.  
- Você prefere **setores regulados e previsíveis** como utilities (energia elétrica, saneamento), bancos e papel e celulose.  
- Você valoriza **empresas com baixo endividamento** e boa geração de caixa operacional.  
- Você evita empresas com alta volatilidade ou que dependem de ciclos econômicos específicos.  
- Você busca **preços razoáveis**, mas não se preocupa tanto com o "timing perfeito" de compra.  
- Você acredita que **reinvestir dividendos** é a chave para construir um patrimônio significativo.
""")

INSTRUCTIONS = dedent("""
## **SUA TAREFA**  
Analise esta empresa como Luiz Barsi faria, aplicando rigorosamente seus critérios. Considere as análises de outros especialistas, mas sempre confie no seu próprio julgamento baseado em sua filosofia de dividendos.  

Sua análise deve seguir uma estrutura de seções, como análise do negócio, análise dos fundamentos, etc.
As seções não precisam ser pré-definidas, faça do jeito que você achar melhor e que faça sentido para sua análise.
A única seção obrigatória é a "CONCLUSÃO", onde você deve tomar a sua decisão final sobre a empresa e resumir os pontos importantes da sua análise.
Apesar disso:
- Você deve analisar o histórico de dividendos da empresa, sua geração de caixa, seu payout e seu crescimento de dividendos.
- Você deve analisar a qualidade dos dividendos da empresa, se eles são consistentes e crescentes.
- Você deve analisar a saúde financeira da empresa, incluindo seu endividamento, margem de lucro, ROE e geração de caixa.
- Quais são os principais riscos para a continuidade dos dividendos?  
- Existem mudanças regulatórias ou setoriais que podem afetar a capacidade de pagamento?  
- A empresa pode manter sua posição competitiva no longo prazo?

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## **IMPORTANTE**
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- **Priorize a geração de renda passiva** sobre ganhos de capital.  
- **Considere o longo prazo** e ignore volatilidades temporárias.  
- Sempre busque **empresas que você entenda facilmente**, pois Barsi valoriza a simplicidade nos negócios.  

> *"O segredo é comprar ações de empresas sólidas, que pagam bons dividendos, e reinvestir esses dividendos. Com o tempo, você constrói uma renda passiva substancial."* - Luiz Barsi  
""")


_EMPTY = BaseAgentOutput(content="Não Fornecido", sentiment="NEUTRAL", confidence=0)


def _validate_barsi_market(portfolio_data: PortfolioPersonaInput):
    us_weight = float(portfolio_data.market_weights.get('US', 0.0))
    if us_weight > 0:
        raise ValueError('Persona Barsi suporta apenas carteira BR no modo portfólio.')


def _analyze_portfolio(portfolio_data: PortfolioPersonaInput) -> BaseAgentOutput:
    _validate_barsi_market(portfolio_data)
    recommendation = _portfolio_recommendation(portfolio_data)
    principal_risk = portfolio_data.risks[0] if portfolio_data.risks else 'Risco principal não identificado.'
    renda_view = (
        'A carteira mostra disciplina de longo prazo para renda recorrente.'
        if portfolio_data.overall_score >= 7
        else 'Ainda falta consistência para transformar a carteira em renda previsível de longo prazo.'
    )
    content = dedent(f"""
    ## Avaliação Estratégica da Carteira
    Pelo meu método previdenciário, vejo **score {portfolio_data.overall_score:.1f}/10** e sentimento **{portfolio_data.portfolio_sentiment}**.
    {renda_view}

    ## Riscos e Continuidade de Renda
    Maior risco hoje: {principal_risk}
    Para minha filosofia, a carteira precisa proteger fluxo de dividendos e evitar concentração excessiva.

    ## Conclusão
    Minha recomendação final é **{recommendation}**.
    O foco deve seguir em qualidade de empresas brasileiras com histórico consistente de distribuição.
    """).strip()
    parsed = PortfolioPersonaOutput(
        content=content,
        sentiment=portfolio_data.portfolio_sentiment,
        confidence=max(0, min(100, int(round(portfolio_data.weighted_confidence)))),
        recommendation=recommendation,
    )
    return BaseAgentOutput(content=parsed.content, sentiment=parsed.sentiment, confidence=parsed.confidence)


def _portfolio_recommendation(portfolio_data: PortfolioPersonaInput) -> Literal['MANTER', 'OBSERVAR', 'REBALANCEAR']:
    if portfolio_data.overall_score >= 7.0 and portfolio_data.max_asset_weight <= 32:
        return 'MANTER'
    if portfolio_data.overall_score < 5.0 or portfolio_data.max_asset_weight > 38:
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
    year_end = today.year

    company_name = stocks.name(ticker, market=market)
    segment = stocks.details(ticker, market=market).get('segmento_de_atuacao', 'nan')
    multiples = stocks.multiples(ticker, market=market)
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'annual', market=market)
    if dre_year and len(dre_year) >= 2:
        cagr_5y_receita_liq = calc_cagr(dre_year, 'receita_liquida', 5)
        cagr_5y_lucro_liq = calc_cagr(dre_year, 'lucro_liquido', 5)
    else:
        cagr_5y_receita_liq = None
        cagr_5y_lucro_liq = None

    _dividends_by_year = stocks.dividends_by_year(ticker, market=market)
    dividends_growth_by_year = []
    dividends_by_year = []
    if _dividends_by_year and len(_dividends_by_year) > 0:
        try:
            df_divs = pl.DataFrame(_dividends_by_year)
            if "valor" in df_divs.columns and "ano" in df_divs.columns:
                dividends_growth_by_year = (
                    df_divs
                    .sort('ano')
                    .with_columns(valor=pl.col('valor').pct_change().round(4))
                    .drop_nulls()
                    .to_dicts()
                )
                # filtra dados do ano atual
                dividends_by_year = [d for d in _dividends_by_year if d['ano'] < today.year]
                dividends_growth_by_year = [d for d in dividends_growth_by_year if d['ano'] < today.year]
        except Exception as e:
            print(f"Erro ao processar dividendos no Polars (Barsi): {e}")
    else:
        dividends_by_year = []
        dividends_growth_by_year = []

    if multiples and isinstance(multiples, list) and len(multiples) > 0:
        preco_sobre_lucro = multiples[0].get('p_l', 'N/A')
        preco_sobre_valor_patrimonial = multiples[0].get('p_vp', 'N/A')
        dividend_yield = multiples[0].get('dy', 'N/A')
        try:
            dividend_yield_per_year = {d['ano']: d['dy'] for d in multiples}
        except Exception:
            dividend_yield_per_year = {}
    else:
        preco_sobre_lucro = 'N/A'
        preco_sobre_valor_patrimonial = 'N/A'
        dividend_yield = 'N/A'
        dividend_yield_per_year = {}

    payouts = stocks.payouts(ticker, market=market)

    prompt = dedent(f"""
    Dado o contexto, analise a empresa abaixo.
    Nome: {company_name}
    Ticker: {ticker}
    Setor: {segment}

    ## OPINIÃO DO ANALISTA SOBRE O ÚLTIMO EARNINGS RELEASE
    Sentimento: {earnings_release_analysis.sentiment}
    Confiança: {earnings_release_analysis.confidence}
    Análise: {earnings_release_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE OS DADOS FINANCEIROS DA EMPRESA
    Sentimento: {financial_analysis.sentiment}
    Confiança: {financial_analysis.confidence}
    Análise: {financial_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE O VALUATION DA EMPRESA
    Sentimento: {valuation_analysis.sentiment}
    Confiança: {valuation_analysis.confidence}
    Análise: {valuation_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE AS NOTÍCIAS DA EMPRESA
    Sentimento: {news_analysis.sentiment}
    Confiança: {news_analysis.confidence}
    Análise: {news_analysis.content}

    ## MACROECONOMIA E CUSTO DE OPORTUNIDADE
    {macro_analysis.content}

    ## CONDIÇÕES GRÁFICAS E MÉDIAS MÓVEIS (IGNORAR SE O HORIZONTE FOR MUITO CURTO)
    {technical_analysis.content}

    ## DADOS FINANCEIROS DISPONÍVEIS
    {dre_year}

    ## DADOS EXTRAS
    PREÇO SOBRE LUCRO: {preco_sobre_lucro}
    PREÇO SOBRE VALOR PATRIMONIAL: {preco_sobre_valor_patrimonial}
    CAGR 5Y RECEITA LIQ: {cagr_5y_receita_liq}
    CAGR 5Y LUCRO LIQ: {cagr_5y_lucro_liq}
    CRES. DIVIDENDOS ANUAIS: {dividends_growth_by_year}
    DIVIDEND YIELD ATUAL: {dividend_yield}
    HISTÓRICO DE DIVIDENDOS: {dividends_by_year}
    HISTÓRICO DE DIVIDEND YIELD POR ANO: {dividend_yield_per_year}
    HISTÓRICO DE PAYOUTS (EM %): {payouts}
    """)

    agent = Agent(
        model=get_model(),
        system_message=SYSTEM_PROMPT,
        instructions=INSTRUCTIONS,
        tools=[ReasoningTools(think=True, analyze=True)],
        response_model=BaseAgentOutput,
        retries=3,
    )
    r = agent.run(f"Data de Hoje: {today.isoformat()}\n\n" + prompt)
    return r.content
