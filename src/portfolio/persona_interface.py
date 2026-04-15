from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from src.portfolio.models import PortfolioAnalysisOutput


class PortfolioHoldingSnapshot(BaseModel):
    ticker: str
    market: Literal['BR', 'US']
    weight: float
    sentiment: Literal['BULLISH', 'NEUTRAL', 'BEARISH']
    confidence: int


class PortfolioPersonaInput(BaseModel):
    persona: str
    objective: str | None = None
    portfolio_sentiment: Literal['BULLISH', 'NEUTRAL', 'BEARISH'] = 'NEUTRAL'
    weighted_confidence: float = 0.0
    overall_score: float = 0.0
    diversification_score: float | None = None
    subscores: dict[str, float] = Field(default_factory=dict)
    market_weights: dict[str, float] = Field(default_factory=dict)
    max_asset_weight: float = 0.0
    hhi_normalized: float = 0.0
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    rebalancing_suggestions: list[str] = Field(default_factory=list)
    objective_fit: dict[str, Any] = Field(default_factory=dict)
    top_holdings: list[PortfolioHoldingSnapshot] = Field(default_factory=list)


class PortfolioPersonaOutput(BaseModel):
    content: str
    sentiment: Literal['BULLISH', 'NEUTRAL', 'BEARISH'] = 'NEUTRAL'
    confidence: int = 0
    recommendation: Literal['MANTER', 'OBSERVAR', 'REBALANCEAR'] = 'OBSERVAR'


def build_portfolio_persona_input(
    output: PortfolioAnalysisOutput,
    persona: str,
) -> PortfolioPersonaInput:
    sorted_assets = sorted(output.asset_analyses, key=lambda x: float(x.normalized_weight), reverse=True)
    top_holdings = [
        PortfolioHoldingSnapshot(
            ticker=a.ticker,
            market=a.market,
            weight=round(float(a.normalized_weight), 2),
            sentiment=a.sentiment,
            confidence=int(a.confidence),
        )
        for a in sorted_assets[:5]
    ]

    objective = None
    if output.objective_fit:
        objective = str(output.objective_fit.get('objective') or '') or None

    return PortfolioPersonaInput(
        persona=persona,
        objective=objective,
        portfolio_sentiment=output.portfolio_sentiment,
        weighted_confidence=round(float(output.weighted_confidence), 2),
        overall_score=round(float(output.overall_score or 0.0), 2),
        diversification_score=output.diversification_score,
        subscores=dict(output.subscores or {}),
        market_weights=dict(output.concentration_metrics.market_weights or {}),
        max_asset_weight=float(output.concentration_metrics.max_asset_weight or 0.0),
        hhi_normalized=float(output.concentration_metrics.hhi_normalized or 0.0),
        strengths=list(output.strengths or []),
        weaknesses=list(output.weaknesses or []),
        risks=list(output.risks or []),
        rebalancing_suggestions=list(output.rebalancing_suggestions or []),
        objective_fit=dict(output.objective_fit or {}),
        top_holdings=top_holdings,
    )
