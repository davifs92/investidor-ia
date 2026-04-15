from __future__ import annotations

from src.portfolio.models import PortfolioAssetAnalysis


SENTIMENT_SCORE_MAP = {'BULLISH': 1.0, 'NEUTRAL': 0.5, 'BEARISH': 0.0}


def aggregate_portfolio_signals(asset_analyses: list[PortfolioAssetAnalysis]) -> tuple[dict[str, float], float, str]:
    if not asset_analyses:
        return {'BULLISH': 0.0, 'NEUTRAL': 0.0, 'BEARISH': 0.0}, 0.0, 'NEUTRAL'

    total_weight = sum(float(asset.normalized_weight) for asset in asset_analyses)
    if total_weight <= 0:
        return {'BULLISH': 0.0, 'NEUTRAL': 0.0, 'BEARISH': 0.0}, 0.0, 'NEUTRAL'

    breakdown = {'BULLISH': 0.0, 'NEUTRAL': 0.0, 'BEARISH': 0.0}
    for asset in asset_analyses:
        sentiment = asset.sentiment if asset.sentiment in breakdown else 'NEUTRAL'
        breakdown[sentiment] += float(asset.normalized_weight)

    breakdown = {k: (v / total_weight) * 100.0 for k, v in breakdown.items()}
    weighted_confidence = round(
        sum(float(asset.normalized_weight) * float(asset.confidence) for asset in asset_analyses) / total_weight,
        2,
    )

    weighted_score = (
        sum(float(asset.normalized_weight) * SENTIMENT_SCORE_MAP.get(asset.sentiment, 0.5) for asset in asset_analyses)
        / total_weight
    )
    if weighted_score >= 0.67:
        portfolio_sentiment = 'BULLISH'
    elif weighted_score <= 0.33:
        portfolio_sentiment = 'BEARISH'
    else:
        portfolio_sentiment = 'NEUTRAL'

    return breakdown, weighted_confidence, portfolio_sentiment
