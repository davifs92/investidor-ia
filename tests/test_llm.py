"""
Testes para o wrapper ask() em src/llm.py.

O Agent do Agno e get_model() são mockados para que os testes:
- Não consumam créditos de API (Gemini, OpenAI, etc.)
- Não dependam de configuração de API key no ambiente de CI
- Sejam rápidos e determinísticos
"""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from src.agents.base import BaseAgentOutput


class TestAsk:
    """Testes do wrapper ask() em src/llm.py."""

    @patch('src.llm.get_model')
    @patch('src.llm.Agent')
    def test_ask_returns_string_when_no_response_model(self, mock_agent_class, mock_get_model):
        """Quando response_model=None, ask() deve retornar o conteúdo como string."""
        from src.llm import ask

        # configura o mock do Agent e seu retorno
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value.content = 'Resposta em texto livre'
        mock_agent_class.return_value = mock_agent_instance

        result = ask(message='Qual a Selic atual?')

        assert result == 'Resposta em texto livre'
        mock_agent_instance.run.assert_called_once_with('Qual a Selic atual?')

    @patch('src.llm.get_model')
    @patch('src.llm.Agent')
    def test_ask_returns_pydantic_instance_when_response_model_given(
        self, mock_agent_class, mock_get_model
    ):
        """Quando response_model é fornecido, ask() deve retornar a instância Pydantic do Agno."""
        from src.llm import ask

        expected_output = BaseAgentOutput(
            content='Análise mock', sentiment='BULLISH', confidence=75
        )
        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value.content = expected_output
        mock_agent_class.return_value = mock_agent_instance

        result = ask(message='Analise WEGE3', response_model=BaseAgentOutput)

        assert isinstance(result, BaseAgentOutput)
        assert result.sentiment == 'BULLISH'
        assert result.confidence == 75

    @patch('src.llm.get_model')
    @patch('src.llm.Agent')
    def test_ask_passes_temperature_to_get_model(self, mock_agent_class, mock_get_model):
        """Verifica que a temperature é repassada corretamente para get_model()."""
        from src.llm import ask

        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value.content = 'ok'
        mock_agent_class.return_value = mock_agent_instance

        ask(message='Teste', temperature=0.2)

        mock_get_model.assert_called_once_with(temperature=0.2)

    @patch('src.llm.get_model')
    @patch('src.llm.Agent')
    def test_ask_agent_created_with_retries(self, mock_agent_class, mock_get_model):
        """Verifica que o Agent é instanciado com retries=3 (não duplicar lógica de retry)."""
        from src.llm import ask

        mock_agent_instance = MagicMock()
        mock_agent_instance.run.return_value.content = 'ok'
        mock_agent_class.return_value = mock_agent_instance

        ask(message='Teste')

        _, kwargs = mock_agent_class.call_args
        assert kwargs.get('retries') == 3

    @patch('src.llm.get_model', side_effect=ValueError('API key não configurada'))
    def test_ask_propagates_get_model_error(self, mock_get_model):
        """Se get_model() lançar ValueError (ex: API key ausente), ask() deve propagar."""
        from src.llm import ask

        with pytest.raises(ValueError, match='API key não configurada'):
            ask(message='Qualquer coisa')
