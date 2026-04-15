from unittest.mock import patch

from src.portfolio.models import PortfolioItem
from src.portfolio.price_fetcher import enrich_portfolio_prices


def test_uses_manual_weights_when_quantity_not_informed():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=70),
        PortfolioItem(ticker='VALE3', market='BR', weight=30),
    ]

    with patch('src.portfolio.price_fetcher._fetch_last_close', return_value=10.0):
        enriched, warnings = enrich_portfolio_prices(items, reference_currency='BRL')

    assert warnings == []
    assert abs((enriched[0].normalized_weight or 0) - 70.0) <= 1e-6
    assert abs((enriched[1].normalized_weight or 0) - 30.0) <= 1e-6
    assert enriched[0].current_price == 10.0
    assert enriched[1].current_price == 10.0


def test_uses_market_value_when_all_positions_have_quantity_and_converts_currency():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=50, quantity=10),
        PortfolioItem(ticker='AAPL', market='US', weight=50, quantity=10),
    ]

    def fake_close(symbol: str) -> float:
        if symbol == 'PETR4.SA':
            return 30.0
        if symbol == 'AAPL':
            return 200.0
        if symbol == 'BRL=X':
            return 5.0
        raise AssertionError(f'Símbolo inesperado: {symbol}')

    with patch('src.portfolio.price_fetcher._fetch_last_close', side_effect=fake_close):
        enriched, warnings = enrich_portfolio_prices(items, reference_currency='BRL')

    assert warnings == []
    # BR: 10*30 = 300 BRL | US: 10*200 USD => 2000*5 = 10000 BRL
    assert abs((enriched[0].market_value or 0) - 300.0) <= 1e-6
    assert abs((enriched[1].market_value or 0) - 10000.0) <= 1e-6
    assert abs((enriched[0].normalized_weight or 0) - (300.0 / 10300.0 * 100.0)) <= 1e-6
    assert abs((enriched[1].normalized_weight or 0) - (10000.0 / 10300.0 * 100.0)) <= 1e-6


def test_falls_back_to_manual_weight_when_price_fetch_fails():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=60, quantity=10),
        PortfolioItem(ticker='VALE3', market='BR', weight=40, quantity=10),
    ]

    def fake_close(symbol: str) -> float:
        if symbol == 'PETR4.SA':
            raise ValueError('rate limited')
        return 50.0

    with patch('src.portfolio.price_fetcher._fetch_last_close', side_effect=fake_close):
        enriched, warnings = enrich_portfolio_prices(items, reference_currency='BRL')

    assert len(warnings) == 1
    assert 'Falha ao obter preço de PETR4' in warnings[0]
    assert abs((enriched[0].normalized_weight or 0) - 60.0) <= 1e-6
    assert abs((enriched[1].normalized_weight or 0) - 40.0) <= 1e-6


def test_falls_back_to_manual_weight_when_fx_fails_for_mixed_portfolio():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=60, quantity=10),
        PortfolioItem(ticker='AAPL', market='US', weight=40, quantity=10),
    ]

    def fake_close(symbol: str) -> float:
        if symbol == 'PETR4.SA':
            return 30.0
        if symbol == 'AAPL':
            return 200.0
        if symbol == 'BRL=X':
            raise ValueError('fx unavailable')
        raise AssertionError(f'Símbolo inesperado: {symbol}')

    with patch('src.portfolio.price_fetcher._fetch_last_close', side_effect=fake_close):
        enriched, warnings = enrich_portfolio_prices(items, reference_currency='BRL')

    assert len(warnings) == 1
    assert 'Falha ao obter cotação USD/BRL' in warnings[0]
    assert abs((enriched[0].normalized_weight or 0) - 60.0) <= 1e-6
    assert abs((enriched[1].normalized_weight or 0) - 40.0) <= 1e-6
