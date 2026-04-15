from __future__ import annotations

from src.portfolio.models import PortfolioAssetAnalysis, PortfolioConcentrationMetrics


def generate_portfolio_insights(
    asset_analyses: list[PortfolioAssetAnalysis],
    concentration_metrics: PortfolioConcentrationMetrics,
    sentiment_breakdown: dict[str, float],
    objective_fit: dict | None,
    persona: str | None = None,
) -> dict[str, list[str]]:
    strengths: list[str] = []
    weaknesses: list[str] = []
    risks: list[str] = []
    rebalancing: list[str] = []

    bullish_weight = float(sentiment_breakdown.get('BULLISH', 0.0))
    bearish_weight = float(sentiment_breakdown.get('BEARISH', 0.0))

    if bullish_weight >= 50:
        strengths.append(f'Base da carteira com viés positivo: {bullish_weight:.1f}% em ativos bullish.')
    if concentration_metrics.max_asset_weight <= 30:
        strengths.append('Concentração por ativo em nível controlado.')
    if len(concentration_metrics.sector_weights) >= 3:
        strengths.append('Diversificação setorial adequada para reduzir risco idiossincrático.')

    if concentration_metrics.max_asset_weight > 35:
        heavy = max(asset_analyses, key=lambda a: a.normalized_weight, default=None)
        if heavy:
            weaknesses.append(
                f'Concentração elevada em {heavy.ticker} ({heavy.normalized_weight:.1f}%), reduzindo equilíbrio da carteira.'
            )
            rebalancing.append(_persona_prefix(persona) + f' considerar reduzir gradualmente {heavy.ticker} para próximo de 25%-30% do portfólio.')

    if bearish_weight >= 25:
        weaknesses.append(f'Peso relevante em teses bearish ({bearish_weight:.1f}%), pressionando a relação risco/retorno.')
        risky = [a.ticker for a in asset_analyses if a.sentiment == 'BEARISH' and a.normalized_weight >= 10]
        if risky:
            rebalancing.append(_persona_prefix(persona) + f' revisar exposição em ativos bearish com maior peso: {", ".join(risky)}.')

    us_weight = concentration_metrics.market_weights.get('US', 0.0)
    br_weight = concentration_metrics.market_weights.get('BR', 0.0)
    if us_weight >= 80 or br_weight >= 80:
        market = 'US' if us_weight >= 80 else 'BR'
        weight = us_weight if us_weight >= 80 else br_weight
        risks.append(f'Concentração geográfica no mercado {market} ({weight:.1f}%) aumenta sensibilidade macro.')
        rebalancing.append(_persona_prefix(persona) + ' avaliar incremento de exposição no mercado complementar para reduzir risco de concentração.')

    if any('Setor não disponível' in a for a in concentration_metrics.alerts):
        risks.append('Parte da carteira sem classificação setorial dificulta controle fino de diversificação.')

    if objective_fit:
        score = float(objective_fit.get('score', 0.0))
        alignment = str(objective_fit.get('alignment', 'indisponivel'))
        if score >= 7:
            strengths.append(f'A carteira está alinhada ao objetivo declarado (score {score:.1f}, alinhamento {alignment}).')
        else:
            weaknesses.append(f'Alinhamento ao objetivo abaixo do ideal (score {score:.1f}, alinhamento {alignment}).')
            for alert in objective_fit.get('alerts', [])[:2]:
                risks.append(str(alert))
            rebalancing.append(_persona_prefix(persona) + ' ajustar a composição para aumentar aderência ao objetivo declarado.')

    # Garante mínimo de itens quando há dados.
    if asset_analyses:
        strengths = _ensure_minimum(strengths, 'Carteira com base analisada e passível de otimização incremental.')
        weaknesses = _ensure_minimum(weaknesses, 'Há espaço para melhorar balanceamento entre convicção e diversificação.')
        risks = _ensure_minimum(risks, 'Risco de cenário macro pode impactar ativos mais sensíveis.')
        rebalancing = _ensure_minimum(
            rebalancing,
            _persona_prefix(persona) + ' priorizar ajustes graduais, sem promessas de retorno futuro.',
        )

    return {
        'strengths': strengths[:5],
        'weaknesses': weaknesses[:5],
        'risks': risks[:5],
        'rebalancing_suggestions': rebalancing[:5],
    }


def _persona_prefix(persona: str | None) -> str:
    key = (persona or '').lower().strip()
    if key == 'buffett':
        return 'Com foco em margem de segurança,'
    if key == 'graham':
        return 'Sob ótica de valor intrínseco,'
    if key == 'barsi':
        return 'Priorizando renda e disciplina de dividendos,'
    if key == 'lynch':
        return 'Com visão GARP e crescimento sustentável,'
    return 'De forma prudente,'


def _ensure_minimum(items: list[str], fallback: str) -> list[str]:
    if len(items) >= 3:
        return items
    while len(items) < 3:
        items.append(fallback)
    return items
