from unittest.mock import patch, MagicMock

import pytest

from src.agents.analysts import macro, technical
from src.agents.investors import graham, lynch
from src.agents.base import BaseAgentOutput

@pytest.fixture
def mock_agent_run():
    with patch("agno.agent.Agent.run") as mock_run:
        mock_run.return_value = MagicMock(content="Conteúdo Gerado.")
        yield mock_run


def test_macro_analyst_br(mock_agent_run):
    with patch("src.agents.analysts.macro.get_selic", return_value="10.50"):
        resultado = macro.analyze("PETR4.SA")
        assert isinstance(resultado, str) or isinstance(resultado, BaseAgentOutput)
        assert mock_agent_run.called
        
        call_args = mock_agent_run.call_args[0][0]
        assert "Data Base:" in call_args
        assert "PETR4.SA" in call_args


def test_macro_analyst_us(mock_agent_run):
    with patch("src.agents.analysts.macro.get_fed_funds", return_value="5.25"):
        resultado = macro.analyze("AAPL")
        assert mock_agent_run.called
        
        call_args = mock_agent_run.call_args[0][0]
        assert "Data Base:" in call_args
        assert "AAPL" in call_args


def test_technical_analyst(mock_agent_run):
    # Test that the technical analyst successfully calls agent.run with MCP enabled
    with patch("src.agents.analysts.technical.MCPTools") as mock_mcp:
        resultado = technical.analyze("PETR4.SA")
        assert mock_mcp.called
        assert mock_agent_run.called
        
        call_args = mock_agent_run.call_args[0][0]
        assert "Data Base:" in call_args
        assert "PETR4" in call_args


def test_graham_analyst(mock_agent_run):
    # Just to assert parsing and identity splitting
    with patch("src.data.stocks.balance_sheet") as mock_bs:
        mock_bs.return_value = [{"ativo_circulante": 1000, "passivo_total": 500}]
        with patch("src.data.stocks.income_statement", return_value=[{"receita_liquida": 100, "lucro_liquido": 10, "ebit": 15}] * 5), \
             patch("src.data.stocks.cash_flow", return_value=[]), \
             patch("src.data.stocks.multiples", return_value={}), \
             patch("src.data.stocks.dividends_by_year", return_value=[]), \
             patch("src.data.stocks.name", return_value="Petrobras"), \
             patch("src.data.stocks.details", return_value={}):
             
             resultado = graham.analyze(
                 "PETR4.SA", 
                 earnings_release_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
                 financial_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
                 valuation_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
                 news_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
                 macro_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
                 technical_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0)
             )
             
             assert mock_agent_run.called
             call_args = mock_agent_run.call_args[0][0]
             assert "Data de Hoje:" in call_args


def test_lynch_analyst(mock_agent_run):
    from src.agents.investors import lynch
    with patch("src.data.stocks.income_statement", return_value=[]), \
         patch("src.data.stocks.balance_sheet", return_value=[]), \
         patch("src.data.stocks.cash_flow", return_value=[]), \
         patch("src.data.stocks.multiples", return_value={}), \
         patch("src.data.stocks.dividends_by_year", return_value=[]), \
         patch("src.data.stocks.name", return_value="Apple"), \
         patch("src.data.stocks.details", return_value={}):
         
         resultado = lynch.analyze(
             "AAPL", 
             earnings_release_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
             financial_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
             valuation_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
             news_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
             macro_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0),
             technical_analysis=BaseAgentOutput(content="", sentiment="NEUTRAL", confidence=0)
         )
         
         assert mock_agent_run.called
         call_args = mock_agent_run.call_args[0][0]
         assert "Data de Hoje:" in call_args
