from src.portfolio.metrics import calculate_concentration_metrics
from src.portfolio.models import PortfolioAssetAnalysis


def _asset(ticker: str, market: str, weight: float, sector: str | None) -> PortfolioAssetAnalysis:
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        weight=weight,
        normalized_weight=weight,
        sentiment='NEUTRAL',
        confidence=50,
        sector=sector,
    )


def test_concentration_high_detects_alerts_and_hhi():
    assets = [
        _asset('AAPL', 'US', 70, 'Technology'),
        _asset('MSFT', 'US', 20, 'Technology'),
        _asset('VALE3', 'BR', 10, 'Materials'),
    ]
    metrics = calculate_concentration_metrics(assets, asset_weight_limit=25.0, market_weight_limit=80.0)
    assert metrics.max_asset_weight == 70.0
    assert metrics.market_weights['US'] == 90.0
    assert metrics.hhi_normalized > 0.0
    assert any('AAPL' in alert for alert in metrics.alerts)
    assert any('mercado US' in alert for alert in metrics.alerts)


def test_concentration_balanced_has_low_alerts():
    assets = [
        _asset('A', 'US', 25, 'Tech'),
        _asset('B', 'US', 25, 'Health'),
        _asset('C', 'BR', 25, 'Finance'),
        _asset('D', 'BR', 25, 'Energy'),
    ]
    metrics = calculate_concentration_metrics(assets)
    assert metrics.max_asset_weight == 25.0
    assert metrics.hhi_normalized < 0.2
    assert not any('acima do limite' in alert for alert in metrics.alerts)


def test_concentration_with_missing_sector_generates_alert():
    assets = [
        _asset('A', 'US', 60, None),
        _asset('B', 'BR', 40, 'Finance'),
    ]
    metrics = calculate_concentration_metrics(assets)
    assert 'Setor não disponível' in metrics.sector_weights
    assert any('Setor não disponível' in alert for alert in metrics.alerts)
