from __future__ import annotations

import math

from src.portfolio.aggregator import SENTIMENT_SCORE_MAP
from src.portfolio.models import PortfolioAssetAnalysis, PortfolioConcentrationMetrics
from src.portfolio.sector_resolver import UNKNOWN_SECTOR

# Story 9 - pesos da nota de diversificação
DIV_ASSET_CONCENTRATION_WEIGHT = 0.40
DIV_NUM_ASSETS_WEIGHT = 0.25
DIV_MARKET_CONCENTRATION_WEIGHT = 0.20
DIV_SECTOR_CONCENTRATION_WEIGHT = 0.15

# Story 10 - pesos da nota geral
OVERALL_QUALITY_WEIGHT = 0.30
OVERALL_DIVERSIFICATION_WEIGHT = 0.25
OVERALL_OBJECTIVE_FIT_WEIGHT = 0.20
OVERALL_CONCENTRATION_RISK_WEIGHT = 0.15
OVERALL_VALUATION_WEIGHT = 0.10


def calculate_diversification_score(
    asset_analyses: list[PortfolioAssetAnalysis],
    concentration_metrics: PortfolioConcentrationMetrics,
) -> tuple[float, str]:
    if not asset_analyses:
        return 0.0, 'Sem ativos analisados para calcular diversificação.'

    max_asset_weight = concentration_metrics.max_asset_weight
    market_max = max(concentration_metrics.market_weights.values()) if concentration_metrics.market_weights else 0.0

    known_sector_weights = {
        sector: weight
        for sector, weight in concentration_metrics.sector_weights.items()
        if sector != UNKNOWN_SECTOR
    }
    max_known_sector = max(known_sector_weights.values()) if known_sector_weights else 0.0

    # 1) Concentração por ativo (limiar 30%)
    if max_asset_weight <= 30:
        asset_component = 10.0
    else:
        asset_component = max(0.0, 10.0 - (max_asset_weight - 30.0) * 0.5)

    # 2) Número de ativos (escala log com saturação em 15)
    n_assets = len(asset_analyses)
    num_assets_component = 10.0 * min(math.log1p(n_assets) / math.log1p(15), 1.0)

    # 3) Concentração por mercado (limiar 80%)
    if market_max <= 80:
        market_component = 10.0
    else:
        market_component = max(0.0, 10.0 - (market_max - 80.0) * 0.5)

    # 4) Concentração por setor (limiar 50%), quando disponível
    if known_sector_weights:
        if max_known_sector <= 50:
            sector_component = 10.0
        else:
            sector_component = max(0.0, 10.0 - (max_known_sector - 50.0) * 0.5)
    else:
        sector_component = 5.0

    score = (
        DIV_ASSET_CONCENTRATION_WEIGHT * asset_component
        + DIV_NUM_ASSETS_WEIGHT * num_assets_component
        + DIV_MARKET_CONCENTRATION_WEIGHT * market_component
        + DIV_SECTOR_CONCENTRATION_WEIGHT * sector_component
    )
    score = round(max(0.0, min(10.0, score)), 1)

    penalties = {
        'concentração por ativo': 10.0 - asset_component,
        'número de ativos': 10.0 - num_assets_component,
        'concentração por mercado': 10.0 - market_component,
        'concentração por setor': 10.0 - sector_component,
    }
    major_factor = max(penalties, key=penalties.get)
    explanation = f'Principal fator penalizante: {major_factor}.'
    return score, explanation


def calculate_overall_score(
    asset_analyses: list[PortfolioAssetAnalysis],
    concentration_metrics: PortfolioConcentrationMetrics,
    diversification_score: float,
    objective_fit_score: float | None = None,
) -> tuple[float, dict[str, float]]:
    subscores = {
        'quality_assets': _quality_assets_score(asset_analyses),
        'diversification': float(diversification_score),
        'concentration_risk': round((1.0 - concentration_metrics.hhi_normalized) * 10.0, 2),
        'valuation': _valuation_score(asset_analyses),
    }

    if objective_fit_score is not None:
        subscores['objective_fit'] = float(objective_fit_score)

    weights = {
        'quality_assets': OVERALL_QUALITY_WEIGHT,
        'diversification': OVERALL_DIVERSIFICATION_WEIGHT,
        'objective_fit': OVERALL_OBJECTIVE_FIT_WEIGHT,
        'concentration_risk': OVERALL_CONCENTRATION_RISK_WEIGHT,
        'valuation': OVERALL_VALUATION_WEIGHT,
    }

    available_keys = [k for k in weights if k in subscores and subscores[k] is not None]
    total_weight = sum(weights[k] for k in available_keys)
    if total_weight <= 0:
        return 0.0, subscores

    normalized_weights = {k: weights[k] / total_weight for k in available_keys}
    overall = sum(subscores[k] * normalized_weights[k] for k in available_keys)
    overall = round(max(0.0, min(10.0, overall)), 1)
    return overall, {k: round(v, 2) for k, v in subscores.items()}


def _quality_assets_score(asset_analyses: list[PortfolioAssetAnalysis]) -> float:
    if not asset_analyses:
        return 0.0
    total_weight = sum(float(a.normalized_weight) for a in asset_analyses)
    if total_weight <= 0:
        return 0.0

    weighted = 0.0
    for a in asset_analyses:
        sentiment_score = SENTIMENT_SCORE_MAP.get(a.sentiment, 0.5)
        score_0_10 = (float(a.confidence) / 100.0) * sentiment_score * 10.0
        weighted += float(a.normalized_weight) * score_0_10
    return round(weighted / total_weight, 2)


def _valuation_score(asset_analyses: list[PortfolioAssetAnalysis]) -> float:
    assets_with_valuation = [a for a in asset_analyses if a.valuation_confidence is not None]
    if not assets_with_valuation:
        return 0.0

    total_weight = sum(float(a.normalized_weight) for a in assets_with_valuation)
    if total_weight <= 0:
        return 0.0

    weighted = sum(float(a.normalized_weight) * (float(a.valuation_confidence or 0) / 100.0) * 10.0 for a in assets_with_valuation)
    return round(weighted / total_weight, 2)
