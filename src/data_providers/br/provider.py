from typing import Literal

from src.cache import cache_it
from src.data_providers.base import BaseDataProvider
from . import statusinvest, fundamentus

class BRDataProvider(BaseDataProvider):
    """Provedor de dados para o mercado brasileiro (B3). Utiliza StatusInvest e Fundamentus sob o capô."""
    
    def _clean_ticker(self, ticker: str) -> str:
        """Remove sufixos de mercado para compatibilidade com APIs brasileiras."""
        return ticker.upper().replace('.SA', '').strip()

    @cache_it
    def details(self, ticker: str) -> dict:
        return statusinvest.details(self._clean_ticker(ticker))

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
        return statusinvest.income_statement(self._clean_ticker(ticker), year_start, year_end, period)

    @cache_it
    def balance_sheet(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> dict:
        return statusinvest.balance_sheet(self._clean_ticker(ticker), year_start, year_end, period)

    @cache_it
    def cash_flow(
        self, 
        ticker: str, 
        year_start: int | None = None, 
        year_end: int | None = None
    ) -> dict:
        return statusinvest.cash_flow(self._clean_ticker(ticker), year_start, year_end)

    @cache_it
    def multiples(self, ticker: str) -> dict:
        return statusinvest.multiples(self._clean_ticker(ticker))

    @cache_it
    def dividends(self, ticker: str) -> list[dict]:
        return statusinvest.dividends(self._clean_ticker(ticker))

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
        return statusinvest.payouts(self._clean_ticker(ticker))

    @cache_it
    def earnings_release_pdf_path(self, ticker: str) -> str:
        clean_t = self._clean_ticker(ticker)
        results_trimestrais = fundamentus.resultados_trimestrais(clean_t)
        download_link = results_trimestrais[0]['download_link'] if results_trimestrais else None
        if not download_link:
            apres = fundamentus.apresentacoes(clean_t)
            download_link = apres[0]['download_link'] if apres else None

        if not download_link:
            raise ValueError('Não foi possível encontrar o earnings release para o ticker informado.')

        import requests
        import os
        import tempfile
        
        try:
            content = requests.get(download_link, timeout=15).content
            tmp_path = os.path.join(tempfile.gettempdir(), f"{ticker}_earnings.pdf")
            with open(tmp_path, 'wb') as f:
                f.write(content)
            return tmp_path
        except Exception as e:
            raise ValueError(f"Faha no download do arquivo PDF: {e}")

    @cache_it
    def news(self, ticker: str) -> list[dict]:
        import yfinance as yf
        try:
            # Para o Brasil, o yfinance precisa do sufixo .SA
            clean_t = self._clean_ticker(ticker)
            tk = yf.Ticker(f"{clean_t}.SA")
            yf_news = tk.news
            if not yf_news:
                return []
            
            result = []
            for item in yf_news[:8]:
                result.append({
                    'title': item.get('title', ''),
                    'url': item.get('link', ''),
                    'body': item.get('publisher', ''),
                    'content': item.get('title', '')
                })
            return result
        except Exception:
            return []


