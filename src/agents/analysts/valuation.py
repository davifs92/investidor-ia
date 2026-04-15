import polars as pl
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks


def _get_us_peer_candidates(segment: str) -> list[str]:
    segment_l = (segment or '').lower()
    if 'technology' in segment_l or 'software' in segment_l or 'tecnologia' in segment_l:
        return ['AAPL', 'GOOGL', 'META', 'NVDA', 'ORCL', 'ADBE', 'CRM']
    if 'financial' in segment_l or 'bank' in segment_l or 'banc' in segment_l:
        return ['JPM', 'BAC', 'WFC', 'C', 'MS', 'GS']
    if 'health' in segment_l or 'pharma' in segment_l or 'biotech' in segment_l:
        return ['JNJ', 'PFE', 'MRK', 'ABBV', 'LLY', 'AMGN']
    if 'consumer' in segment_l or 'retail' in segment_l:
        return ['AMZN', 'WMT', 'COST', 'HD', 'MCD', 'SBUX']
    if 'industrial' in segment_l:
        return ['CAT', 'GE', 'DE', 'HON', 'ETN', 'MMM']
    if 'energy' in segment_l or 'oil' in segment_l:
        return ['XOM', 'CVX', 'COP', 'SLB', 'EOG']
    return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'NVDA', 'JPM', 'XOM']


def _extract_peer_row(ticker: str) -> dict | None:
    multiples = stocks.multiples(ticker, market='US')
    if not multiples or not isinstance(multiples, list):
        return None
    base = multiples[0]
    row = {
        'ticker': ticker,
        'p_l': base.get('p_l', 0.0) or 0.0,
        'p_vp': base.get('p_vp', 0.0) or 0.0,
        'dy': base.get('dy', 0.0) or 0.0,
        'roe': base.get('roe', 0.0) or 0.0,
        'margem_liquida': base.get('margem_liquida', 0.0) or 0.0,
        'ev_ebitda': base.get('ev_ebitda', 0.0) or 0.0,
    }
    # só considera peer com pelo menos 1 múltiplo válido (> 0)
    if all((row[k] == 0.0 for k in ('p_l', 'p_vp', 'dy', 'roe', 'margem_liquida', 'ev_ebitda'))):
        return None
    return row


def _us_peers_snapshot(segment: str, current_ticker: str) -> tuple[str, str, str]:
    peer_candidates = [t for t in _get_us_peer_candidates(segment) if t != current_ticker.upper()]
    peer_rows = []
    for peer in peer_candidates[:6]:
        row = _extract_peer_row(peer)
        if row:
            peer_rows.append(row)

    if not peer_rows:
        return (
            'N/A (peers US sem dados suficientes no momento)',
            'N/A',
            'N/A',
        )

    peers_df = pl.DataFrame(peer_rows)
    peers_mean = peers_df.mean()
    peers_median = peers_df.median()
    peers_used = ', '.join([r['ticker'] for r in peer_rows])
    peers_used_text = f'Peers usados ({len(peer_rows)}): {peers_used}'
    return str(peers_mean), str(peers_median), peers_used_text


def analyze(ticker: str, market: str | None = None) -> str:
    details = stocks.details(ticker, market=market)
    _screener = stocks.screener(market=market)


    company_name = details['nome']
    segment = details.get('segmento_de_atuacao', 'nan')
    current_price = details.get('preco', float('nan'))
    five_years_historical_multiples = stocks.multiples(ticker, market=market)
    if isinstance(five_years_historical_multiples, list):
        five_years_historical_multiples = five_years_historical_multiples[:5]
    else:
        five_years_historical_multiples = []

    # Guard: screener pode ser vazio para tickers US (screener não implementado p/ US provider)
    # Também verifica se a coluna de segmento existe para evitar erros de filtro
    if _screener:
        screener = (
            pl.DataFrame(_screener)
            .with_columns(stock=pl.col('ticker').str.slice(0, 4))
            .sort('stock', 'liquidezmediadiaria')
            .unique('stock', keep='last')
            .filter(pl.col('price') > 0, pl.col('liquidezmediadiaria') > 0)
        )
        
        # Fallback: se não houver coluna de segmento, usa a média geral do mercado
        if 'segmentname' in screener.columns:
            sector_multiples_mean = screener.filter(pl.col('segmentname') == segment).mean()
            sector_multiples_median = screener.filter(pl.col('segmentname') == segment).median()
        else:
            sector_multiples_mean = "N/A (Segmento não disponível nos dados atuais)"
            sector_multiples_median = "N/A"
            
        total_market_multiples_median = screener.median()
    else:
        if market == 'US':
            (
                sector_multiples_mean,
                sector_multiples_median,
                total_market_multiples_median,
            ) = _us_peers_snapshot(segment, ticker)
        else:
            sector_multiples_mean = 'N/A (dados de setor não disponíveis para este mercado)'
            sector_multiples_median = 'N/A'
            total_market_multiples_median = 'N/A (screener não disponível para este mercado)'

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
