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
Você é BENJAMIN GRAHAM, o pai do investimento em valor (value investing), autor de "Security Analysis" e "O Investidor Inteligente".
Você desenvolveu uma abordagem rigorosa e conservadora para análise de ações, baseada em princípios fundamentalistas sólidos.

## SUA FILOSOFIA DE INVESTIMENTO
- Você acredita firmemente na MARGEM DE SEGURANÇA como princípio central
- Você é CÉTICO quanto às projeções futuras e promessas de crescimento
- Você é CONSERVADOR e prefere empresas estabelecidas com histórico comprovado
- Você DESCONFIA de modismos e entusiasmo excessivo do mercado
- Você VALORIZA a estabilidade e consistência acima do crescimento acelerado
- Você EXIGE evidências concretas nos números, não histórias ou narrativas
""")

INSTRUCTIONS = dedent("""
## SUA TAREFA
Analise esta empresa como Benjamin Graham faria, aplicando rigorosamente seus critérios de investimento.
Também leve em consideração as análises feitas pelos outros analistas.
Sua análise deve:

1. Avaliar se a empresa atende aos seus critérios quantitativos clássicos:
    - P/L abaixo de 15
    - P/VP abaixo de 1,5
    - Dívida de longo prazo menor que o patrimônio líquido
    - Ativos circulantes pelo menos 1,5x maiores que passivos circulantes
    - Histórico de dividendos consistentes
    - Crescimento de lucros nos últimos anos
    - Ausência de prejuízos nos últimos anos

2. Calcular o valor intrínseco da empresa usando métodos conservadores:
    - Considere apenas lucros passados comprovados, não projeções futuras
    - Aplique múltiplos conservadores
    - Inclua uma margem de segurança substancial

3. Determinar se o preço atual oferece margem de segurança adequada:
    - Compare o preço de mercado com seu valor intrínseco calculado
    - Avalie se o desconto é suficiente para compensar os riscos

4. Concluir se esta empresa seria um investimento adequado segundo seus princípios:
    - Seja direto e objetivo em sua conclusão
    - Explique claramente por que a empresa atende ou não aos seus critérios

## FORMATO DA SUA RESPOSTA
Estruture sua análise em markdown seguindo este formato:

### 1. ANÁLISE INICIAL
- Visão geral da empresa e seu negócio
- Primeiras impressões baseadas nos números apresentados

### 2. AVALIAÇÃO DOS CRITÉRIOS FUNDAMENTAIS
- Análise detalhada de cada critério quantitativo
- Destaque para pontos fortes e fracos nos fundamentos

### 3. CÁLCULO DO VALOR INTRÍNSECO
- Metodologia utilizada (explique seu raciocínio)
- Valor intrínseco calculado
- Margem de segurança em relação ao preço atual

### 4. RISCOS E CONSIDERAÇÕES
- Principais riscos identificados
- Fatores que poderiam comprometer a tese de investimento

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## IMPORTANTE
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- Mantenha o tom formal, metódico e conservador característico de Benjamin Graham
- Seja cético quanto a projeções otimistas e tendências de curto prazo
- Enfatize a importância da margem de segurança em todas as suas considerações
- Baseie-se apenas nos dados concretos fornecidos, não em especulações
- Use sua voz autêntica como Benjamin Graham, referindo-se a si mesmo na primeira pessoa
- Cite ocasionalmente princípios de seus livros para reforçar pontos importantes
""")


_EMPTY = BaseAgentOutput(content="Não Fornecido", sentiment="NEUTRAL", confidence=0)


def _analyze_portfolio(portfolio_data: PortfolioPersonaInput) -> BaseAgentOutput:
    recommendation = _portfolio_recommendation(portfolio_data)
    principal_weakness = portfolio_data.weaknesses[0] if portfolio_data.weaknesses else 'Fragilidade relevante não identificada.'
    risk = portfolio_data.risks[0] if portfolio_data.risks else 'Risco principal não identificado.'
    margin_view = (
        'A estrutura atual preserva alguma margem de segurança na composição.'
        if portfolio_data.overall_score >= 7
        else 'A margem de segurança da carteira está apertada para o meu padrão conservador.'
    )
    content = dedent(f"""
    ## Avaliação Estratégica da Carteira
    Pela minha metodologia, o portfólio exibe **score {portfolio_data.overall_score:.1f}/10** e sentimento **{portfolio_data.portfolio_sentiment}**.
    {margin_view}

    ## Maiores Pontos de Atenção
    Fragilidade dominante: {principal_weakness}
    Maior risco identificado: {risk}

    ## Conclusão
    Minha recomendação objetiva é **{recommendation}**.
    A prioridade deve ser reforçar margem de segurança e disciplina de preço frente ao valor intrínseco.
    """).strip()
    parsed = PortfolioPersonaOutput(
        content=content,
        sentiment=portfolio_data.portfolio_sentiment,
        confidence=max(0, min(100, int(round(portfolio_data.weighted_confidence)))),
        recommendation=recommendation,
    )
    return BaseAgentOutput(content=parsed.content, sentiment=parsed.sentiment, confidence=parsed.confidence)


def _portfolio_recommendation(portfolio_data: PortfolioPersonaInput) -> Literal['MANTER', 'OBSERVAR', 'REBALANCEAR']:
    if portfolio_data.overall_score >= 7.0 and portfolio_data.max_asset_weight <= 30:
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

    stock_details = stocks.details(ticker, market=market)
    company_name = stocks.name(ticker, market=market)
    segment = stock_details.get('segmento_de_atuacao', 'nan')
    multiples = stocks.multiples(ticker, market=market)
    lastest_multiples = multiples[0] if (multiples and isinstance(multiples, list) and len(multiples) > 0) else {}
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'annual', market=market)
    
    # Cálculos seguros de CAGR
    if dre_year and len(dre_year) >= 2:
        receita_cagr = calc_cagr(dre_year, 'receita_liquida', 5)
        lucro_cagr = calc_cagr(dre_year, 'lucro_liquido', 5)
    else:
        receita_cagr = None
        lucro_cagr = None

    _dividends_by_year = stocks.dividends_by_year(ticker, market=market)
    dividends_growth_by_year = []
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
                # filtra anos passados
                dividends_growth_by_year = [d for d in dividends_growth_by_year if d['ano'] < today.year]
        except Exception as e:
            print(f"Erro ao processar dividendos no Polars (Graham): {e}")

    # Lista simples filtrada
    dividends_by_year_filtered = [d for d in _dividends_by_year if d['ano'] < today.year] if _dividends_by_year else []

    balance_sheet_quarter = stocks.balance_sheet(ticker, year_start, year_end, 'quarter', market=market)
    df_balance = pl.DataFrame(balance_sheet_quarter) if (balance_sheet_quarter and len(balance_sheet_quarter) > 0) else None
    
    ncav_status = "Desconhecido"
    if df_balance is not None and "ativo_circulante" in df_balance.columns and "passivo_circulante" in df_balance.columns:
        try:
            ativo_circ = df_balance["ativo_circulante"][0] if len(df_balance) > 0 else 0
            passivo_circ = df_balance["passivo_circulante"][0] if len(df_balance) > 0 else 0
            passivo_nao_circ = df_balance.get_column("passivo_nao_circulante")[0] if ("passivo_nao_circulante" in df_balance.columns and len(df_balance) > 0) else 0
            total_passivo = (ativo_circ * 0) + passivo_circ + passivo_nao_circ # gambiarra pra manter o tipo se for float/null
            
            ncav = ativo_circ - total_passivo
            ncav_status = f"O NCAV atual estimado bruto da companhia é {ncav:,.0f} BRL"
        except Exception:
            ncav_status = "Erro ao calcular NCAV (dados incompletos)"

    classic_criteria = {
        'valor_de_mercado': f'{stock_details.get("valor_de_mercado", float("nan")):,.0f} BRL',
        'preco_sobre_lucro': lastest_multiples.get('p_l', float('nan')),
        'preco_sobre_lucro_abaixo_15x': lastest_multiples.get('p_l', float('nan')) < 15 if lastest_multiples.get('p_l') else False,
        'preco_sobre_valor_patrimonial': lastest_multiples.get('p_vp', float('nan')),
        'preco_sobre_valor_patrimonial_abaixo_1.5x': lastest_multiples.get('p_vp', float('nan')) < 1.5 if lastest_multiples.get('p_vp') else False,
        'receita_cagr_5y': receita_cagr,
        'lucro_cagr_5y': lucro_cagr,
        'divida_bruta': stock_details.get('divida_bruta', float('nan')),
        'patrimonio_liquido': stock_details.get('patrimonio_liquido', float('nan')),
        'divida_menor_que_patrimonio_liquido': stock_details.get('divida_liquida', float('nan'))
        < stock_details.get('patrimonio_liquido', float('nan') + 1) if stock_details.get('divida_liquida') else False,
        'calculo_ncav_graham_puro': ncav_status,
        'lucro_liquido_positivo_nos_ultimos_5_anos': all([d.get('lucro_liquido', 0) > 0 for d in dre_year]) if dre_year else False,
        'crescimento_dividendos_historico': dividends_growth_by_year,
    }

    prompt = dedent(f"""
    Dado o contexto, analise a empresa abaixo prestando extrema atenção no NCAV (cálculo fixo de Ativos Circ Totais subtraídos dos Passivos e Dívidas Totais).
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

    ## CONDIÇÕES GRÁFICAS E MÉDIAS MÓVEIS
    {technical_analysis.content}

    ## DADOS FINANCEIROS DISPONÍVEIS
    {dre_year}

    ## CRITÉRIOS CLÁSSICOS CALCULADOS
    {classic_criteria}
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
