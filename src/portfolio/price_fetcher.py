from __future__ import annotations

from typing import Literal

import yfinance as yf

from src.portfolio.models import PortfolioItem, SupportedCurrency
from src.portfolio.normalizers import normalize_portfolio_weights
from src.settings import PORTFOLIO_REFERENCE_CURRENCY


def _ticker_for_market(ticker: str, market: Literal['BR', 'US']) -> str:
    ticker_up = ticker.upper().strip()
    if market == 'BR' and not ticker_up.endswith('.SA'):
        return f'{ticker_up}.SA'
    return ticker_up


def _fetch_last_close(ticker: str) -> float:
    hist = yf.Ticker(ticker).history(period='1d')
    if hist is None or hist.empty:
        raise ValueError(f'Histórico vazio para {ticker}.')
    return float(hist['Close'].iloc[-1])


def _fetch_usdbrl_rate() -> float:
    rate = _fetch_last_close('BRL=X')
    if rate <= 0:
        raise ValueError('Cotação USD/BRL inválida.')
    return rate


def _convert_to_reference(value: float, item_currency: SupportedCurrency, reference_currency: SupportedCurrency, usdbrl: float) -> float:
    if item_currency == reference_currency:
        return value
    if item_currency == 'USD' and reference_currency == 'BRL':
        return value * usdbrl
    if item_currency == 'BRL' and reference_currency == 'USD':
        return value / usdbrl
    return value


def enrich_portfolio_prices(
    items: list[PortfolioItem],
    reference_currency: SupportedCurrency | None = None,
) -> tuple[list[PortfolioItem], list[str]]:
    if not items:
        return [], []

    ref_currency = (reference_currency or PORTFOLIO_REFERENCE_CURRENCY)  # type: ignore[assignment]
    warnings: list[str] = []
    enriched: list[PortfolioItem] = []

    # Primeiro passo: buscar preços e valores de mercado por posição (quando quantity existir)
    for item in items:
        updated = item.model_copy(deep=True)
        updated.currency = 'BRL' if item.market == 'BR' else 'USD'
        ticker_fetch = _ticker_for_market(item.ticker, item.market)

        try:
            updated.current_price = _fetch_last_close(ticker_fetch)
        except Exception as exc:
            updated.current_price = None
            warnings.append(f"Falha ao obter preço de {item.ticker}: {exc}. Usando peso manual como fallback.")

        if updated.quantity is not None and updated.current_price is not None:
            updated.market_value = float(updated.quantity) * float(updated.current_price)
        else:
            updated.market_value = None

        enriched.append(updated)

    # Determina se é possível usar pesos reais (todos com quantity e market_value)
    can_use_market_values = all((it.quantity is not None and (it.market_value or 0) > 0) for it in enriched)

    usdbrl = 1.0
    has_mixed_currency = any(it.currency == 'USD' for it in enriched) and any(it.currency == 'BRL' for it in enriched)
    needs_fx = has_mixed_currency or ref_currency != 'BRL'
    if needs_fx:
        try:
            usdbrl = _fetch_usdbrl_rate()
        except Exception as exc:
            warnings.append(f'Falha ao obter cotação USD/BRL: {exc}. Usando peso manual normalizado.')
            can_use_market_values = False

    if can_use_market_values:
        converted_values: list[float] = []
        for it in enriched:
            converted = _convert_to_reference(float(it.market_value or 0.0), it.currency or 'BRL', ref_currency, usdbrl)
            it.market_value = converted
            converted_values.append(converted)

        total_value = sum(converted_values)
        if total_value <= 0:
            warnings.append('Valor de mercado total inválido. Usando peso manual normalizado.')
            can_use_market_values = False
        else:
            for it in enriched:
                it.normalized_weight = (float(it.market_value or 0.0) / total_value) * 100.0

    if not can_use_market_values:
        fallback = normalize_portfolio_weights(enriched)
        for original, normalized in zip(enriched, fallback):
            original.normalized_weight = normalized.normalized_weight
            # mantém market_value calculado quando disponível, mas peso final segue manual

    return enriched, warnings
