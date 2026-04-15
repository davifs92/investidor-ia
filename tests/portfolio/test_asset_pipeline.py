import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.agents.base import BaseAgentOutput
from src.portfolio.asset_pipeline import analyze_portfolio_asset
from src.portfolio.models import PortfolioItem


def test_uses_recent_report_before_running_analysts(tmp_path: Path):
    reports_file = tmp_path / 'reports.json'
    report_payload = [
        {
            'ticker': 'AAPL',
            'investor_name': 'buffett',
            'generated_at': datetime.now().isoformat(),
            'data': {
                'analysts': {
                    'financial': {'content': 'financeiro cacheado', 'sentiment': 'BULLISH', 'confidence': 90},
                    'valuation': {'content': 'valuation cacheado', 'sentiment': 'NEUTRAL', 'confidence': 70},
                    'technical': {'content': 'tecnico cacheado', 'sentiment': 'BULLISH', 'confidence': 80},
                }
            },
        }
    ]
    reports_file.write_text(json.dumps(report_payload))
    item = PortfolioItem(ticker='AAPL', market='US', weight=100, normalized_weight=100)

    with patch('src.portfolio.asset_pipeline.DB_DIR', tmp_path):
        with patch('src.portfolio.asset_pipeline.cache.get', return_value=None):
            with patch('src.portfolio.asset_pipeline.cache.set', return_value=None):
                with patch('src.portfolio.asset_pipeline.financial.analyze', side_effect=AssertionError('não deveria chamar')):
                    result = analyze_portfolio_asset(item, ttl_seconds=3600, full_analysis=False)

    assert result.used_cached_analysis is True
    assert result.ticker == 'AAPL'
    assert result.confidence > 0
    assert result.financial_summary.startswith('financeiro')


def test_runs_three_analysts_in_default_mode():
    item = PortfolioItem(ticker='MSFT', market='US', weight=60, normalized_weight=60)
    fin = BaseAgentOutput(content='fin', sentiment='BULLISH', confidence=80)
    val = BaseAgentOutput(content='val', sentiment='NEUTRAL', confidence=60)
    tech = BaseAgentOutput(content='tech', sentiment='BULLISH', confidence=70)

    with patch('src.portfolio.asset_pipeline.cache.get', return_value=None):
        with patch('src.portfolio.asset_pipeline._find_recent_report', return_value=None):
            with patch('src.portfolio.asset_pipeline.financial.analyze', return_value=fin) as m_fin:
                with patch('src.portfolio.asset_pipeline.valuation.analyze', return_value=val) as m_val:
                    with patch('src.portfolio.asset_pipeline.technical.analyze', return_value=tech) as m_tech:
                        with patch('src.portfolio.asset_pipeline.cache.set', return_value=None):
                            result = analyze_portfolio_asset(item, ttl_seconds=3600, full_analysis=False)

    assert result.used_cached_analysis is False
    assert result.sentiment == 'BULLISH'
    assert result.confidence == 70
    assert m_fin.called and m_val.called and m_tech.called


def test_runs_full_mode_with_six_analysts():
    item = PortfolioItem(ticker='PETR4', market='BR', weight=40, normalized_weight=40)
    base = BaseAgentOutput(content='x', sentiment='NEUTRAL', confidence=50)

    with patch('src.portfolio.asset_pipeline.cache.get', return_value=None):
        with patch('src.portfolio.asset_pipeline._find_recent_report', return_value=None):
            with patch('src.portfolio.asset_pipeline.financial.analyze', return_value=base):
                with patch('src.portfolio.asset_pipeline.valuation.analyze', return_value=base):
                    with patch('src.portfolio.asset_pipeline.technical.analyze', return_value=base):
                        with patch('src.portfolio.asset_pipeline.news.analyze', return_value=base) as m_news:
                            with patch('src.portfolio.asset_pipeline.macro.analyze', return_value=base) as m_macro:
                                with patch('src.portfolio.asset_pipeline.earnings_release.analyze', return_value=base) as m_earn:
                                    with patch('src.portfolio.asset_pipeline.cache.set', return_value=None):
                                        result = analyze_portfolio_asset(item, ttl_seconds=3600, full_analysis=True)

    assert result.used_cached_analysis is False
    assert result.sentiment == 'NEUTRAL'
    assert m_news.called and m_macro.called and m_earn.called
