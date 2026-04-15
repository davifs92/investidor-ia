from unittest.mock import patch

from src.portfolio.analyzer import PortfolioAnalyzer
from src.portfolio.models import PortfolioAnalysisInput, PortfolioAnalysisOutput, PortfolioItem
from src.portfolio.validators import PortfolioValidationError


def test_analyzer_runs_base_pipeline_and_returns_output():
    def fake_asset_analyzer(item, full_analysis=False):
        return {
            'PETR4': (80, 'BULLISH'),
            'AAPL': (60, 'NEUTRAL'),
        }.get(item.ticker, (0, 'NEUTRAL'))

    def build_output(item, full_analysis=False):
        confidence, sentiment = fake_asset_analyzer(item, full_analysis=full_analysis)
        from src.portfolio.models import PortfolioAssetAnalysis

        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or 0),
            sentiment=sentiment,
            confidence=confidence,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=build_output)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='PETR4', market='BR', weight=70),
            PortfolioItem(ticker='AAPL', market='US', weight=30),
        ],
        reference_currency='BRL',
        analysis_mode='portfolio',
    )

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data)

    assert isinstance(output, PortfolioAnalysisOutput)
    assert len(output.asset_analyses) == 2
    assert abs(sum(a.normalized_weight for a in output.asset_analyses) - 100.0) <= 1e-6
    assert output.analysis_metadata.reference_currency == 'BRL'
    assert output.analysis_metadata.analysis_mode == 'portfolio'
    assert output.persona_analysis is None
    assert output.portfolio_sentiment in {'BULLISH', 'NEUTRAL'}
    assert output.weighted_confidence > 0
    assert set(output.sentiment_breakdown.keys()) == {'BULLISH', 'NEUTRAL', 'BEARISH'}
    assert output.diversification_score is not None
    assert output.overall_score is not None
    assert isinstance(output.subscores, dict) and 'diversification' in output.subscores
    assert isinstance(output.objective_fit, dict) and 'score' in output.objective_fit
    assert len(output.strengths) >= 1
    assert len(output.rebalancing_suggestions) >= 1


def test_analyzer_supports_optional_persona_consolidator():
    from src.portfolio.models import PortfolioAssetAnalysis

    def build_output(item, full_analysis=False):
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or 0),
            sentiment='NEUTRAL',
            confidence=50,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=build_output)
    data = PortfolioAnalysisInput(
        items=[PortfolioItem(ticker='VALE3', market='BR', weight=100)],
    )

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data, persona_consolidator=lambda result: f'Parecer com {len(result.asset_analyses)} ativo(s).')

    assert output.persona_analysis == 'Parecer com 1 ativo(s).'


def test_analyzer_preserves_warnings_from_validation_and_pricing():
    from src.portfolio.models import PortfolioAssetAnalysis

    def build_output(item, full_analysis=False):
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or 0),
            sentiment='NEUTRAL',
            confidence=40,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=build_output)
    data = PortfolioAnalysisInput(
        items=[PortfolioItem(ticker=f'TK{i}', market='US', weight=1) for i in range(21)]
    )

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data)

    assert any('pode demorar mais' in warning for warning in output.analysis_metadata.warnings)


def test_analyzer_raises_validation_error_for_invalid_input():
    analyzer = PortfolioAnalyzer()
    invalid = PortfolioAnalysisInput(items=[])
    try:
        analyzer.analyze(invalid)
    except PortfolioValidationError:
        return
    raise AssertionError('Era esperado PortfolioValidationError para carteira vazia.')
