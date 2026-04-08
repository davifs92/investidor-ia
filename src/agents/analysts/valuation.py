import polars as pl
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks


def analyze(ticker: str) -> str:
    details = stocks.details(ticker)
    _screener = stocks.screener()


    company_name = details['nome']
    segment = details.get('segmento_de_atuacao', 'nan')
    current_price = details.get('preco', float('nan'))
    five_years_historical_multiples = stocks.multiples(ticker)[:5]

    # Guard: screener pode ser vazio para tickers US (screener não implementado p/ US provider)
    if _screener:
        screener = (
            pl.DataFrame(_screener)
            .with_columns(stock=pl.col('ticker').str.slice(0, 4))
            .sort('stock', 'liquidezmediadiaria')
            .unique('stock', keep='last')
            .filter(pl.col('price') > 0, pl.col('liquidezmediadiaria') > 0)
        )
        sector_multiples_mean = screener.filter(pl.col('segmentname') == segment).mean()
        sector_multiples_median = screener.filter(pl.col('segmentname') == segment).median()
        total_market_multiples_median = screener.median()
    else:
        sector_multiples_mean = 'N/A (dados de setor não disponíveis para este mercado)'
        sector_multiples_median = 'N/A'
        total_market_multiples_median = 'N/A (screener não disponível para mercado US)'

    system_message = """
    Você é um analista especializado em valuation relativo de empresas. 
    Sua tarefa é analisar se a empresa está cara ou barata utilizando métricas de múltiplos.

    ## SUA TAREFA
    1. Comparação Direta com o Setor e prêmios/descontos.
    2. Comparação Histórica com a própria média.
    3. Comparação com o Mercado em Geral.
    4. Leve em conta o estagio da empresa (P/L, EV/EBITDA, ROIC).

    ## DIRETRIZES IMPORTANTES
    - Foque exclusivamente em indicadores objetivos.
    - Evite modelos de desconto (DCF). Foque no panorama relativo.
    - Não faça recomendações diretas de compra ou venda, crie um relatório.

    ## FORMATO DA SUA RESPOSTA
    Sua análise deve ser estruturada em markdown. Você pode desenhar seções de valuation e comparações. 
    Finalize com uma conclusão sintética.
    """

    user_prompt = f"""
    Faça uma Análise de Valuation Relativo da Empresa abaixo.
    Ticker: {ticker}
    Nome: {company_name}
    Setor: {segment}
    Preço Atual: {current_price}

    ### Múltiplos Históricos da Empresa (5 anos)
    {five_years_historical_multiples}

    ### Múltiplos do Setor (média)
    {sector_multiples_mean}

    ### Múltiplos do Setor (mediana)
    {sector_multiples_median}

    ### Múltiplos do Mercado Geral (mediana)
    {total_market_multiples_median}
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
