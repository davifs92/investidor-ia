from src.portfolio.aggregator import aggregate_portfolio_signals
from src.portfolio.models import PortfolioAssetAnalysis


def _asset(ticker: str, weight: float, sentiment: str, confidence: int) -> PortfolioAssetAnalysis:
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market='US',
        weight=weight,
        normalized_weight=weight,
        sentiment=sentiment,  # type: ignore[arg-type]
        confidence=confidence,
    )


def test_aggregate_all_bullish():
    assets = [_asset('A', 50, 'BULLISH', 80), _asset('B', 50, 'BULLISH', 60)]
    breakdown, weighted_conf, sentiment = aggregate_portfolio_signals(assets)
    assert sentiment == 'BULLISH'
    assert breakdown['BULLISH'] == 100.0
    assert weighted_conf == 70.0


def test_aggregate_all_bearish():
    assets = [_asset('A', 40, 'BEARISH', 90), _asset('B', 60, 'BEARISH', 30)]
    breakdown, weighted_conf, sentiment = aggregate_portfolio_signals(assets)
    assert sentiment == 'BEARISH'
    assert breakdown['BEARISH'] == 100.0
    assert weighted_conf == 54.0


def test_aggregate_mixed_portfolio():
    assets = [
        _asset('A', 50, 'BULLISH', 80),
        _asset('B', 30, 'NEUTRAL', 50),
        _asset('C', 20, 'BEARISH', 40),
    ]
    breakdown, weighted_conf, sentiment = aggregate_portfolio_signals(assets)
    assert round(breakdown['BULLISH'], 2) == 50.0
    assert round(breakdown['NEUTRAL'], 2) == 30.0
    assert round(breakdown['BEARISH'], 2) == 20.0
    assert weighted_conf == 63.0
    assert sentiment == 'NEUTRAL'
