from src.portfolio.models import (
    PortfolioAnalysisMetadata,
    PortfolioAnalysisOutput,
    PortfolioAssetAnalysis,
    PortfolioConcentrationMetrics,
)
from src.portfolio.persona_interface import build_portfolio_persona_input


def test_build_portfolio_persona_input_maps_output_fields():
    output = PortfolioAnalysisOutput(
        portfolio_sentiment='BULLISH',
        weighted_confidence=72.4,
        diversification_score=6.8,
        overall_score=7.3,
        subscores={'diversification': 6.8, 'objective_fit': 7.1},
        objective_fit={'objective': 'equilibrio', 'score': 7.1},
        strengths=['forca 1'],
        weaknesses=['fraqueza 1'],
        risks=['risco 1'],
        rebalancing_suggestions=['sug 1'],
        concentration_metrics=PortfolioConcentrationMetrics(
            max_asset_weight=32.0,
            market_weights={'BR': 60.0, 'US': 40.0},
            hhi_normalized=0.23,
        ),
        asset_analyses=[
            PortfolioAssetAnalysis(
                ticker='AAPL',
                market='US',
                weight=50,
                normalized_weight=55.0,
                sentiment='BULLISH',
                confidence=80,
            ),
            PortfolioAssetAnalysis(
                ticker='VALE3',
                market='BR',
                weight=50,
                normalized_weight=45.0,
                sentiment='NEUTRAL',
                confidence=60,
            ),
        ],
        analysis_metadata=PortfolioAnalysisMetadata(),
    )

    persona_input = build_portfolio_persona_input(output=output, persona='buffett')

    assert persona_input.persona == 'buffett'
    assert persona_input.objective == 'equilibrio'
    assert persona_input.overall_score == 7.3
    assert persona_input.market_weights == {'BR': 60.0, 'US': 40.0}
    assert len(persona_input.top_holdings) == 2
    assert persona_input.top_holdings[0].ticker == 'AAPL'
