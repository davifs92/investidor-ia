from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.agents.base import BaseAgentOutput


@patch('src.agents.analysts.valuation.stocks.multiples')
def test_us_peers_snapshot_returns_na_when_no_peer_has_data(mock_multiples):
    from src.agents.analysts.valuation import _us_peers_snapshot

    mock_multiples.return_value = [{'p_l': 0.0, 'p_vp': 0.0, 'dy': 0.0, 'roe': 0.0, 'margem_liquida': 0.0, 'ev_ebitda': 0.0}]

    peers_mean, peers_median, peers_used = _us_peers_snapshot('Technology', 'MSFT')

    assert peers_mean.startswith('N/A')
    assert peers_median == 'N/A'
    assert peers_used == 'N/A'


@patch('src.agents.analysts.valuation.get_model')
@patch('src.agents.analysts.valuation.Agent')
@patch('src.agents.analysts.valuation.stocks.screener', return_value=[])
@patch('src.agents.analysts.valuation.stocks.details')
@patch('src.agents.analysts.valuation.stocks.multiples')
def test_valuation_uses_us_peers_when_screener_is_empty(
    mock_multiples,
    mock_details,
    mock_screener,
    mock_agent_class,
    mock_get_model,
):
    from src.agents.analysts.valuation import analyze

    mock_details.return_value = {
        'nome': 'Microsoft Corporation',
        'segmento_de_atuacao': 'Technology',
        'preco': 412.0,
    }

    def _multiples_side_effect(ticker, market=None):
        if ticker == 'MSFT':
            return [{
                'ano': 'LTM',
                'preco_atual': 412.0,
                'p_l': 31.2,
                'p_vp': 10.1,
                'dy': 0.007,
                'roe': 0.32,
                'margem_liquida': 0.35,
                'ev_ebitda': 22.5,
            }]
        return [{
            'ano': 'LTM',
            'preco_atual': 100.0,
            'p_l': 25.0,
            'p_vp': 8.0,
            'dy': 0.005,
            'roe': 0.20,
            'margem_liquida': 0.22,
            'ev_ebitda': 18.0,
        }]

    mock_multiples.side_effect = _multiples_side_effect

    mock_agent = MagicMock()
    mock_agent.run.return_value = SimpleNamespace(
        content=BaseAgentOutput(
            content='Valuation com peers US carregados',
            sentiment='BULLISH',
            confidence=75,
        )
    )
    mock_agent_class.return_value = mock_agent

    result = analyze('MSFT', market='US')

    assert isinstance(result, BaseAgentOutput)
    assert result.sentiment == 'BULLISH'

    run_prompt = mock_agent.run.call_args[0][0]
    assert 'Peers usados' in run_prompt
    assert 'N/A (screener não disponível para mercado US)' not in run_prompt
