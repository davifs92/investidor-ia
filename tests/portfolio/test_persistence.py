from pathlib import Path

from src.portfolio.models import (
    PortfolioAnalysisInput,
    PortfolioAnalysisMetadata,
    PortfolioAnalysisOutput,
    PortfolioAssetAnalysis,
    PortfolioConcentrationMetrics,
    PortfolioItem,
)
from src.portfolio import persistence


def _sample_input() -> PortfolioAnalysisInput:
    return PortfolioAnalysisInput(
        items=[PortfolioItem(ticker='VALE3', market='BR', weight=100)],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
        analysis_mode='portfolio',
    )


def _sample_output() -> PortfolioAnalysisOutput:
    return PortfolioAnalysisOutput(
        portfolio_sentiment='NEUTRAL',
        weighted_confidence=60.0,
        concentration_metrics=PortfolioConcentrationMetrics(
            max_asset_weight=100.0,
            market_weights={'BR': 100.0},
            sector_weights={'Materiais': 100.0},
            hhi_normalized=1.0,
            alerts=[],
        ),
        diversification_score=3.5,
        overall_score=4.2,
        subscores={'diversification': 3.5},
        strengths=['forca'],
        weaknesses=['fraqueza'],
        risks=['risco'],
        rebalancing_suggestions=['sugestao'],
        asset_analyses=[
            PortfolioAssetAnalysis(
                ticker='VALE3',
                market='BR',
                weight=100.0,
                normalized_weight=100.0,
                sentiment='NEUTRAL',
                confidence=60,
            )
        ],
        analysis_metadata=PortfolioAnalysisMetadata(),
    )


def test_save_and_list_portfolio_reports(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'DB_DIR', Path(tmp_path))
    report = persistence.save_portfolio_report(
        analysis_input=_sample_input(),
        analysis_output=_sample_output(),
        portfolio_name='Carteira Teste',
    )

    listed = persistence.list_portfolio_reports()
    assert len(listed) == 1
    assert listed[0]['id'] == report['id']
    assert listed[0]['portfolio_name'] == 'Carteira Teste'
    loaded = persistence.get_portfolio_report(report['id'])
    assert loaded is not None
    assert loaded['assets_count'] == 1


def test_save_update_duplicate_delete_portfolio_composition(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'DB_DIR', Path(tmp_path))

    created = persistence.save_portfolio_composition(
        name='Carteira A',
        items=[{'ticker': 'PETR4', 'market': 'BR', 'weight': 60.0}],
        objective='dividendos',
        persona='barsi',
        reference_currency='BRL',
    )
    assert created['name'] == 'Carteira A'

    updated = persistence.save_portfolio_composition(
        name='Carteira A1',
        items=[{'ticker': 'PETR4', 'market': 'BR', 'weight': 50.0}, {'ticker': 'VALE3', 'market': 'BR', 'weight': 50.0}],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
        portfolio_id=created['id'],
    )
    assert updated['id'] == created['id']
    assert len(updated['items']) == 2

    copied = persistence.duplicate_saved_portfolio(created['id'], 'Carteira A copia')
    assert copied['id'] != created['id']
    assert copied['name'] == 'Carteira A copia'

    all_portfolios = persistence.list_saved_portfolios()
    assert len(all_portfolios) == 2

    persistence.mark_portfolio_analyzed(created['id'])
    marked = persistence.get_saved_portfolio(created['id'])
    assert marked is not None
    assert marked.get('last_analyzed_at') is not None

    assert persistence.delete_saved_portfolio(created['id']) is True
    assert persistence.delete_saved_portfolio('nao-existe') is False
    remaining = persistence.list_saved_portfolios()
    assert len(remaining) == 1


def test_save_portfolio_composition_requires_name(tmp_path, monkeypatch):
    monkeypatch.setattr(persistence, 'DB_DIR', Path(tmp_path))
    try:
        persistence.save_portfolio_composition(name='   ', items=[])
    except ValueError as exc:
        assert 'Nome do portfólio é obrigatório' in str(exc)
        return
    raise AssertionError('Era esperado ValueError para nome vazio.')
