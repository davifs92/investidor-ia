from __future__ import annotations

from src.portfolio.models import PortfolioAssetAnalysis, PortfolioConcentrationMetrics


def evaluate_objective_fit(
    objective: str,
    persona: str | None,
    asset_analyses: list[PortfolioAssetAnalysis],
    concentration_metrics: PortfolioConcentrationMetrics,
) -> dict:
    if not asset_analyses:
        return {
            'objective': objective,
            'score': 0.0,
            'alignment': 'indisponivel',
            'alerts': ['Sem ativos analisados para avaliar adequação ao objetivo.'],
            'details': {},
        }

    total_weight = sum(float(a.normalized_weight) for a in asset_analyses)
    if total_weight <= 0:
        return {
            'objective': objective,
            'score': 0.0,
            'alignment': 'indisponivel',
            'alerts': ['Pesos inválidos para avaliar adequação ao objetivo.'],
            'details': {},
        }

    dividend_weight = 0.0
    growth_weight = 0.0
    quality_weight = 0.0
    bearish_weight = 0.0
    alerts: list[str] = []

    for asset in asset_analyses:
        w = float(asset.normalized_weight)
        text = f'{asset.financial_summary} {asset.valuation_summary} {asset.technical_summary}'.lower()

        is_dividend = any(k in text for k in ['dividend', 'dy', 'yield', 'renda'])
        is_growth = any(k in text for k in ['growth', 'crescimento', 'garp', 'expans'])

        if is_dividend:
            dividend_weight += w
        if is_growth:
            growth_weight += w
        if asset.sentiment != 'BEARISH' and asset.confidence >= 65:
            quality_weight += w
        if asset.sentiment == 'BEARISH':
            bearish_weight += w

    score = 5.0
    if objective == 'dividendos':
        score += (dividend_weight - 35.0) / 10.0
        if growth_weight > 40:
            score -= 1.5
            alerts.append('Peso em ativos de crescimento acima de 40% para objetivo de dividendos.')
    elif objective == 'crescimento':
        score += (growth_weight - 35.0) / 10.0
        if dividend_weight > 50:
            score -= 1.5
            alerts.append('Peso em ativos de renda acima de 50% para objetivo de crescimento.')
    elif objective == 'equilibrio':
        concentration_penalty = max(0.0, concentration_metrics.max_asset_weight - 35.0) / 10.0
        mix_bonus = 1.0 if dividend_weight >= 20 and growth_weight >= 20 else 0.0
        score += mix_bonus - concentration_penalty
        if mix_bonus == 0.0:
            alerts.append('Carteira pouco balanceada entre teses de renda e crescimento.')
    elif objective == 'longo_prazo_conservador':
        score += (quality_weight - 60.0) / 12.0
        if bearish_weight > 20:
            score -= 1.5
            alerts.append('Exposição bearish acima de 20% para objetivo conservador.')
        if concentration_metrics.max_asset_weight > 30:
            score -= 1.0
            alerts.append('Concentração por ativo acima de 30% para objetivo conservador.')

    # Consistência objetivo x persona
    persona_key = (persona or '').strip().lower()
    if objective == 'dividendos' and persona_key == 'lynch':
        alerts.append('Inconsistência: objetivo dividendos com persona Lynch.')
        score -= 1.0
    if objective == 'crescimento' and persona_key == 'barsi':
        alerts.append('Inconsistência: objetivo crescimento com persona Barsi.')
        score -= 1.0

    score = round(max(0.0, min(10.0, score)), 1)
    if score >= 7.0:
        alignment = 'alto'
    elif score >= 4.5:
        alignment = 'moderado'
    else:
        alignment = 'baixo'

    return {
        'objective': objective,
        'score': score,
        'alignment': alignment,
        'alerts': alerts,
        'details': {
            'dividend_weight': round(dividend_weight, 2),
            'growth_weight': round(growth_weight, 2),
            'quality_weight': round(quality_weight, 2),
            'bearish_weight': round(bearish_weight, 2),
        },
    }
