from typing import Literal
from src.market_router import MarketRouter

def details(ticker: str) -> dict:
    return MarketRouter.get_provider(ticker).details(ticker)

def name(ticker: str) -> str:
    return MarketRouter.get_provider(ticker).name(ticker)

def income_statement(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return MarketRouter.get_provider(ticker).income_statement(ticker, year_start, year_end, period)

def balance_sheet(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
    period: Literal['annual', 'quarter'] = 'annual',
) -> dict:
    return MarketRouter.get_provider(ticker).balance_sheet(ticker, year_start, year_end, period)

def cash_flow(
    ticker: str,
    year_start: int | None = None,
    year_end: int | None = None,
) -> dict:
    return MarketRouter.get_provider(ticker).cash_flow(ticker, year_start, year_end)

def multiples(ticker: str) -> dict:
    return MarketRouter.get_provider(ticker).multiples(ticker)

def dividends(ticker: str) -> list[dict]:
    return MarketRouter.get_provider(ticker).dividends(ticker)

def dividends_by_year(ticker: str) -> list[dict]:
    return MarketRouter.get_provider(ticker).dividends_by_year(ticker)

def screener():
    # Placeholder for broader tools, routing arbitrary. Typically screeners are market-specific.
    # We will route to BR as fallback for now or US if specified otherwise.
    return MarketRouter.get_provider('.SA').screener()

def payouts(ticker: str) -> list[dict]:
    return MarketRouter.get_provider(ticker).payouts(ticker)

def earnings_release_pdf_path(ticker: str) -> str:
    return MarketRouter.get_provider(ticker).earnings_release_pdf_path(ticker)



