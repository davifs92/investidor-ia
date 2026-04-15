from src.portfolio.models import PortfolioItem


def normalize_portfolio_weights(items: list[PortfolioItem]) -> list[PortfolioItem]:
    if not items:
        return []

    total = sum(item.weight for item in items)
    if total <= 0:
        raise ValueError('Não é possível normalizar pesos com soma menor ou igual a zero.')

    normalized: list[PortfolioItem] = []
    for item in items:
        updated = item.model_copy(deep=True)
        updated.normalized_weight = (item.weight / total) * 100.0
        normalized.append(updated)
    return normalized
