from __future__ import annotations

import yfinance as yf

from src.data import stocks
from src.portfolio.models import PortfolioAssetAnalysis

UNKNOWN_SECTOR = 'Setor não disponível'


def resolve_asset_sectors(asset_analyses: list[PortfolioAssetAnalysis]) -> tuple[list[PortfolioAssetAnalysis], list[str]]:
    warnings: list[str] = []
    updated_assets: list[PortfolioAssetAnalysis] = []

    for asset in asset_analyses:
        updated = asset.model_copy(deep=True)
        if updated.sector and updated.sector.strip():
            updated_assets.append(updated)
            continue

        resolved_sector = _resolve_sector_by_market(updated.ticker, updated.market)
        if not resolved_sector:
            resolved_sector = UNKNOWN_SECTOR
            warnings.append(f'Setor não disponível para {updated.ticker}.')
        updated.sector = resolved_sector
        updated_assets.append(updated)

    return updated_assets, warnings


def _resolve_sector_by_market(ticker: str, market: str) -> str | None:
    try:
        details = stocks.details(ticker, market=market)
    except Exception:
        details = {}

    provider_sector = str(details.get('segmento_de_atuacao', '')).strip() if isinstance(details, dict) else ''
    if provider_sector and provider_sector.upper() != 'N/A':
        return provider_sector

    if market == 'US':
        try:
            info = yf.Ticker(ticker).info
            sector = str((info or {}).get('sector', '')).strip()
            if sector and sector.upper() != 'N/A':
                return sector
        except Exception:
            return None
    return None
