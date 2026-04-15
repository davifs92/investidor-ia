import pytest
from unittest.mock import patch

from src.agents.investors import barsi, buffett, graham, lynch
from src.portfolio.analyzer import PortfolioAnalyzer
from src.portfolio.models import (
    PortfolioAnalysisInput,
    PortfolioAssetAnalysis,
    PortfolioItem,
)
from src.portfolio.persona_interface import PortfolioPersonaInput


def _persona_input(market_weights: dict[str, float]) -> PortfolioPersonaInput:
    return PortfolioPersonaInput(
        persona='buffett',
        objective='equilibrio',
        portfolio_sentiment='NEUTRAL',
        weighted_confidence=66.0,
        overall_score=6.2,
        diversification_score=6.0,
        market_weights=market_weights,
        max_asset_weight=31.0,
        hhi_normalized=0.21,
        strengths=['forca'],
        weaknesses=['fraqueza'],
        risks=['risco principal'],
        rebalancing_suggestions=['sugestao'],
    )


def test_portfolio_mode_generates_persona_text_for_buffett_and_graham():
    b = buffett.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'BR': 60.0, 'US': 40.0}))
    g = graham.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'BR': 60.0, 'US': 40.0}))

    assert 'vantagem competitiva' in b.content.lower()
    assert 'margem de segurança' in g.content.lower()


def test_portfolio_mode_generates_persona_text_for_barsi_and_lynch():
    b = barsi.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'BR': 100.0}))
    l = lynch.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'US': 100.0}))

    assert 'renda' in b.content.lower()
    assert 'garp' in l.content.lower()


def test_barsi_portfolio_mode_rejects_us_market_weight():
    with pytest.raises(ValueError, match='apenas carteira BR'):
        barsi.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'US': 100.0}))


def test_lynch_portfolio_mode_rejects_br_market_weight():
    with pytest.raises(ValueError, match='apenas carteira US'):
        lynch.analyze(analysis_mode='portfolio', portfolio_data=_persona_input({'BR': 100.0}))


def test_analyzer_auto_uses_persona_when_persona_is_provided():
    def fake_asset(item, full_analysis=False):
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or item.weight),
            sentiment='NEUTRAL',
            confidence=55,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=fake_asset)
    data = PortfolioAnalysisInput(items=[PortfolioItem(ticker='VALE3', market='BR', weight=100)], persona='buffett')

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            with patch('src.portfolio.analyzer.consolidate_portfolio_by_persona', return_value='Parecer persona'):
                output = analyzer.analyze(data)

    assert output.persona_analysis == 'Parecer persona'
