from unittest.mock import MagicMock, patch

from src.portfolio.models import PortfolioAssetAnalysis
from src.portfolio.sector_resolver import UNKNOWN_SECTOR, resolve_asset_sectors


def _asset(ticker: str, market: str, sector: str | None = None) -> PortfolioAssetAnalysis:
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        weight=50,
        normalized_weight=50,
        sentiment='NEUTRAL',
        confidence=50,
        sector=sector,
    )


def test_resolves_br_sector_from_provider():
    assets = [_asset('PETR4', 'BR')]
    with patch('src.portfolio.sector_resolver.stocks.details', return_value={'segmento_de_atuacao': 'Petróleo e Gás'}):
        updated, warnings = resolve_asset_sectors(assets)
    assert updated[0].sector == 'Petróleo e Gás'
    assert warnings == []


def test_resolves_us_sector_with_yfinance_fallback():
    assets = [_asset('AAPL', 'US')]
    mock_ticker = MagicMock()
    mock_ticker.info = {'sector': 'Technology'}
    with patch('src.portfolio.sector_resolver.stocks.details', return_value={'segmento_de_atuacao': 'N/A'}):
        with patch('src.portfolio.sector_resolver.yf.Ticker', return_value=mock_ticker):
            updated, warnings = resolve_asset_sectors(assets)
    assert updated[0].sector == 'Technology'
    assert warnings == []


def test_marks_unknown_sector_when_unavailable():
    assets = [_asset('XYZ', 'US')]
    mock_ticker = MagicMock()
    mock_ticker.info = {}
    with patch('src.portfolio.sector_resolver.stocks.details', return_value={'segmento_de_atuacao': 'N/A'}):
        with patch('src.portfolio.sector_resolver.yf.Ticker', return_value=mock_ticker):
            updated, warnings = resolve_asset_sectors(assets)
    assert updated[0].sector == UNKNOWN_SECTOR
    assert any('Setor não disponível' in warning for warning in warnings)
