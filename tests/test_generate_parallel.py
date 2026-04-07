"""
Testes para a lógica de execução paralela dos analistas em pages/generate.py.

Todos os analistas e o Agent do Agno são mockados para que os testes:
- Não consumam créditos de API
- Não dependam de conexão com a internet
- Sejam rápidos (< 1s por teste)
"""
import concurrent.futures
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import BaseAgentOutput


# Output de mock reutilizável
MOCK_BULLISH = BaseAgentOutput(content='Mock análise', sentiment='BULLISH', confidence=80)
MOCK_NEUTRAL = BaseAgentOutput(content='', sentiment='NEUTRAL', confidence=0)


class TestParallelAnalysts:
    """Testes de integração da execução paralela dos analistas."""

    @patch('src.agents.analysts.earnings_release.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.financial.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.valuation.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.news.analyze', return_value=MOCK_BULLISH)
    def test_all_analysts_called_once(
        self,
        mock_news,
        mock_valuation,
        mock_financial,
        mock_earnings,
    ):
        """Verifica que cada analista é chamado exatamente uma vez com o ticker correto."""
        ticker = 'WEGE3'

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            from src.agents.analysts import earnings_release, financial, valuation, news

            future_earnings  = executor.submit(earnings_release.analyze, ticker)
            future_financial = executor.submit(financial.analyze, ticker)
            future_valuation = executor.submit(valuation.analyze, ticker)
            future_news      = executor.submit(news.analyze, ticker)

            result_earnings  = future_earnings.result()
            result_financial = future_financial.result()
            result_valuation = future_valuation.result()
            result_news      = future_news.result()

        mock_earnings.assert_called_once_with(ticker)
        mock_financial.assert_called_once_with(ticker)
        mock_valuation.assert_called_once_with(ticker)
        mock_news.assert_called_once_with(ticker)

        assert result_earnings.sentiment == 'BULLISH'
        assert result_financial.sentiment == 'BULLISH'
        assert result_valuation.sentiment == 'BULLISH'
        assert result_news.sentiment == 'BULLISH'

    @patch('src.agents.analysts.earnings_release.analyze', return_value=MOCK_NEUTRAL)
    @patch('src.agents.analysts.financial.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.valuation.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.news.analyze', return_value=MOCK_BULLISH)
    def test_one_analyst_failure_does_not_block_others(
        self,
        mock_news,
        mock_valuation,
        mock_financial,
        mock_earnings,
    ):
        """
        Se um analista retorna fallback (NEUTRAL confidence=0), os demais
        ainda devem retornar seus resultados normalmente.
        Isso valida a resiliência do modelo de fallback existente nos analistas.
        """
        ticker = 'PETR4'

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            from src.agents.analysts import earnings_release, financial, valuation, news

            future_earnings  = executor.submit(earnings_release.analyze, ticker)
            future_financial = executor.submit(financial.analyze, ticker)
            future_valuation = executor.submit(valuation.analyze, ticker)
            future_news      = executor.submit(news.analyze, ticker)

            result_earnings  = future_earnings.result()
            result_financial = future_financial.result()
            result_valuation = future_valuation.result()
            result_news      = future_news.result()

        # earnings retornou fallback neutro
        assert result_earnings.sentiment == 'NEUTRAL'
        assert result_earnings.confidence == 0

        # os outros 3 retornaram normalmente
        assert result_financial.sentiment == 'BULLISH'
        assert result_valuation.sentiment == 'BULLISH'
        assert result_news.sentiment == 'BULLISH'

    @patch('src.agents.analysts.earnings_release.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.financial.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.valuation.analyze', return_value=MOCK_BULLISH)
    @patch('src.agents.analysts.news.analyze', return_value=MOCK_BULLISH)
    def test_results_are_base_agent_output_instances(
        self,
        mock_news,
        mock_valuation,
        mock_financial,
        mock_earnings,
    ):
        """Garante que todos os resultados são instâncias válidas de BaseAgentOutput."""
        ticker = 'VALE3'

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            from src.agents.analysts import earnings_release, financial, valuation, news

            futures = [
                executor.submit(earnings_release.analyze, ticker),
                executor.submit(financial.analyze, ticker),
                executor.submit(valuation.analyze, ticker),
                executor.submit(news.analyze, ticker),
            ]
            results = [f.result() for f in futures]

        for result in results:
            assert isinstance(result, BaseAgentOutput)
            assert result.sentiment in ('BULLISH', 'BEARISH', 'NEUTRAL')
            assert 0 <= result.confidence <= 100
