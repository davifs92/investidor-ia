import pytest

from src.portfolio.models import PortfolioAnalysisInput, PortfolioItem
from src.portfolio.validators import PortfolioValidationError, validate_portfolio_input


def test_rejects_empty_portfolio():
    data = PortfolioAnalysisInput(items=[])
    with pytest.raises(PortfolioValidationError) as exc:
        validate_portfolio_input(data)
    assert 'Carteira vazia' in str(exc.value)


def test_rejects_missing_ticker():
    data = PortfolioAnalysisInput(items=[PortfolioItem(ticker=' ', market='BR', weight=50)])
    with pytest.raises(PortfolioValidationError) as exc:
        validate_portfolio_input(data)
    assert 'sem ticker informado' in str(exc.value)


def test_rejects_negative_weight():
    data = PortfolioAnalysisInput(items=[PortfolioItem(ticker='PETR4', market='BR', weight=-10)])
    with pytest.raises(PortfolioValidationError) as exc:
        validate_portfolio_input(data)
    assert 'peso negativo' in str(exc.value)


def test_rejects_invalid_market_via_model_validation():
    with pytest.raises(Exception):
        PortfolioItem(ticker='AAPL', market='AR', weight=10)  # type: ignore[arg-type]


def test_rejects_total_weight_less_or_equal_zero():
    data = PortfolioAnalysisInput(
        items=[
            PortfolioItem(ticker='PETR4', market='BR', weight=0),
            PortfolioItem(ticker='VALE3', market='BR', weight=0),
        ]
    )
    with pytest.raises(PortfolioValidationError) as exc:
        validate_portfolio_input(data)
    assert 'Soma total de pesos' in str(exc.value)


def test_warns_when_portfolio_has_more_than_20_assets():
    items = [PortfolioItem(ticker=f'TK{i}', market='US', weight=1) for i in range(21)]
    data = PortfolioAnalysisInput(items=items)
    warnings = validate_portfolio_input(data, max_assets=20)
    assert len(warnings) == 1
    assert 'pode demorar mais' in warnings[0]
