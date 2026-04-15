from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


SupportedMarket = Literal['BR', 'US']
SupportedCurrency = Literal['BRL', 'USD']
PortfolioObjective = Literal['dividendos', 'crescimento', 'equilibrio', 'longo_prazo_conservador']
PortfolioMode = Literal['portfolio', 'full']


class PortfolioItem(BaseModel):
    ticker: str
    market: SupportedMarket
    weight: float
    quantity: float | None = None
    avg_price: float | None = None
    current_price: float | None = None
    market_value: float | None = None
    normalized_weight: float | None = None
    sector: str | None = None
    currency: SupportedCurrency | None = None


class PortfolioAnalysisInput(BaseModel):
    items: list[PortfolioItem] = Field(default_factory=list)
    objective: PortfolioObjective = 'equilibrio'
    persona: str | None = None
    reference_currency: SupportedCurrency = 'BRL'
    analysis_mode: PortfolioMode = 'portfolio'


class PortfolioAssetAnalysis(BaseModel):
    ticker: str
    market: SupportedMarket
    weight: float
    normalized_weight: float
    sentiment: Literal['BULLISH', 'NEUTRAL', 'BEARISH'] = 'NEUTRAL'
    confidence: int = 0
    financial_summary: str = ''
    valuation_summary: str = ''
    technical_summary: str = ''
    valuation_confidence: int | None = None
    sector: str | None = None
    used_cached_analysis: bool = False


class PortfolioConcentrationMetrics(BaseModel):
    max_asset_weight: float = 0.0
    market_weights: dict[str, float] = Field(default_factory=dict)
    sector_weights: dict[str, float] = Field(default_factory=dict)
    hhi_normalized: float = 0.0
    alerts: list[str] = Field(default_factory=list)


class PortfolioFailedAsset(BaseModel):
    ticker: str
    market: SupportedMarket
    error_type: str
    error_message: str


class PortfolioAnalysisMetadata(BaseModel):
    started_at: datetime | None = None
    finished_at: datetime | None = None
    elapsed_seconds: float | None = None
    reference_currency: SupportedCurrency = 'BRL'
    analysis_mode: PortfolioMode = 'portfolio'
    warnings: list[str] = Field(default_factory=list)
    used_full_analysis: bool = False


class PortfolioAnalysisOutput(BaseModel):
    portfolio_sentiment: Literal['BULLISH', 'NEUTRAL', 'BEARISH'] = 'NEUTRAL'
    weighted_confidence: float = 0.0
    sentiment_breakdown: dict[str, float] = Field(default_factory=dict)
    concentration_metrics: PortfolioConcentrationMetrics = Field(default_factory=PortfolioConcentrationMetrics)
    diversification_score: float | None = None
    overall_score: float | None = None
    subscores: dict[str, float] = Field(default_factory=dict)
    objective_fit: dict[str, Any] | None = None
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    rebalancing_suggestions: list[str] = Field(default_factory=list)
    persona_analysis: str | None = None
    asset_analyses: list[PortfolioAssetAnalysis] = Field(default_factory=list)
    failed_assets: list[PortfolioFailedAsset] = Field(default_factory=list)
    analysis_metadata: PortfolioAnalysisMetadata = Field(default_factory=PortfolioAnalysisMetadata)
