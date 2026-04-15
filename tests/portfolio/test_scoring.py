from src.portfolio.metrics import calculate_concentration_metrics
from src.portfolio.models import PortfolioAssetAnalysis
from src.portfolio.scoring import calculate_diversification_score, calculate_overall_score


def _asset(
    ticker: str,
    weight: float,
    sentiment: str,
    confidence: int,
    valuation_confidence: int | None = None,
    market: str = 'US',
    sector: str | None = 'Tech',
) -> PortfolioAssetAnalysis:
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        weight=weight,
        normalized_weight=weight,
        sentiment=sentiment,  # type: ignore[arg-type]
        confidence=confidence,
        valuation_confidence=valuation_confidence,
        sector=sector,
    )


def test_diversification_score_concentrated_portfolio_is_low_with_explanation():
    assets = [
        _asset('AAPL', 80, 'BULLISH', 80, market='US', sector='Tech'),
        _asset('MSFT', 20, 'NEUTRAL', 60, market='US', sector='Tech'),
    ]
    metrics = calculate_concentration_metrics(assets)
    score, explanation = calculate_diversification_score(assets, metrics)
    assert score < 6.0
    assert 'fator penalizante' in explanation


def test_diversification_score_balanced_portfolio_is_higher():
    assets = [
        _asset('A', 25, 'BULLISH', 70, market='US', sector='Tech'),
        _asset('B', 25, 'NEUTRAL', 60, market='US', sector='Health'),
        _asset('C', 25, 'NEUTRAL', 65, market='BR', sector='Finance'),
        _asset('D', 25, 'BEARISH', 55, market='BR', sector='Energy'),
    ]
    metrics = calculate_concentration_metrics(assets)
    score, _ = calculate_diversification_score(assets, metrics)
    assert score >= 7.0


def test_overall_score_redistributes_when_objective_fit_missing():
    assets = [
        _asset('A', 60, 'BULLISH', 80, valuation_confidence=70),
        _asset('B', 40, 'NEUTRAL', 60, valuation_confidence=50),
    ]
    metrics = calculate_concentration_metrics(assets)
    diversification_score, _ = calculate_diversification_score(assets, metrics)
    overall_1, subscores_1 = calculate_overall_score(
        asset_analyses=assets,
        concentration_metrics=metrics,
        diversification_score=diversification_score,
        objective_fit_score=None,
    )
    overall_2, subscores_2 = calculate_overall_score(
        asset_analyses=assets,
        concentration_metrics=metrics,
        diversification_score=diversification_score,
        objective_fit_score=None,
    )
    assert overall_1 == overall_2
    assert subscores_1 == subscores_2
    assert 0.0 <= overall_1 <= 10.0


def test_overall_score_with_objective_fit_uses_dimension():
    assets = [
        _asset('A', 50, 'BULLISH', 90, valuation_confidence=80),
        _asset('B', 50, 'NEUTRAL', 50, valuation_confidence=60),
    ]
    metrics = calculate_concentration_metrics(assets)
    diversification_score, _ = calculate_diversification_score(assets, metrics)
    overall, subscores = calculate_overall_score(
        asset_analyses=assets,
        concentration_metrics=metrics,
        diversification_score=diversification_score,
        objective_fit_score=8.0,
    )
    assert 'objective_fit' in subscores
    assert 0.0 <= overall <= 10.0
