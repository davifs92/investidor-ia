from datetime import datetime

from src.portfolio.models import (
    PortfolioAnalysisMetadata,
    PortfolioAnalysisOutput,
    PortfolioAssetAnalysis,
    PortfolioConcentrationMetrics,
)
from src.portfolio.pdf_export import generate_portfolio_pdf_bytes


def test_generate_portfolio_pdf_bytes_returns_pdf_signature():
    output = PortfolioAnalysisOutput(
        portfolio_sentiment='NEUTRAL',
        weighted_confidence=64.2,
        concentration_metrics=PortfolioConcentrationMetrics(
            max_asset_weight=60.0,
            market_weights={'BR': 60.0, 'US': 40.0},
            sector_weights={'Financeiro': 50.0, 'Tecnologia': 50.0},
            hhi_normalized=0.42,
            alerts=['Concentração elevada em ativo.'],
        ),
        diversification_score=5.8,
        overall_score=6.4,
        subscores={'quality_assets': 6.2, 'diversification': 5.8},
        strengths=['Boa dispersão setorial.'],
        weaknesses=['Concentração em um único ativo.'],
        risks=['Sensibilidade cambial.'],
        rebalancing_suggestions=['Reduzir peso de ativo dominante.'],
        persona_analysis='Parecer final da persona para a carteira.',
        asset_analyses=[
            PortfolioAssetAnalysis(
                ticker='VALE3',
                market='BR',
                weight=60.0,
                normalized_weight=60.0,
                sentiment='NEUTRAL',
                confidence=62,
            ),
            PortfolioAssetAnalysis(
                ticker='AAPL',
                market='US',
                weight=40.0,
                normalized_weight=40.0,
                sentiment='BULLISH',
                confidence=70,
            ),
        ],
        analysis_metadata=PortfolioAnalysisMetadata(warnings=['Aviso teste']),
    )

    pdf_bytes = generate_portfolio_pdf_bytes(
        portfolio_name='Carteira XPTO',
        objective='equilibrio',
        persona_name='Warren Buffett',
        output=output,
        generated_at=datetime(2026, 4, 12, 10, 0, 0),
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF')
    assert len(pdf_bytes) > 1200
