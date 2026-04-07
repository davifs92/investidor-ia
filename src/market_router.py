from src.data_providers.br.provider import BRDataProvider
from src.data_providers.us.provider import USDataProvider
from src.data_providers.base import BaseDataProvider

class MarketRouter:
    @staticmethod
    def get_provider(ticker: str) -> BaseDataProvider:
        """
        Roteador multi-mercado que identifica o país através da formatação do Ticker.
        - Tickers com sufixo .SA são roteados para o Provider Brasil (Fundamentus/StatusInvest)
        - Tickers internacionais são roteados para o Provider Americano (yfinance)
        """
        if ticker.upper().endswith('.SA'):
            return BRDataProvider()
        return USDataProvider()
