import json


from agno.tools.toolkit import Toolkit


from src.data import stocks


class StocksTools(Toolkit):
    def __init__(self, market: str | None = None):
        super().__init__(name='stocks_tools')
        self.market = market
        self.register(self.detalhes)
        self.register(self.multiplos)
        self.register(self.dados_financeiros)
        self.register(self.dividendos)

    def detalhes(self, ticker: str) -> str:
        """
        Obtém os detalhes da ação.

        Args:
            ticker (str): O ticker para obter os detalhes.

        Returns:
            str: um JSON contendo os detalhes da ação.
        """
        return json.dumps(stocks.details(ticker, market=self.market))

    def multiplos(self, ticker: str, limit: int = 10) -> str:
        """
        Obtém o histórico anual de multiplos da ação.

        Args:
            ticker (str): O ticker para obter os multiplos.
            limit (int): O número máximo de anos a serem retornados. Default é 10 (últimos 10 anos).

        Returns:
            str: um JSON contendo o histórico anual de multiplos da ação.
        """
        return json.dumps(stocks.multiples(ticker, market=self.market)[:limit])

    def dados_financeiros(
        self,
        ticker: str,
        document: str,
        period: str = 'quarter',
        resultado_ltm: bool = False,
    ) -> str:
        """
        Obtém os dados financeiros da ação.
        """
        if document == 'resultados':
            data = stocks.income_statement(ticker, period=period, market=self.market)
            if period == 'annual' and resultado_ltm:
                data = data[1:]
            return json.dumps(data)
        elif document == 'balanco':
            data = stocks.balance_sheet(ticker, period=period, market=self.market)
            return json.dumps(data)
        elif document == 'fluxo_caixa':
            data = stocks.cash_flow(ticker, market=self.market)
            return json.dumps(data)

    def dividendos(self, ticker: str, agrupar_por_ano: bool = False) -> str:
        """
        Obtém os dividendos da ação.
        """
        if agrupar_por_ano:
            return json.dumps(stocks.dividends_by_year(ticker, market=self.market))
        return json.dumps(stocks.dividendos(ticker, market=self.market))
