import inspect
from typing import Literal

from src.cache import cache_it
from src.data_providers.base import BaseDataProvider
from . import statusinvest, fundamentus

class BRDataProvider(BaseDataProvider):
    """Provedor de dados para o mercado brasileiro (B3). Utiliza StatusInvest e Fundamentus sob o capô."""
    
    @cache_it
    def details(self, ticker: str) -> dict:
        return statusinvest.details(ticker)

    @cache_it
    def name(self, ticker: str) -> str:
        return self.details(ticker)['nome']

    @cache_it
    def income_statement(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> dict:
        return statusinvest.income_statement(ticker, year_start, year_end, period)

    @cache_it
    def balance_sheet(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> dict:
        return statusinvest.balance_sheet(ticker, year_start, year_end, period)

    @cache_it
    def cash_flow(
        self, 
        ticker: str, 
        year_start: int | None = None, 
        year_end: int | None = None
    ) -> dict:
        return statusinvest.cash_flow(ticker, year_start, year_end)

    @cache_it
    def multiples(self, ticker: str) -> dict:
        return statusinvest.multiples(ticker)

    @cache_it
    def dividends(self, ticker: str) -> list[dict]:
        return statusinvest.dividends(ticker)

    @cache_it
    def dividends_by_year(self, ticker: str) -> list[dict]:
        stock_dividends = self.dividends(ticker)
        yearly_dividends = {}
        for dividend in stock_dividends:
            if dividend['data_pagamento'] == '----':
                continue
            year = int(dividend['data_pagamento'][:4])
            if year not in yearly_dividends:
                yearly_dividends[year] = 0
            yearly_dividends[year] += dividend['valor']

        return [{'ano': year, 'valor': round(value, 8)} for year, value in sorted(yearly_dividends.items())]

    @cache_it
    def screener(self):
        return statusinvest.screener()

    @cache_it
    def payouts(self, ticker: str) -> list[dict]:
        return statusinvest.payouts(ticker)

    @cache_it
    def earnings_release_text(self, ticker: str) -> str:
        results_trimestrais = fundamentus.resultados_trimestrais(ticker)
        download_link = results_trimestrais[0]['download_link'] if results_trimestrais else None
        if not download_link:
            apres = fundamentus.apresentacoes(ticker)
            download_link = apres[0]['download_link'] if apres else None

        if not download_link:
            raise ValueError('Não foi possível encontrar o earnings release para o ticker informado.')

        import requests
        import io
        from pypdf import PdfReader
        content = requests.get(download_link).content
        reader = PdfReader(io.BytesIO(content))
        return ''.join([page.extract_text() for page in reader.pages])

