import pytest
from unittest.mock import patch, MagicMock

from src.agents.analysts.technical import analyze
from src.agents.base import BaseAgentOutput
from agno.tools.mcp import MCPTools

@patch('src.agents.analysts.technical.Agent')
@patch('src.agents.analysts.technical.MCPTools.__init__', return_value=None)
def test_technical_analysis_success(mock_mcp_init, mock_agent_class):
    """Garante que a analise técnica chama o Agent e estrutura o MCPTool apontando para o servidor python local."""
    
    # Prepara um Mock do BaseAgentOutput real do Agno Response (RunResponse)
    mock_response = MagicMock()
    mock_response.content = BaseAgentOutput(content="Analise OK do TA-Lib", sentiment="BULLISH", confidence=85)
    
    mock_agent_instance = mock_agent_class.return_value
    mock_agent_instance.run.return_value = mock_response
    
    # Executa a função do Technical Analyst
    result = analyze("PETR4.SA")
    
    # Confirmar asserções (Least Astonishment e Mocking exigidos pelo agents.md)
    mock_mcp_init.assert_called_once_with(
        command="python",
        args=["mcp_servers/investmcp/technical_analysis.py"]
    )
    
    # Verifica se os args do Agent estavam corretos e com show_tool_calls=False para nao sujar o terminal
    args, kwargs = mock_agent_class.call_args
    assert 'tools' in kwargs
    assert 'show_tool_calls' in kwargs and kwargs['show_tool_calls'] is False
    assert kwargs['response_model'] == BaseAgentOutput
    
    # Verifica se chamou agent.run() e retornou corretamente
    mock_agent_instance.run.assert_called_once()
    assert result == mock_response.content

@patch('src.agents.analysts.technical.MCPTools.__init__', side_effect=Exception("FastMCP Binário Error"))
def test_technical_analysis_exception_fallback(mock_mcp_init):
    """Garante a Resiliência do analista em Null-Safety caso o Submódulo externo não funcione (ex: Lib TA-Lib quebrando)."""
    
    result = analyze("AAPL")
    
    # Afirma fallback formatado e catch bloqueando stack trace 
    assert isinstance(result, BaseAgentOutput)
    assert result.sentiment == "NEUTRAL"
    assert result.confidence == 0
    assert "Erro de MCP Técnico Inoperante" in result.content
