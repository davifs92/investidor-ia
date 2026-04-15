from typing import Literal
from src.market_router import MarketRouter

def details(ticker: str, market: str | None = None) -> dict:
    return MarketRouter.get_provider(ticker, market).details(ticker)

def name(ticker: str, market: str | None = None) -> str:
    return MarketRouter.get_provider(ticker, market).name(ticker)

def income_statement(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
    market: str | None = None,
) -> dict:
    return MarketRouter.get_provider(ticker, market).income_statement(ticker, year_start, year_end, period)

def balance_sheet(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
    market: str | None = None,
) -> dict:
    return MarketRouter.get_provider(ticker, market).balance_sheet(ticker, year_start, year_end, period)

def cash_flow(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    market: str | None = None,
) -> dict:
    return MarketRouter.get_provider(ticker, market).cash_flow(ticker, year_start, year_end)

def multiples(ticker: str, market: str | None = None) -> dict:
    return MarketRouter.get_provider(ticker, market).multiples(ticker)

def dividends(ticker: str, market: str | None = None) -> list[dict]:
    return MarketRouter.get_provider(ticker, market).dividends(ticker)

def dividends_by_year(ticker: str, market: str | None = None) -> list[dict]:
    return MarketRouter.get_provider(ticker, market).dividends_by_year(ticker)

def screener(market: str | None = None):
    # Fallback para BR se nenhum mercado for especificado no screener
    actual_market = market if market else 'BR'
    return MarketRouter.get_provider('', actual_market).screener()

def payouts(ticker: str, market: str | None = None) -> list[dict]:
    return MarketRouter.get_provider(ticker, market).payouts(ticker)

def earnings_release_pdf_path(ticker: str, market: str | None = None) -> str:
    return MarketRouter.get_provider(ticker, market).earnings_release_pdf_path(ticker)

def earnings_release_summary(ticker: str, market: str | None = None) -> str:
    provider = MarketRouter.get_provider(ticker, market)
    fn = getattr(provider, 'earnings_release', None)
    if callable(fn):
        return fn(ticker)
    raise NotImplementedError('Resumo de earnings release não disponível para este mercado/provider.')

def news(ticker: str, market: str | None = None) -> list[dict]:
    return MarketRouter.get_provider(ticker, market).news(ticker)


