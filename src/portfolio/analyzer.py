from __future__ import annotations

from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable

from src.agents.investors import consolidate_portfolio_by_persona
from src.portfolio.asset_pipeline import analyze_portfolio_asset
from src.portfolio.aggregator import aggregate_portfolio_signals
from src.portfolio.insights import generate_portfolio_insights
from src.portfolio.metrics import calculate_concentration_metrics
from src.portfolio.objective_fit import evaluate_objective_fit
from src.portfolio.models import (
    PortfolioAnalysisInput,
    PortfolioAnalysisMetadata,
    PortfolioAnalysisOutput,
    PortfolioAssetAnalysis,
    PortfolioFailedAsset,
)
from src.portfolio.normalizers import normalize_portfolio_weights
from src.portfolio.price_fetcher import enrich_portfolio_prices
from src.portfolio.scoring import calculate_diversification_score, calculate_overall_score
from src.portfolio.sector_resolver import resolve_asset_sectors
from src.portfolio.validators import validate_portfolio_input
from src.settings import PORTFOLIO_MAX_WORKERS

PersonaConsolidator = Callable[[PortfolioAnalysisOutput], str]
ProgressCallback = Callable[[dict], None]


class PortfolioAnalyzer:
    """Orquestrador principal da análise de portfólio (base do pipeline)."""

    def __init__(
        self,
        asset_analyzer: Callable[..., PortfolioAssetAnalysis] | None = None,
    ):
        self._asset_analyzer = asset_analyzer or analyze_portfolio_asset

    def analyze(
        self,
        data: PortfolioAnalysisInput,
        persona_consolidator: PersonaConsolidator | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> PortfolioAnalysisOutput:
        started_at = datetime.now()
        metadata_warnings: list[str] = []

        metadata_warnings.extend(validate_portfolio_input(data))

        enriched_items, price_warnings = enrich_portfolio_prices(data.items, reference_currency=data.reference_currency)
        metadata_warnings.extend(price_warnings)

        # Garantia defensiva: se algum item vier sem normalized_weight, normaliza por peso manual.
        if any(item.normalized_weight is None for item in enriched_items):
            enriched_items = normalize_portfolio_weights(enriched_items)

        asset_analyses, failed_assets = self._run_assets_parallel(
            enriched_items=enriched_items,
            full_analysis=(data.analysis_mode == 'full'),
            progress_callback=progress_callback,
        )
        if failed_assets:
            metadata_warnings.append(
                f'Análise concluída com falhas parciais: {len(failed_assets)} ativo(s) não processado(s).'
            )

        asset_analyses, sector_warnings = resolve_asset_sectors(asset_analyses)
        metadata_warnings.extend(sector_warnings)

        sentiment_breakdown, weighted_confidence, portfolio_sentiment = aggregate_portfolio_signals(asset_analyses)
        concentration_metrics = calculate_concentration_metrics(asset_analyses)
        objective_fit = evaluate_objective_fit(
            objective=data.objective,
            persona=data.persona,
            asset_analyses=asset_analyses,
            concentration_metrics=concentration_metrics,
        )
        metadata_warnings.extend([str(a) for a in objective_fit.get('alerts', [])[:2]])
        diversification_score, diversification_explanation = calculate_diversification_score(asset_analyses, concentration_metrics)
        metadata_warnings.append(f'Diversificação: {diversification_explanation}')
        overall_score, subscores = calculate_overall_score(
            asset_analyses=asset_analyses,
            concentration_metrics=concentration_metrics,
            diversification_score=diversification_score,
            objective_fit_score=float(objective_fit.get('score', 0.0)),
        )
        insights = generate_portfolio_insights(
            asset_analyses=asset_analyses,
            concentration_metrics=concentration_metrics,
            sentiment_breakdown=sentiment_breakdown,
            objective_fit=objective_fit,
            persona=data.persona,
        )

        finished_at = datetime.now()
        output = PortfolioAnalysisOutput(
            portfolio_sentiment=portfolio_sentiment,
            weighted_confidence=weighted_confidence,
            sentiment_breakdown={k: round(v, 2) for k, v in sentiment_breakdown.items()},
            concentration_metrics=concentration_metrics,
            diversification_score=diversification_score,
            overall_score=overall_score,
            subscores=subscores,
            objective_fit=objective_fit,
            strengths=insights['strengths'],
            weaknesses=insights['weaknesses'],
            risks=insights['risks'],
            rebalancing_suggestions=insights['rebalancing_suggestions'],
            asset_analyses=asset_analyses,
            failed_assets=failed_assets,
            analysis_metadata=PortfolioAnalysisMetadata(
                started_at=started_at,
                finished_at=finished_at,
                elapsed_seconds=(finished_at - started_at).total_seconds(),
                reference_currency=data.reference_currency,
                analysis_mode=data.analysis_mode,
                warnings=metadata_warnings,
                used_full_analysis=(data.analysis_mode == 'full'),
            ),
        )

        if persona_consolidator is not None:
            output.persona_analysis = persona_consolidator(output)
        elif data.persona:
            try:
                output.persona_analysis = consolidate_portfolio_by_persona(data.persona, output)
            except Exception as exc:
                metadata_warnings.append(f'Falha ao consolidar persona de portfólio: {exc}')
                output.analysis_metadata.warnings = metadata_warnings

        return output

    def _run_assets_parallel(
        self,
        enriched_items,
        full_analysis: bool,
        progress_callback: ProgressCallback | None = None,
    ):
        asset_analyses: list[PortfolioAssetAnalysis] = []
        failed_assets: list[PortfolioFailedAsset] = []

        total_assets = len(enriched_items)

        for idx, item in enumerate(enriched_items):
            if progress_callback:
                progress_callback(
                    {
                        'asset_id': idx,
                        'ticker': item.ticker.upper().strip(),
                        'market': item.market,
                        'status': 'queued',
                        'completed': 0,
                        'total': total_assets,
                    }
                )

        max_workers = max(1, min(PORTFOLIO_MAX_WORKERS, len(enriched_items)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {
                executor.submit(self._asset_analyzer, item, full_analysis=full_analysis): (idx, item)
                for idx, item in enumerate(enriched_items)
            }

            for idx, item in enumerate(enriched_items):
                if progress_callback:
                    progress_callback(
                        {
                            'asset_id': idx,
                            'ticker': item.ticker.upper().strip(),
                            'market': item.market,
                            'status': 'running',
                            'completed': 0,
                            'total': total_assets,
                        }
                    )

            completed_count = 0
            for future in as_completed(future_to_item):
                idx, item = future_to_item[future]
                try:
                    result = future.result()
                    asset_analyses.append(result)
                    completed_count += 1
                    if progress_callback:
                        progress_callback(
                            {
                                'asset_id': idx,
                                'ticker': item.ticker.upper().strip(),
                                'market': item.market,
                                'status': 'done',
                                'used_cached_analysis': bool(result.used_cached_analysis),
                                'completed': completed_count,
                                'total': total_assets,
                            }
                        )
                except Exception as exc:
                    failed_assets.append(
                        PortfolioFailedAsset(
                            ticker=item.ticker.upper().strip(),
                            market=item.market,
                            error_type=type(exc).__name__,
                            error_message=str(exc),
                        )
                    )
                    completed_count += 1
                    if progress_callback:
                        progress_callback(
                            {
                                'asset_id': idx,
                                'ticker': item.ticker.upper().strip(),
                                'market': item.market,
                                'status': 'failed',
                                'error_type': type(exc).__name__,
                                'error_message': str(exc),
                                'completed': completed_count,
                                'total': total_assets,
                            }
                        )
        return asset_analyses, failed_assets
