import datetime

import polars as pl
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import calc_cagr


def analyze(ticker: str, market: str | None = None) -> str:
    today = datetime.date.today()
    year_start = today.year - 5
    year_end = today.year

    company_name = stocks.name(ticker, market=market)
    segment = stocks.details(ticker, market=market).get('segmento_de_atuacao', 'nan')
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'annual', market=market)
    dre_quarter = stocks.income_statement(ticker, year_start, year_end, 'quarter', market=market)
    balance_sheet_quarter = stocks.balance_sheet(ticker, year_start, year_end, 'quarter', market=market)
    cash_flow = stocks.cash_flow(ticker, year_start, year_end, market=market)
    stock_details = stocks.multiples(ticker, market=market)
    
    # Logs defensivos para debug de conectividade com US provider
    if not (dre_year or dre_quarter): print(f'[financial analyst] AVISO: DRE para {ticker} retornou vazio.')
    if not balance_sheet_quarter: print(f'[financial analyst] AVISO: Balanço para {ticker} retornou vazio.')
    if not cash_flow: print(f'[financial analyst] AVISO: Fluxo de Caixa para {ticker} retornou vazio.')
    if not stock_details: print(f'[financial analyst] AVISO: Múltiplos para {ticker} retornaram vazio.')

    cagr_5y_receita_liq = calc_cagr(dre_year, 'receita_liquida', 5) if dre_year and len(dre_year) >= 2 else None
    cagr_5y_lucro_liq = calc_cagr(dre_year, 'lucro_liquido', 5) if dre_year and len(dre_year) >= 2 else None

    _dividends_by_year = stocks.dividends_by_year(ticker, market=market)
    dividends_growth_by_year = []
    dividends_by_year = []
    if _dividends_by_year and len(_dividends_by_year) > 0:
        try:
            df_divs = pl.DataFrame(_dividends_by_year)
            if 'valor' in df_divs.columns and 'ano' in df_divs.columns:
                dividends_growth_by_year = (
                    df_divs
                    .sort('ano')
                    .with_columns(valor=pl.col('valor').pct_change().round(4))
                    .drop_nulls()
                    .to_dicts()
                )
                dividends_by_year = [d for d in _dividends_by_year if d['ano'] < today.year]
                dividends_growth_by_year = [d for d in dividends_growth_by_year if d['ano'] < today.year]
        except Exception as e:
            print(f'[financial analyst] Erro ao processar dividendos: {e}')
    else:
        dividends_by_year = []
        dividends_growth_by_year = []

    system_message = """
    Você é um analista financeiro especializado em análise fundamentalista de demonstrações financeiras.
    Sua tarefa é analisar objetivamente os dados financeiros fornecidos e extrair conclusões imparciais sobre a qualidade dos números, saúde financeira e desempenho da empresa.

    ## SUA TAREFA
    Analise os dados financeiros fornecidos e produza uma interpretação concisa e objetiva. Sua análise deve:

    1. Identificar tendências significativas nos principais indicadores financeiros
    2. Destacar pontos fortes e fracos evidenciados pelos números
    3. Avaliar a saúde financeira geral da empresa
    4. Fornecer uma conclusão clara e imparcial baseada estritamente nos dados

    ## DIRETRIZES IMPORTANTES
    - Mantenha-se estritamente objetivo e imparcial
    - Baseie-se apenas nos dados fornecidos, sem especulações
    - Evite linguagem promocional ou excessivamente negativa
    - Priorize os indicadores mais relevantes para o tipo de negócio e setor
    - Seja conciso e direto, focando apenas nos pontos mais importantes
    - Não faça recomendações de investimento, apenas interprete os dados

    ## FORMATO DA SUA RESPOSTA
    Sua análise deve ser estruturada em markdown e conter no máximo 500 palavras, seguindo este formato de painéis temáticos:

    ### PONTOS PRINCIPAIS DA ANÁLISE FINANCEIRA
    (Receita, Lucratividade, Crescimento, Remuneração ao acionista, Estrutura de Capital, Solvência, Eficiência Operacional)

    #### CONCLUSÃO
    Uma síntese objetiva em 3-5 frases destacando os aspectos mais relevantes da análise e o que os números indicam sobre a situação atual da empresa.
    Lembre-se: sua análise deve ser factual, imparcial e baseada exclusivamente nos dados fornecidos.
    """

    user_prompt = f"""
    Dado o contexto, analise os dados financeiros da empresa abaixo.
    Ticker: {ticker}
    Nome: {company_name}
    Setor: {segment}

    ## DADOS FINANCEIROS
    ### Demonstração de Resultados (DRE)
    {dre_quarter}

    ### Balanço Patrimonial
    {balance_sheet_quarter}

    ### Fluxo de Caixa Anual
    {cash_flow}

    ### Múltiplos e Indicadores
    {stock_details}

    - cagr_5y_receita_liq: {cagr_5y_receita_liq}
    - cagr_5y_lucro_liq: {cagr_5y_lucro_liq}
    - dividends_by_year: {dividends_by_year}
    - dividends_growth_by_year: {dividends_growth_by_year}


    """

    try:
        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=3,
        )
        response = agent.run(user_prompt)
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
