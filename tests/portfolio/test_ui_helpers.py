import pytest

from src.portfolio.ui_helpers import (
    build_portfolio_input,
    composition_rows_for_table,
    get_persona_options,
    sanitize_row,
    sector_market_heatmap_data,
)
from src.portfolio.models import PortfolioAssetAnalysis


def test_get_persona_options_by_market_rules():
    br = get_persona_options({'BR'})
    us = get_persona_options({'US'})
    mixed = get_persona_options({'BR', 'US'})

    assert 'barsi' in br and 'lynch' not in br
    assert 'lynch' in us and 'barsi' not in us
    assert set(mixed.keys()) == {'buffett', 'graham'}


def test_sanitize_row_normalizes_types_and_market():
    row = sanitize_row({'ticker': ' aapl ', 'market': 'xx', 'weight': '12.5', 'quantity': '10', 'avg_price': ''})
    assert row['ticker'] == 'AAPL'
    assert row['market'] == 'BR'
    assert row['weight'] == 12.5
    assert row['quantity'] == 10.0
    assert row['avg_price'] is None


def test_build_portfolio_input_creates_items():
    data = build_portfolio_input(
        rows=[{'ticker': 'petr4', 'market': 'BR', 'weight': 60}, {'ticker': 'aapl', 'market': 'US', 'weight': 40}],
        objective='equilibrio',
        persona='buffett',
        reference_currency='BRL',
    )
    assert len(data.items) == 2
    assert data.items[0].ticker == 'PETR4'
    assert data.persona == 'buffett'


def test_build_portfolio_input_rejects_invalid_rows():
    with pytest.raises(ValueError, match='ticker é obrigatório'):
        build_portfolio_input(
            rows=[{'ticker': '', 'market': 'BR', 'weight': 10}],
            objective='equilibrio',
            persona='buffett',
            reference_currency='BRL',
        )

    with pytest.raises(ValueError, match='peso deve ser maior que zero'):
        build_portfolio_input(
            rows=[{'ticker': 'PETR4', 'market': 'BR', 'weight': 0}],
            objective='equilibrio',
            persona='buffett',
            reference_currency='BRL',
        )


def test_composition_rows_for_table_sorted_and_formatted():
    rows = composition_rows_for_table(
        [
            PortfolioAssetAnalysis(
                ticker='AAPL',
                market='US',
                weight=30,
                normalized_weight=30,
                sentiment='NEUTRAL',
                confidence=50,
                used_cached_analysis=False,
            ),
            PortfolioAssetAnalysis(
                ticker='VALE3',
                market='BR',
                weight=70,
                normalized_weight=70,
                sentiment='BULLISH',
                confidence=80,
                used_cached_analysis=True,
            ),
        ]
    )
    assert rows[0]['Ticker'] == 'VALE3'
    assert rows[0]['Cache'] == 'Sim'
    assert rows[1]['Cache'] == 'Nao'


def test_sector_market_heatmap_data_returns_expected_shape():
    x, y, z = sector_market_heatmap_data({'BR': 60.0, 'US': 40.0}, {'Financeiro': 50.0, 'Tecnologia': 50.0})
    assert x == ['Mercado', 'Setor']
    assert y == ['Concentracao (%)']
    assert len(z) == 1 and len(z[0]) == 2
