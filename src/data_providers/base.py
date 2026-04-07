from abc import ABC, abstractmethod
from typing import Literal

class BaseDataProvider(ABC):
    @abstractmethod
    def details(self, ticker: str) -> dict:
        pass

    @abstractmethod
    def name(self, ticker: str) -> str:
        pass

    @abstractmethod
    def income_statement(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> dict:
        pass

    @abstractmethod
    def balance_sheet(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> dict:
        pass

    @abstractmethod
    def cash_flow(
        self, 
        ticker: str, 
        year_start: int | None = None, 
        year_end: int | None = None
    ) -> dict:
        pass

    @abstractmethod
    def multiples(self, ticker: str) -> dict:
        pass

    @abstractmethod
    def dividends(self, ticker: str) -> list[dict]:
        pass

    @abstractmethod
    def dividends_by_year(self, ticker: str) -> list[dict]:
        pass

    @abstractmethod
    def screener(self):
        pass

    @abstractmethod
    def payouts(self, ticker: str) -> list[dict]:
        pass

    @abstractmethod
    def earnings_release_pdf_path(self, ticker: str) -> str:
        pass

