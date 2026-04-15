from unittest.mock import patch

from src.portfolio.analyzer import PortfolioAnalyzer
from src.portfolio.models import PortfolioAnalysisInput, PortfolioAssetAnalysis, PortfolioItem


def test_analyzer_emits_progress_events_for_success_failure_and_cache():
    def fake_asset_analyzer(item, full_analysis=False):
        if item.ticker == 'FAIL1':
            raise RuntimeError('quebra simulada')
        return PortfolioAssetAnalysis(
            ticker=item.ticker,
            market=item.market,
            weight=float(item.weight),
            normalized_weight=float(item.normalized_weight or item.weight),
            sentiment='NEUTRAL',
            confidence=50,
            used_cached_analysis=(item.ticker == 'CASH3'),
        )

    analyzer = PortfolioAnalyzer(asset_analyzer=fake_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='CASH3', market='BR', weight=40),
            PortfolioItem(ticker='FAIL1', market='US', weight=30),
            PortfolioItem(ticker='OKAY3', market='BR', weight=30),
        ],
        analysis_mode='portfolio',
    )

    events: list[dict] = []

    with patch('src.portfolio.analyzer.enrich_portfolio_prices', return_value=(data.items, [])):
        with patch('src.portfolio.analyzer.resolve_asset_sectors', side_effect=lambda assets: (assets, [])):
            output = analyzer.analyze(data, progress_callback=lambda event: events.append(event))

    queued = [e for e in events if e.get('status') == 'queued']
    running = [e for e in events if e.get('status') == 'running']
    done = [e for e in events if e.get('status') == 'done']
    failed = [e for e in events if e.get('status') == 'failed']

    assert len(queued) == 3
    assert len(running) == 3
    assert len(done) == 2
    assert len(failed) == 1
    assert any(e.get('used_cached_analysis') is True for e in done)
    assert failed[0].get('ticker') == 'FAIL1'
    assert len(output.asset_analyses) == 2
    assert len(output.failed_assets) == 1
