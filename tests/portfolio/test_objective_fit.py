from src.portfolio.metrics import calculate_concentration_metrics
from src.portfolio.models import PortfolioAssetAnalysis
from src.portfolio.objective_fit import evaluate_objective_fit


def _asset(ticker: str, weight: float, sentiment: str, confidence: int, fin: str = '', val: str = '', tech: str = ''):
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market='US',
        weight=weight,
        normalized_weight=weight,
        sentiment=sentiment,  # type: ignore[arg-type]
        confidence=confidence,
        financial_summary=fin,
        valuation_summary=val,
        technical_summary=tech,
    )


def test_objective_dividendos_with_lynch_adds_inconsistency_alert():
    assets = [
        _asset('A', 60, 'NEUTRAL', 70, fin='dividend yield forte'),
        _asset('B', 40, 'NEUTRAL', 65, fin='renda com dividendos'),
    ]
    metrics = calculate_concentration_metrics(assets)
    result = evaluate_objective_fit('dividendos', 'lynch', assets, metrics)
    assert any('Inconsistência' in alert for alert in result['alerts'])


def test_objective_crescimento_with_growth_profile_has_higher_score():
    assets = [
        _asset('A', 70, 'BULLISH', 80, val='growth acelerado'),
        _asset('B', 30, 'NEUTRAL', 60, val='tese de crescimento'),
    ]
    metrics = calculate_concentration_metrics(assets)
    result = evaluate_objective_fit('crescimento', 'lynch', assets, metrics)
    assert result['score'] >= 6.0
    assert result['alignment'] in {'moderado', 'alto'}


def test_objective_conservador_penalizes_bearish_and_concentration():
    assets = [
        _asset('A', 80, 'BEARISH', 40),
        _asset('B', 20, 'NEUTRAL', 50),
    ]
    metrics = calculate_concentration_metrics(assets)
    result = evaluate_objective_fit('longo_prazo_conservador', 'buffett', assets, metrics)
    assert result['score'] <= 5.5
    assert len(result['alerts']) >= 1
