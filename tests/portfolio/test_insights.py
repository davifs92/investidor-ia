from src.portfolio.insights import generate_portfolio_insights
from src.portfolio.metrics import calculate_concentration_metrics
from src.portfolio.models import PortfolioAssetAnalysis


def _asset(ticker: str, weight: float, sentiment: str, confidence: int, market: str = 'US', sector: str | None = 'Tech'):
    return PortfolioAssetAnalysis(
        ticker=ticker,
        market=market,  # type: ignore[arg-type]
        weight=weight,
        normalized_weight=weight,
        sentiment=sentiment,  # type: ignore[arg-type]
        confidence=confidence,
        sector=sector,
    )


def test_insights_are_data_driven_with_concentrated_bearish_case():
    assets = [
        _asset('AAPL', 60, 'BEARISH', 55, market='US', sector='Tech'),
        _asset('PETR4', 40, 'NEUTRAL', 60, market='BR', sector='Energy'),
    ]
    metrics = calculate_concentration_metrics(assets)
    breakdown = {'BULLISH': 0.0, 'NEUTRAL': 40.0, 'BEARISH': 60.0}
    objective_fit = {'score': 4.0, 'alignment': 'baixo', 'alerts': ['Objetivo desalinhado.']}

    result = generate_portfolio_insights(
        asset_analyses=assets,
        concentration_metrics=metrics,
        sentiment_breakdown=breakdown,
        objective_fit=objective_fit,
        persona='graham',
    )

    assert any('AAPL' in s for s in result['weaknesses'] + result['rebalancing_suggestions'])
    assert any('desalinhado' in r.lower() or 'objetivo' in r.lower() for r in result['risks'])
    assert len(result['strengths']) >= 3
    assert len(result['weaknesses']) >= 3
    assert len(result['risks']) >= 3
    assert len(result['rebalancing_suggestions']) >= 3


def test_insights_persona_tone_changes_suggestion_prefix():
    assets = [
        _asset('VALE3', 50, 'BULLISH', 70, market='BR', sector='Materials'),
        _asset('ITUB4', 50, 'NEUTRAL', 65, market='BR', sector='Finance'),
    ]
    metrics = calculate_concentration_metrics(assets)
    breakdown = {'BULLISH': 50.0, 'NEUTRAL': 50.0, 'BEARISH': 0.0}
    objective_fit = {'score': 8.0, 'alignment': 'alto', 'alerts': []}

    barsi_result = generate_portfolio_insights(assets, metrics, breakdown, objective_fit, persona='barsi')
    lynch_result = generate_portfolio_insights(assets, metrics, breakdown, objective_fit, persona='lynch')

    assert any('renda e disciplina de dividendos' in s for s in barsi_result['rebalancing_suggestions'])
    assert any('GARP' in s for s in lynch_result['rebalancing_suggestions'])
