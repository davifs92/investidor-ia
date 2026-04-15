from __future__ import annotations

from src.portfolio.models import PortfolioAssetAnalysis, PortfolioConcentrationMetrics
from src.portfolio.sector_resolver import UNKNOWN_SECTOR


def calculate_concentration_metrics(
    asset_analyses: list[PortfolioAssetAnalysis],
    asset_weight_limit: float = 25.0,
    market_weight_limit: float = 80.0,
) -> PortfolioConcentrationMetrics:
    if not asset_analyses:
        return PortfolioConcentrationMetrics()

    total_weight = sum(float(a.normalized_weight) for a in asset_analyses)
    if total_weight <= 0:
        return PortfolioConcentrationMetrics()

    market_weights: dict[str, float] = {}
    sector_weights: dict[str, float] = {}
    alerts: list[str] = []
    max_asset_weight = 0.0

    for asset in asset_analyses:
        weight = (float(asset.normalized_weight) / total_weight) * 100.0
        max_asset_weight = max(max_asset_weight, weight)

        market_weights[asset.market] = market_weights.get(asset.market, 0.0) + weight
        sector = asset.sector if asset.sector else UNKNOWN_SECTOR
        sector_weights[sector] = sector_weights.get(sector, 0.0) + weight

        if weight > asset_weight_limit:
            alerts.append(f'Ativo {asset.ticker} acima do limite de concentração ({weight:.2f}% > {asset_weight_limit:.2f}%).')

    for market, weight in market_weights.items():
        if weight > market_weight_limit:
            alerts.append(f'Concentração elevada no mercado {market} ({weight:.2f}% > {market_weight_limit:.2f}%).')

    if UNKNOWN_SECTOR in sector_weights:
        alerts.append('Setor não disponível para um ou mais ativos.')

    hhi = sum((float(asset.normalized_weight) / total_weight) ** 2 for asset in asset_analyses)
    n = len(asset_analyses)
    if n <= 1:
        hhi_normalized = 1.0
    else:
        hhi_normalized = (hhi - (1.0 / n)) / (1.0 - (1.0 / n))
        hhi_normalized = max(0.0, min(1.0, hhi_normalized))

    return PortfolioConcentrationMetrics(
        max_asset_weight=round(max_asset_weight, 2),
        market_weights={k: round(v, 2) for k, v in market_weights.items()},
        sector_weights={k: round(v, 2) for k, v in sector_weights.items()},
        hhi_normalized=round(hhi_normalized, 4),
        alerts=alerts,
    )
