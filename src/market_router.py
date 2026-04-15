from src.data_providers.br.provider import BRDataProvider
from src.data_providers.us.provider import USDataProvider
from src.data_providers.base import BaseDataProvider

class MarketRouter:
    @staticmethod
    def get_provider(ticker: str, market: str | None = None) -> BaseDataProvider:
        """
        Roteador multi-mercado.
        - Se 'market' for fornecido ('BR' ou 'US'), usa o provedor correspondente.
        - Caso contrário, identifica o país através da formatação do Ticker (.SA).
        """
        if market == 'BR':
            return BRDataProvider()
        if market == 'US':
            return USDataProvider()
            
        if ticker.upper().endswith('.SA'):
            return BRDataProvider()
            
        return USDataProvider()
