import pytest

from src.portfolio.models import PortfolioItem
from src.portfolio.normalizers import normalize_portfolio_weights


def test_normalization_keeps_100_sum_when_already_100():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=60),
        PortfolioItem(ticker='VALE3', market='BR', weight=40),
    ]
    normalized = normalize_portfolio_weights(items)
    total = sum(item.normalized_weight or 0 for item in normalized)
    assert abs(total - 100.0) <= 1e-6
    assert normalized[0].normalized_weight == 60
    assert normalized[1].normalized_weight == 40


def test_normalization_when_sum_less_than_100():
    items = [
        PortfolioItem(ticker='AAPL', market='US', weight=30),
        PortfolioItem(ticker='MSFT', market='US', weight=20),
    ]
    normalized = normalize_portfolio_weights(items)
    assert abs((normalized[0].normalized_weight or 0) - 60.0) <= 1e-6
    assert abs((normalized[1].normalized_weight or 0) - 40.0) <= 1e-6
    assert abs(sum(item.normalized_weight or 0 for item in normalized) - 100.0) <= 1e-6


def test_normalization_when_sum_greater_than_100():
    items = [
        PortfolioItem(ticker='PETR4', market='BR', weight=120),
        PortfolioItem(ticker='ITUB4', market='BR', weight=80),
    ]
    normalized = normalize_portfolio_weights(items)
    assert abs((normalized[0].normalized_weight or 0) - 60.0) <= 1e-6
    assert abs((normalized[1].normalized_weight or 0) - 40.0) <= 1e-6


def test_single_asset_extreme_case():
    items = [PortfolioItem(ticker='TSLA', market='US', weight=0.000001)]
    normalized = normalize_portfolio_weights(items)
    assert abs((normalized[0].normalized_weight or 0) - 100.0) <= 1e-6


def test_preserves_original_weight_and_other_fields():
    item = PortfolioItem(ticker='NVDA', market='US', weight=33, quantity=10, avg_price=100.0)
    normalized = normalize_portfolio_weights([item])[0]
    assert item.weight == 33
    assert normalized.weight == 33
    assert normalized.quantity == 10
    assert normalized.avg_price == 100.0


def test_raises_when_total_weight_non_positive():
    items = [PortfolioItem(ticker='AAPL', market='US', weight=0)]
    with pytest.raises(ValueError):
        normalize_portfolio_weights(items)
