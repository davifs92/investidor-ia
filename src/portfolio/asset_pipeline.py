from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from src.agents.analysts import earnings_release, financial, macro, news, technical, valuation
from src.agents.base import BaseAgentOutput
from src.cache import cache
from src.portfolio.models import PortfolioAssetAnalysis, PortfolioItem
from src.settings import DB_DIR, PORTFOLIO_ANALYSIS_TTL, PORTFOLIO_FULL_ANALYSIS


def _canonical_ticker(ticker: str) -> str:
    up = ticker.upper().strip()
    return up[:-3] if up.endswith('.SA') else up


def _truncate(text: str, max_chars: int = 280) -> str:
    clean = ' '.join((text or '').split())
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + '...'


def _weighted_sentiment_and_confidence(outputs: list[BaseAgentOutput]) -> tuple[str, int]:
    valid = [o for o in outputs if isinstance(o, BaseAgentOutput)]
    if not valid:
        return 'NEUTRAL', 0

    score_map = {'BULLISH': 1.0, 'NEUTRAL': 0.5, 'BEARISH': 0.0}
    avg_score = sum(score_map.get(o.sentiment, 0.5) for o in valid) / len(valid)
    avg_conf = int(round(sum(o.confidence for o in valid) / len(valid)))

    if avg_score >= 0.67:
        sentiment = 'BULLISH'
    elif avg_score <= 0.33:
        sentiment = 'BEARISH'
    else:
        sentiment = 'NEUTRAL'
    return sentiment, avg_conf


def _analysis_from_report_item(item: PortfolioItem, report_data: dict) -> PortfolioAssetAnalysis | None:
    analysts = report_data.get('data', {}).get('analysts', {})
    financial_data = analysts.get('financial', {}) if isinstance(analysts, dict) else {}
    valuation_data = analysts.get('valuation', {}) if isinstance(analysts, dict) else {}
    technical_data = analysts.get('technical', {}) if isinstance(analysts, dict) else {}

    if not (financial_data or valuation_data or technical_data):
        return None

    outputs: list[BaseAgentOutput] = []
    for data in (financial_data, valuation_data, technical_data):
        if isinstance(data, dict):
            outputs.append(
                BaseAgentOutput(
                    content=str(data.get('content', '')),
                    sentiment=str(data.get('sentiment', 'NEUTRAL')).upper(),
                    confidence=int(data.get('confidence', 0)),
                )
            )

    sentiment, confidence = _weighted_sentiment_and_confidence(outputs)

    return PortfolioAssetAnalysis(
        ticker=item.ticker.upper().strip(),
        market=item.market,
        weight=item.weight,
        normalized_weight=float(item.normalized_weight or 0.0),
        sentiment=sentiment,
        confidence=confidence,
        financial_summary=_truncate(str(financial_data.get('content', ''))),
        valuation_summary=_truncate(str(valuation_data.get('content', ''))),
        technical_summary=_truncate(str(technical_data.get('content', ''))),
        valuation_confidence=int(valuation_data.get('confidence', 0)) if isinstance(valuation_data, dict) else None,
        sector=item.sector,
        used_cached_analysis=True,
    )


def _find_recent_report(item: PortfolioItem, ttl_hours: int) -> dict | None:
    reports_file = Path(DB_DIR) / 'reports.json'
    if not reports_file.exists():
        return None

    try:
        with open(reports_file, 'r') as f:
            raw = json.load(f) if f.readable() else []
    except Exception:
        return None

    if not isinstance(raw, list):
        return None

    now = datetime.now()
    canonical_item = _canonical_ticker(item.ticker)
    ttl_limit = now - timedelta(hours=ttl_hours)

    # procura do mais recente para o mais antigo
    for report in reversed(raw):
        try:
            report_ticker = _canonical_ticker(str(report.get('ticker', '')))
            generated_at = datetime.fromisoformat(str(report.get('generated_at')))
            if report_ticker == canonical_item and generated_at >= ttl_limit:
                return report
        except Exception:
            continue
    return None


def analyze_portfolio_asset(
    item: PortfolioItem,
    ttl_seconds: int = PORTFOLIO_ANALYSIS_TTL,
    full_analysis: bool = PORTFOLIO_FULL_ANALYSIS,
) -> PortfolioAssetAnalysis:
    cache_key = f'portfolio_asset_pipeline:{_canonical_ticker(item.ticker)}:{item.market}:{full_analysis}'
    cached = cache.get(cache_key, default=None)
    if isinstance(cached, PortfolioAssetAnalysis):
        return cached

    ttl_hours = max(1, int(ttl_seconds / 3600))
    recent = _find_recent_report(item, ttl_hours=ttl_hours)
    if recent:
        parsed = _analysis_from_report_item(item, recent)
        if parsed:
            cache.set(cache_key, parsed, expire=ttl_seconds)
            return parsed

    market = item.market
    ticker = item.ticker.upper().strip()
    financial_out = financial.analyze(ticker, market=market)
    valuation_out = valuation.analyze(ticker, market=market)
    technical_out = technical.analyze(ticker, market=market)

    extra_outputs: list[BaseAgentOutput] = []
    if full_analysis:
        extra_outputs = [
            news.analyze(ticker, market=market),
            macro.analyze(ticker, market=market),
            earnings_release.analyze(ticker, market=market),
        ]

    outputs = [financial_out, valuation_out, technical_out, *extra_outputs]
    sentiment, confidence = _weighted_sentiment_and_confidence(outputs)

    result = PortfolioAssetAnalysis(
        ticker=ticker,
        market=item.market,
        weight=item.weight,
        normalized_weight=float(item.normalized_weight or 0.0),
        sentiment=sentiment,  # type: ignore[arg-type]
        confidence=confidence,
        financial_summary=_truncate(financial_out.content),
        valuation_summary=_truncate(valuation_out.content),
        technical_summary=_truncate(technical_out.content),
        valuation_confidence=valuation_out.confidence,
        sector=item.sector,
        used_cached_analysis=False,
    )
    cache.set(cache_key, result, expire=ttl_seconds)
    return result
