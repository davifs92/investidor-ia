from __future__ import annotations

from typing import Any

from src.settings import INVESTORS_BR, INVESTORS_US
from src.portfolio.models import PortfolioAnalysisInput, PortfolioItem


MIXED_PORTFOLIO_PERSONAS = {'buffett': 'Warren Buffett', 'graham': 'Benjamin Graham'}
OBJECTIVE_OPTIONS = {
    'dividendos': 'Dividendos',
    'crescimento': 'Crescimento',
    'equilibrio': 'Equilibrio',
    'longo_prazo_conservador': 'Longo Prazo Conservador',
}


def get_persona_options(markets: set[str]) -> dict[str, str]:
    normalized = {m.upper().strip() for m in markets if m}
    if normalized == {'BR'}:
        return dict(INVESTORS_BR)
    if normalized == {'US'}:
        return dict(INVESTORS_US)
    if normalized == {'BR', 'US'}:
        return dict(MIXED_PORTFOLIO_PERSONAS)
    # fallback defensivo quando nenhum mercado válido foi selecionado ainda
    return dict(MIXED_PORTFOLIO_PERSONAS)


def sanitize_row(row: dict[str, Any]) -> dict[str, Any]:
    ticker = str(row.get('ticker', '') or '').upper().strip()
    market = str(row.get('market', 'BR') or 'BR').upper().strip()
    if market not in {'BR', 'US'}:
        market = 'BR'

    def _num(value: Any) -> float | None:
        if value in (None, '', 'None'):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    weight = _num(row.get('weight'))
    quantity = _num(row.get('quantity'))
    avg_price = _num(row.get('avg_price'))

    return {
        'ticker': ticker,
        'market': market,
        'weight': weight if weight is not None else 0.0,
        'quantity': quantity,
        'avg_price': avg_price,
    }


def build_portfolio_input(
    rows: list[dict[str, Any]],
    objective: str,
    persona: str,
    reference_currency: str = 'BRL',
) -> PortfolioAnalysisInput:
    items: list[PortfolioItem] = []
    errors: list[str] = []

    for idx, raw in enumerate(rows, start=1):
        row = sanitize_row(raw)
        ticker = row['ticker']
        market = row['market']
        weight = row['weight']

        if not ticker:
            errors.append(f'Linha {idx}: ticker é obrigatório.')
            continue
        if weight <= 0:
            errors.append(f'Linha {idx}: peso deve ser maior que zero.')
            continue

        items.append(
            PortfolioItem(
                ticker=ticker,
                market=market,
                weight=weight,
                quantity=row['quantity'],
                avg_price=row['avg_price'],
            )
        )

    if not items:
        errors.append('Adicione ao menos um ativo válido antes de analisar.')
    if errors:
        raise ValueError('\n'.join(errors))

    return PortfolioAnalysisInput(
        items=items,
        objective=objective,
        persona=persona,
        reference_currency=reference_currency,
        analysis_mode='portfolio',
    )


def composition_rows_for_table(asset_analyses) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for asset in sorted(asset_analyses, key=lambda x: float(x.normalized_weight), reverse=True):
        rows.append(
            {
                'Ticker': asset.ticker,
                'Mercado': asset.market,
                'Peso Informado (%)': round(float(asset.weight), 2),
                'Peso Normalizado (%)': round(float(asset.normalized_weight), 2),
                'Sentimento': asset.sentiment,
                'Confianca (%)': int(asset.confidence),
                'Setor': asset.sector or '-',
                'Cache': 'Sim' if asset.used_cached_analysis else 'Nao',
            }
        )
    return rows


def sector_market_heatmap_data(market_weights: dict[str, float], sector_weights: dict[str, float]) -> tuple[list[str], list[str], list[list[float]]]:
    x = ['Mercado', 'Setor']
    markets_total = round(sum(float(v) for v in market_weights.values()), 2)
    sectors_total = round(sum(float(v) for v in sector_weights.values()), 2)
    y = ['Concentracao (%)']
    z = [[markets_total, sectors_total]]
    return x, y, z
