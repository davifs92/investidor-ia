import pytest
import pandas as pd
from datetime import datetime

from src.market_router import MarketRouter
from src.data_providers.us.provider import USDataProvider
from src.data_providers.br.provider import BRDataProvider


def test_market_router_returns_correct_provider():
    """Garante que o sufixo do Ticker invoque os objetos certos de Provider."""
    br_provider = MarketRouter.get_provider("PETR4.SA")
    us_provider = MarketRouter.get_provider("AAPL")

    assert isinstance(br_provider, BRDataProvider), "O provedor .SA não é o BRDataProvider"
    assert isinstance(us_provider, USDataProvider), "O provedor sem sufixo não é o USDataProvider"

def test_us_data_provider_normalize_df():
    """Garante que o dataframe pandas da API do YFinance resulte na formatação requerida pelos Analysts em PT-BR."""
    provider = USDataProvider()
    
    # Criando um DataFrame Mock como yfinance retornaria 
    # Linhas = Métricas (Total Revenue, Net Income), Colunas = Datas
    dates = [datetime(2023, 12, 31), datetime(2022, 12, 31)]
    data = {
        dates[0]: {'Total Revenue': 1500.0, 'Net Income': 500.0},
        dates[1]: {'Total Revenue': 1200.0, 'Net Income': 400.0}
    }
    mock_df = pd.DataFrame(data)

    mapping = {
        'receita_liquida': 'Total Revenue',
        'lucro_liquido': 'Net Income'
    }

    normalized = provider._normalize_df(mock_df, mapping)
    
    # Verifica se deve retornar uma Lista de Dicionários convertidos com chaves pt_BR e ordem (Recente p/ Velho)
    assert isinstance(normalized, list)
    assert len(normalized) == 2
    
    # A data mais recente (2023) tem precedência de sort (reverse=True)
    assert normalized[0]['data'] == '2023-12-31'
    assert normalized[0]['receita_liquida'] == 1500.0
    assert normalized[0]['lucro_liquido'] == 500.0
    
    assert normalized[1]['data'] == '2022-12-31'
    assert normalized[1]['lucro_liquido'] == 400.0

def test_us_provider_earnings_release_stub():
    """Garante que caso o EDGAR não devolva nada, a string default não deixe o código quebrar em None."""
    provider = USDataProvider()
    texto = provider.earnings_release_text("MOCKTICKER")
    assert "Earnings Release" in texto or "SEC EDGAR" in texto
    assert isinstance(texto, str)
