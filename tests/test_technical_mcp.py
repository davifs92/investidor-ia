import time
from unittest.mock import MagicMock, patch

import pandas as pd

from src.agents.analysts.technical import analyze
from src.agents.base import BaseAgentOutput


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
        command="python mcp_servers/investmcp/technical_analysis.py"
    )
    
    # Verifica se os args do Agent estavam corretos e com show_tool_calls=False para nao sujar o terminal
    args, kwargs = mock_agent_class.call_args
    assert 'tools' in kwargs
    assert 'show_tool_calls' in kwargs and kwargs['show_tool_calls'] is False
    assert 'response_model' not in kwargs
    
    # Verifica se chamou agent.run() e retornou corretamente
    mock_agent_instance.run.assert_called_once()
    assert result == mock_response.content

@patch('src.agents.analysts.technical._build_fallback_analysis')
@patch('src.agents.analysts.technical.MCPTools.__init__', side_effect=Exception("FastMCP Binário Error"))
def test_technical_analysis_exception_fallback(mock_mcp_init, mock_build_fallback):
    """Quando o MCP falha na inicialização, o analista deve usar fallback automático."""
    fallback = BaseAgentOutput(content="Fallback OK", sentiment="NEUTRAL", confidence=64)
    mock_build_fallback.return_value = fallback

    result = analyze("AAPL")

    assert result == fallback
    mock_build_fallback.assert_called_once_with("AAPL", market=None)


@patch('src.agents.analysts.technical._build_fallback_analysis')
@patch('src.agents.analysts.technical.Agent')
@patch('src.agents.analysts.technical.MCPTools.__init__', return_value=None)
def test_technical_analysis_llm_no_data_triggers_fallback(mock_mcp_init, mock_agent_class, mock_build_fallback):
    """Se o LLM retornar aviso de falta de dados/MCP, também deve cair no fallback automático."""
    mock_response = MagicMock()
    mock_response.content = BaseAgentOutput(
        content="Não consigo obter dados de mercado diretamente neste ambiente.",
        sentiment="NEUTRAL",
        confidence=0,
    )
    mock_agent_class.return_value.run.return_value = mock_response

    fallback = BaseAgentOutput(content="Fallback yfinance", sentiment="BULLISH", confidence=78)
    mock_build_fallback.return_value = fallback

    result = analyze("AMZN")

    assert result == fallback
    mock_build_fallback.assert_called_once_with("AMZN", market=None)


@patch('src.agents.analysts.technical.requests.get')
def test_alpha_vantage_parser_supports_time_series_alternative_key(mock_get):
    from src.agents.analysts.technical import _price_history_from_alpha_vantage

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'Time Series (Daily) X': {
            '2026-04-09': {'4. close': '100.0'},
            '2026-04-08': {'4. close': '99.0'},
        }
    }
    mock_get.return_value = mock_response

    with patch('src.agents.analysts.technical.config', return_value='demo-key'):
        series = _price_history_from_alpha_vantage('AAPL')
    assert isinstance(series, pd.Series)
    assert len(series) == 2


@patch('src.agents.analysts.technical.time.sleep', return_value=None)
@patch('src.agents.analysts.technical.requests.get')
def test_alpha_vantage_rate_limit_raises_clear_error(mock_get, mock_sleep):
    from src.agents.analysts.technical import _price_history_from_alpha_vantage

    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        'Information': 'Thank you for using Alpha Vantage! Our standard API call frequency is 5 calls per minute.'
    }
    mock_get.return_value = mock_response

    with patch('src.agents.analysts.technical.config', return_value='demo-key'):
        with patch('src.agents.analysts.technical.cache.get', return_value=None):
            with patch('src.agents.analysts.technical.cache.set', return_value=None):
                with patch('src.agents.analysts.technical._ALPHA_MAX_RETRIES', 1):
                    result_error = None
                    try:
                        _price_history_from_alpha_vantage('AAPL')
                    except Exception as exc:
                        result_error = str(exc)

    assert result_error is not None
    assert 'Alpha Vantage' in result_error


@patch('src.agents.analysts.technical.requests.get')
def test_alpha_vantage_skips_call_when_global_cooldown_active(mock_get):
    from src.agents.analysts import technical as technical_mod

    with patch('src.agents.analysts.technical.config', return_value='demo-key'):
        with patch('src.agents.analysts.technical.cache.get', return_value=None):
            with patch.object(technical_mod, '_alpha_rate_limited_until', time.time() + 30):
                error = None
                try:
                    technical_mod._price_history_from_alpha_vantage('MSFT')
                except Exception as exc:
                    error = str(exc)

    mock_get.assert_not_called()
    assert error is not None
    assert 'cooldown global' in error
