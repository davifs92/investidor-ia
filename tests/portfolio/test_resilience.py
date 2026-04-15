import time
from unittest.mock import patch

from src.portfolio.analyzer import PortfolioAnalyzer
from src.portfolio.models import PortfolioAnalysisInput, PortfolioAssetAnalysis, PortfolioItem


def test_partial_failure_does_not_break_portfolio_analysis():
    def flaky_asset_analyzer(item, full_analysis=False):
        if item.ticker.upper() == 'FAIL':
            raise RuntimeError('ticker inválido para teste')
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or 0.0),
            sentiment='NEUTRAL',
            confidence=55,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=flaky_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='OK1', market='US', weight=40),
            PortfolioItem(ticker='FAIL', market='US', weight=30),
            PortfolioItem(ticker='OK2', market='BR', weight=30),
        ]
    )

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data)

    assert len(output.asset_analyses) == 2
    assert len(output.failed_assets) == 1
    assert output.failed_assets[0].ticker == 'FAIL'
    assert output.failed_assets[0].error_type == 'RuntimeError'
    assert any('falhas parciais' in warning for warning in output.analysis_metadata.warnings)


def test_analyzer_runs_assets_in_parallel():
    def slow_asset_analyzer(item, full_analysis=False):
        time.sleep(0.2)
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=item.weight,
            normalized_weight=float(item.normalized_weight or 0.0),
            sentiment='NEUTRAL',
            confidence=50,
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=slow_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='A', market='US', weight=34),
            PortfolioItem(ticker='B', market='US', weight=33),
            PortfolioItem(ticker='C', market='BR', weight=33),
        ]
    )

    start = time.perf_counter()
    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data)
    elapsed = time.perf_counter() - start

    assert len(output.asset_analyses) == 3
    # Em série seria ~0.6s; com paralelismo esperamos substancialmente menor.
    assert elapsed < 0.55
