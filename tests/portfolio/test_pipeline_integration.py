from unittest.mock import patch

from src.portfolio.analyzer import PortfolioAnalyzer
from src.portfolio.models import PortfolioAnalysisInput, PortfolioAssetAnalysis, PortfolioItem
from src.portfolio.pdf_export import generate_portfolio_pdf_bytes


def _fake_asset_analyzer(item, full_analysis=False):
    sentiment = 'BULLISH' if item.ticker.upper().startswith('A') else 'NEUTRAL'
    confidence = 75 if sentiment == 'BULLISH' else 55
    return PortfolioAssetAnalysis(
        ticker=item.ticker.upper(),
        market=item.market,
        weight=float(item.weight),
        normalized_weight=float(item.normalized_weight or 0.0),
        sentiment=sentiment,
        confidence=confidence,
        financial_summary='Resumo financeiro',
        valuation_summary='Resumo valuation',
        technical_summary='Resumo técnico',
        valuation_confidence=65,
        sector='Tecnologia' if item.market == 'US' else 'Financeiro',
        used_cached_analysis=False,
    )


def test_pipeline_integration_complete_valid_portfolio():
    analyzer = PortfolioAnalyzer(asset_analyzer=_fake_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='AAPL', market='US', weight=50),
            PortfolioItem(ticker='ITUB4', market='BR', weight=50),
        ],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
        analysis_mode='portfolio',
    )

    with patch('src.portfolio.price_fetcher._fetch_last_close', return_value=10.0):
        output = analyzer.analyze(data)

    assert len(output.asset_analyses) == 2
    assert output.overall_score is not None
    assert output.diversification_score is not None
    assert isinstance(output.persona_analysis, str) and len(output.persona_analysis) > 0


def test_pipeline_integration_partial_failure():
    def flaky(item, full_analysis=False):
        if item.ticker.upper() == 'FAIL':
            raise TimeoutError('timeout simulado')
        return _fake_asset_analyzer(item, full_analysis=full_analysis)

    analyzer = PortfolioAnalyzer(asset_analyzer=flaky)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='AAPL', market='US', weight=40),
            PortfolioItem(ticker='FAIL', market='US', weight=30),
            PortfolioItem(ticker='BBAS3', market='BR', weight=30),
        ],
        objective='equilibrio',
        persona='graham',
    )

    with patch('src.portfolio.price_fetcher._fetch_last_close', return_value=10.0):
        output = analyzer.analyze(data)

    assert len(output.asset_analyses) == 2
    assert len(output.failed_assets) == 1
    assert output.failed_assets[0].ticker == 'FAIL'
    assert any('falhas parciais' in w for w in output.analysis_metadata.warnings)


def test_pipeline_integration_mixed_br_us_with_fx_conversion():
    analyzer = PortfolioAnalyzer(asset_analyzer=_fake_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='PETR4', market='BR', weight=10, quantity=10),
            PortfolioItem(ticker='AAPL', market='US', weight=90, quantity=1),
        ],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
    )

    def fake_close(ticker: str) -> float:
        prices = {'PETR4.SA': 10.0, 'AAPL': 20.0, 'BRL=X': 5.0}
        return prices[ticker]

    with patch('src.portfolio.price_fetcher._fetch_last_close', side_effect=fake_close):
        output = analyzer.analyze(data)

    weights = {a.ticker: float(a.normalized_weight) for a in output.asset_analyses}
    assert round(weights['PETR4'], 2) == 50.0
    assert round(weights['AAPL'], 2) == 50.0


def test_pipeline_integration_normalization_and_score_end_to_end():
    analyzer = PortfolioAnalyzer(asset_analyzer=_fake_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='ABEV3', market='BR', weight=8),
            PortfolioItem(ticker='MSFT', market='US', weight=2),
        ],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
    )

    # força fallback para pesos manuais normalizados
    with patch('src.portfolio.price_fetcher._fetch_last_close', side_effect=RuntimeError('sem dados')):
        output = analyzer.analyze(data)

    total_weight = sum(float(a.normalized_weight) for a in output.asset_analyses)
    assert round(total_weight, 6) == 100.0
    assert output.overall_score is not None and 0.0 <= float(output.overall_score) <= 10.0
    assert output.diversification_score is not None and 0.0 <= float(output.diversification_score) <= 10.0
    assert isinstance(output.subscores, dict) and 'diversification' in output.subscores


def test_pipeline_integration_generate_pdf_from_output():
    analyzer = PortfolioAnalyzer(asset_analyzer=_fake_asset_analyzer)
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='AAPL', market='US', weight=60),
            PortfolioItem(ticker='BBAS3', market='BR', weight=40),
        ],
        objective='crescimento',
        persona='buffett',
        reference_currency='BRL',
    )

    with patch('src.portfolio.price_fetcher._fetch_last_close', return_value=10.0):
        output = analyzer.analyze(data)

    pdf_bytes = generate_portfolio_pdf_bytes(
        portfolio_name='Carteira Integração',
        objective='crescimento',
        persona_name='Warren Buffett',
        output=output,
    )
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')
