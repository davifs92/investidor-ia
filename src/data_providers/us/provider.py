import yfinance as yf
import pandas as pd
from typing import Literal

from src.cache import cache_it
from src.data_providers.base import BaseDataProvider

class USDataProvider(BaseDataProvider):
    """Provedor de dados para o mercado Americano (NYSE/NASDAQ). Utiliza yfinance sob o capô, normalizando as métricas para português."""
    
    @cache_it
    def details(self, ticker: str) -> dict:
        info = yf.Ticker(ticker).info
        return {
            'nome': info.get('longName', ticker),
            'segmento_de_atuacao': info.get('sector', 'N/A'),
            'descricao': info.get('longBusinessSummary', '')
        }

    @cache_it
    def name(self, ticker: str) -> str:
        return self.details(ticker)['nome']

    def _normalize_df(self, df: pd.DataFrame, mapping: dict) -> list[dict]:
        if df is None or df.empty:
            return []
            
        result = []
        for col in df.columns:
            period_data = df[col].to_dict()
            mapped = {'data': col.strftime('%Y-%m-%d')} if hasattr(col, 'strftime') else {'data': str(col)}
            for pt_key, eng_key in mapping.items():
                val = period_data.get(eng_key, 0.0)
                mapped[pt_key] = float(val) if not pd.isna(val) else 0.0
            result.append(mapped)
            
        return sorted(result, key=lambda x: x['data'], reverse=True)

    @cache_it
    def income_statement(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> list[dict]:
        tk = yf.Ticker(ticker)
        df = tk.financials if period == 'annual' else tk.quarterly_financials
        mapping = {
            'receita_liquida': 'Total Revenue',
            'lucro_liquido': 'Net Income',
            'ebitda': 'EBITDA',
            'ebit': 'EBIT'
        }
        return self._normalize_df(df, mapping)

    @cache_it
    def balance_sheet(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> list[dict]:
        tk = yf.Ticker(ticker)
        df = tk.balance_sheet if period == 'annual' else tk.quarterly_balance_sheet
        mapping = {
            'ativo_total': 'Total Assets',
            'patrimonio_liquido': 'Stockholders Equity',
            'divida_bruta': 'Total Debt',
            'caixa_equivalentes': 'Cash And Cash Equivalents'
        }
        return self._normalize_df(df, mapping)

    @cache_it
    def cash_flow(
        self, 
        ticker: str, 
        year_start: int | None = None, 
        year_end: int | None = None
    ) -> list[dict]:
        tk = yf.Ticker(ticker)
        df = tk.cash_flow
        mapping = {
            'fco': 'Operating Cash Flow',
            'fci': 'Investing Cash Flow',
            'fcf': 'Financing Cash Flow',
            'fc_livre': 'Free Cash Flow'
        }
        return self._normalize_df(df, mapping)

    @cache_it
    def multiples(self, ticker: str) -> dict:
        info = yf.Ticker(ticker).info
        return {
            'p_l': info.get('trailingPE', 0.0),
            'p_vp': info.get('priceToBook', 0.0),
            'dy': info.get('trailingAnnualDividendYield', 0.0) or 0.0,
            'roe': info.get('returnOnEquity', 0.0) or 0.0,
            'margem_liquida': info.get('profitMargins', 0.0) or 0.0,
            'ev_ebitda': info.get('enterpriseToEbitda', 0.0) or 0.0
        }

    @cache_it
    def dividends(self, ticker: str) -> list[dict]:
        divs = yf.Ticker(ticker).dividends
        if divs is None or divs.empty:
            return []
        result = []
        for date, value in divs.items():
            result.append({'data_pagamento': date.strftime('%Y-%m-%d'), 'valor': float(value)})
        return sorted(result, key=lambda x: x['data_pagamento'], reverse=True)

    @cache_it
    def dividends_by_year(self, ticker: str) -> list[dict]:
        divs = self.dividends(ticker)
        yearly = {}
        for d in divs:
            y = int(d['data_pagamento'][:4])
            yearly[y] = yearly.get(y, 0.0) + d['valor']
        return [{'ano': y, 'valor': round(v, 4)} for y, v in sorted(yearly.items(), key=lambda x: x['ano'])]

    @cache_it
    def screener(self):
        return []

    @cache_it
    def payouts(self, ticker: str) -> list[dict]:
        return []

    @cache_it
    def earnings_release_pdf_path(self, ticker: str) -> str:
        # Placeholder provisório até a integração oficial da SEC EDGAR API
        # Lança erro gracioso que será tratado pelo analyst fallback
        raise ValueError(f"Earnings Release para o ticker US {ticker} não implementado ainda (EDGAR pendente).")


