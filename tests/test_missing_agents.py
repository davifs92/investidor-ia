from unittest.mock import patch, MagicMock

import pytest

from src.agents.analysts import news, valuation, earnings_release
from src.agents.investors import barsi, buffett
from src.agents.base import BaseAgentOutput

@pytest.fixture
def mock_agent_run():
    with patch("agno.agent.Agent.run") as mock_run:
        mock_run.return_value = MagicMock(content="Conteúdo Analítico Mockado")
        yield mock_run

def test_news_analyst_br(mock_agent_run):
    with patch("src.agents.analysts.news._search_news_einvestidor", return_value=[{"title": "Teste", "content": "Teste"}]), \
         patch("src.data.stocks.name", return_value="Petrobras"):
        resultado = news.analyze("PETR4.SA")
        assert mock_agent_run.called
        call_args = mock_agent_run.call_args[0][0]
        assert "Brasil (B3)" in call_args

def test_news_analyst_us(mock_agent_run):
    with patch("src.agents.analysts.news._search_news_international", return_value=[{"title": "Test US", "content": "Test US"}]), \
         patch("src.data.stocks.name", return_value="Apple"):
        resultado = news.analyze("AAPL")
        assert mock_agent_run.called
        call_args = mock_agent_run.call_args[0][0]
        assert "Internacional (NYSE/NASDAQ)" in call_args

def test_valuation_analyst_br(mock_agent_run):
    screener_mock = [{"ticker": "PETR4", "liquidezmediadiaria": 1000, "price": 30, "segmentname": "Petróleo"}]
    with patch("src.data.stocks.screener", return_value=screener_mock), \
         patch("src.data.stocks.name", return_value="Petrobras"), \
         patch("src.data.stocks.details", return_value={"nome": "Petrobras", "segmento_de_atuacao": "Petróleo", "preco": 30.0}), \
         patch("src.data.stocks.multiples", return_value=[{"p_l": 5.0, "p_vp": 1.0}]):
        resultado = valuation.analyze("PETR4.SA")
        assert mock_agent_run.called

def test_valuation_analyst_us_empty_screener(mock_agent_run):
    with patch("src.data.stocks.screener", return_value=[]), \
         patch("src.data.stocks.name", return_value="Apple"), \
         patch("src.data.stocks.details", return_value={"nome": "Apple"}), \
         patch("src.data.stocks.multiples", return_value=[]):
        resultado = valuation.analyze("AAPL")
        assert mock_agent_run.called
        # Com screener vazio, o código tem fallback pra 'N/A' que alimenta o LLM

def test_earnings_release_analyst(mock_agent_run):
    with patch("src.data.stocks.name", return_value="Petrobras"), \
         patch("src.data.stocks.earnings_release_pdf_path", return_value="/tmp/test.pdf"), \
         patch("src.agents.analysts.earnings_release.get_earnings_kb") as mock_kb:
        mock_kb.return_value = MagicMock()
        resultado = earnings_release.analyze("PETR4.SA")
        assert mock_agent_run.called
        call_args = mock_agent_run.call_args[0][0]
        assert "Data:" in call_args
        assert "RAG" in call_args

def test_barsi_analyst(mock_agent_run):
    with patch("src.data.stocks.name", return_value="Banco do Brasil"), \
         patch("src.data.stocks.details", return_value={"nome": "Banco do Brasil", "segmento_de_atuacao": "Bancos"}), \
         patch("src.data.stocks.dividends_by_year", return_value=[{"ano": 2023, "valor": 5.0}]), \
         patch("src.data.stocks.income_statement", return_value=[{"data": "2023-12-31", "receita_liquida": 5000, "lucro_liquido": 1000, "fco": 200, "capex": 50}]), \
         patch("src.data.stocks.multiples", return_value=[{"p_l": 5, "p_vp": 1.2, "lpa": 2, "vpa": 10}]), \
         patch("src.data.stocks.payouts", return_value=[{"ano": 2023, "payout": 0.5}]), \
         patch("src.data.stocks.balance_sheet", return_value=[]):
        resultado = barsi.analyze(
            "BBAS3.SA",
            earnings_release_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            financial_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            valuation_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            news_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            macro_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0)
        )
        assert mock_agent_run.called

def test_buffett_analyst(mock_agent_run):
    with patch("src.data.stocks.name", return_value="Apple"), \
         patch("src.data.stocks.dividends_by_year", return_value=[{"ano": 2023, "valor": 5.0}]), \
         patch("src.data.stocks.income_statement", return_value=[{"data": "2023-12-31", "receita_liquida": 10000, "lucro_liquido": 500, "fco": 200, "capex": -50}]), \
         patch("src.data.stocks.balance_sheet", return_value=[]), \
         patch("src.data.stocks.cash_flow", return_value=[]), \
         patch("src.data.stocks.multiples", return_value=[{"p_l": 20}]), \
         patch("src.data.stocks.details", return_value={"segmento_de_atuacao": "Tech"}):
        resultado = buffett.analyze(
            "AAPL",
            earnings_release_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            financial_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            valuation_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            news_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            macro_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
            technical_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0)
        )
        assert mock_agent_run.called
