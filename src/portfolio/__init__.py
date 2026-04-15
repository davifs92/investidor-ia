from __future__ import annotations

from importlib import import_module

__all__ = [
    'PortfolioItem',
    'PortfolioAnalyzer',
    'analyze_portfolio_asset',
    'aggregate_portfolio_signals',
    'calculate_concentration_metrics',
    'evaluate_objective_fit',
    'generate_portfolio_insights',
    'calculate_diversification_score',
    'calculate_overall_score',
    'PortfolioAnalysisInput',
    'PortfolioAssetAnalysis',
    'PortfolioConcentrationMetrics',
    'PortfolioFailedAsset',
    'PortfolioAnalysisMetadata',
    'PortfolioAnalysisOutput',
    'PortfolioValidationError',
    'validate_portfolio_input',
    'normalize_portfolio_weights',
    'PortfolioHoldingSnapshot',
    'PortfolioPersonaInput',
    'PortfolioPersonaOutput',
    'build_portfolio_persona_input',
    'generate_portfolio_pdf_bytes',
    'list_portfolio_reports',
    'get_portfolio_report',
    'save_portfolio_report',
    'list_saved_portfolios',
    'get_saved_portfolio',
    'save_portfolio_composition',
    'duplicate_saved_portfolio',
    'delete_saved_portfolio',
    'mark_portfolio_analyzed',
    'enrich_portfolio_prices',
    'resolve_asset_sectors',
]


_EXPORTS = {
    # models
    'PortfolioItem': ('src.portfolio.models', 'PortfolioItem'),
    'PortfolioAnalysisInput': ('src.portfolio.models', 'PortfolioAnalysisInput'),
    'PortfolioAssetAnalysis': ('src.portfolio.models', 'PortfolioAssetAnalysis'),
    'PortfolioConcentrationMetrics': ('src.portfolio.models', 'PortfolioConcentrationMetrics'),
    'PortfolioFailedAsset': ('src.portfolio.models', 'PortfolioFailedAsset'),
    'PortfolioAnalysisMetadata': ('src.portfolio.models', 'PortfolioAnalysisMetadata'),
    'PortfolioAnalysisOutput': ('src.portfolio.models', 'PortfolioAnalysisOutput'),
    # analyzer/pipeline
    'PortfolioAnalyzer': ('src.portfolio.analyzer', 'PortfolioAnalyzer'),
    'analyze_portfolio_asset': ('src.portfolio.asset_pipeline', 'analyze_portfolio_asset'),
    # processing
    'aggregate_portfolio_signals': ('src.portfolio.aggregator', 'aggregate_portfolio_signals'),
    'calculate_concentration_metrics': ('src.portfolio.metrics', 'calculate_concentration_metrics'),
    'evaluate_objective_fit': ('src.portfolio.objective_fit', 'evaluate_objective_fit'),
    'generate_portfolio_insights': ('src.portfolio.insights', 'generate_portfolio_insights'),
    'calculate_diversification_score': ('src.portfolio.scoring', 'calculate_diversification_score'),
    'calculate_overall_score': ('src.portfolio.scoring', 'calculate_overall_score'),
    'normalize_portfolio_weights': ('src.portfolio.normalizers', 'normalize_portfolio_weights'),
    'enrich_portfolio_prices': ('src.portfolio.price_fetcher', 'enrich_portfolio_prices'),
    'resolve_asset_sectors': ('src.portfolio.sector_resolver', 'resolve_asset_sectors'),
    # validation
    'PortfolioValidationError': ('src.portfolio.validators', 'PortfolioValidationError'),
    'validate_portfolio_input': ('src.portfolio.validators', 'validate_portfolio_input'),
    # persona interface
    'PortfolioHoldingSnapshot': ('src.portfolio.persona_interface', 'PortfolioHoldingSnapshot'),
    'PortfolioPersonaInput': ('src.portfolio.persona_interface', 'PortfolioPersonaInput'),
    'PortfolioPersonaOutput': ('src.portfolio.persona_interface', 'PortfolioPersonaOutput'),
    'build_portfolio_persona_input': ('src.portfolio.persona_interface', 'build_portfolio_persona_input'),
    # persistence
    'list_portfolio_reports': ('src.portfolio.persistence', 'list_portfolio_reports'),
    'get_portfolio_report': ('src.portfolio.persistence', 'get_portfolio_report'),
    'save_portfolio_report': ('src.portfolio.persistence', 'save_portfolio_report'),
    'list_saved_portfolios': ('src.portfolio.persistence', 'list_saved_portfolios'),
    'get_saved_portfolio': ('src.portfolio.persistence', 'get_saved_portfolio'),
    'save_portfolio_composition': ('src.portfolio.persistence', 'save_portfolio_composition'),
    'duplicate_saved_portfolio': ('src.portfolio.persistence', 'duplicate_saved_portfolio'),
    'delete_saved_portfolio': ('src.portfolio.persistence', 'delete_saved_portfolio'),
    'mark_portfolio_analyzed': ('src.portfolio.persistence', 'mark_portfolio_analyzed'),
    # pdf
    'generate_portfolio_pdf_bytes': ('src.portfolio.pdf_export', 'generate_portfolio_pdf_bytes'),
}


def __getattr__(name: str):
    if name not in _EXPORTS:
        raise AttributeError(f'module {__name__!r} has no attribute {name!r}')
    module_name, attr_name = _EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attr_name)
    globals()[name] = value
    return value
