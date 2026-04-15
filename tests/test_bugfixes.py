from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.agents.base import BaseAgentOutput

try:
    import fpdf  # noqa: F401
    _FPDF_AVAILABLE = True
except Exception:
    _FPDF_AVAILABLE = False


class TestEarningsReleaseUS:
    @patch('src.agents.analysts.earnings_release.get_model')
    @patch('src.agents.analysts.earnings_release.Agent')
    @patch('src.agents.analysts.earnings_release.stocks.earnings_release_summary')
    @patch('src.agents.analysts.earnings_release.stocks.details')
    def test_us_uses_sec_context_instead_of_static_fallback(
        self,
        mock_details,
        mock_earnings_summary,
        mock_agent_class,
        mock_get_model,
    ):
        from src.agents.analysts.earnings_release import analyze

        mock_details.return_value = {'nome': 'Apple Inc.'}
        mock_earnings_summary.return_value = 'Último relatório oficial: 10-Q protocolado em 2026-02-01.'

        mock_agent = MagicMock()
        mock_agent.run.return_value = SimpleNamespace(
            content=BaseAgentOutput(
                content='Resumo SEC analisado com sucesso',
                sentiment='BULLISH',
                confidence=82,
            )
        )
        mock_agent_class.return_value = mock_agent

        result = analyze('AAPL', market='US')

        assert isinstance(result, BaseAgentOutput)
        assert result.sentiment == 'BULLISH'
        assert 'RAG para ativos americanos ainda não implementada' not in result.content
        mock_earnings_summary.assert_called_once_with('AAPL', market='US')
        assert mock_agent.run.call_count == 1

    @patch('src.agents.analysts.earnings_release.stocks.earnings_release_summary', side_effect=RuntimeError('SEC offline'))
    @patch('src.agents.analysts.earnings_release.stocks.details', return_value={'nome': 'Apple Inc.'})
    def test_us_returns_graceful_neutral_when_sec_summary_fails(self, mock_details, mock_earnings_summary):
        from src.agents.analysts.earnings_release import analyze

        result = analyze('AAPL', market='US')

        assert isinstance(result, BaseAgentOutput)
        assert result.sentiment == 'NEUTRAL'
        assert result.confidence == 0
        assert 'Não foi possível processar os dados de Earnings Release da SEC' in result.content


@pytest.mark.skipif(
    not _FPDF_AVAILABLE,
    reason='fpdf2 não instalado no ambiente de teste',
)
def test_pdf_generator_guarantees_page_before_writing(monkeypatch):
    from src import utils_pdf

    class FakePDF:
        def __init__(self):
            self._page = 0
            self._y = 100

        def page_no(self):
            return self._page

        def add_page(self):
            self._page += 1

        def _needs_page(self):
            if self.page_no() == 0:
                raise RuntimeError('No page open, you need to call add_page() first')

        def set_auto_page_break(self, auto=True, margin=20):
            pass

        def alias_nb_pages(self):
            pass

        def set_fill_color(self, *args, **kwargs):
            self._needs_page()

        def rect(self, *args, **kwargs):
            self._needs_page()

        def set_text_color(self, *args, **kwargs):
            self._needs_page()

        def set_font(self, *args, **kwargs):
            self._needs_page()

        def set_y(self, y):
            self._needs_page()
            self._y = y

        def cell(self, *args, **kwargs):
            self._needs_page()

        def ln(self, *args, **kwargs):
            self._needs_page()

        def write_html(self, *args, **kwargs):
            self._needs_page()

        def multi_cell(self, *args, **kwargs):
            self._needs_page()

        def get_y(self):
            self._needs_page()
            return self._y

        def set_draw_color(self, *args, **kwargs):
            self._needs_page()

        def line(self, *args, **kwargs):
            self._needs_page()

        def output(self):
            self._needs_page()
            return b'%PDF-FAKE%'

    monkeypatch.setattr(utils_pdf, 'MyFPDF', FakePDF)

    data = {
        'investor': {'sentiment': 'NEUTRAL', 'confidence': 50, 'content': '# Teste\nConteúdo'},
        'analysts': {
            'earnings_release': {'sentiment': 'NEUTRAL', 'confidence': 0, 'content': 'Texto'},
            'financial': {'sentiment': 'BULLISH', 'confidence': 80, 'content': 'Texto'},
            'valuation': {'sentiment': 'NEUTRAL', 'confidence': 45, 'content': 'Texto'},
            'news': {'sentiment': 'BEARISH', 'confidence': 30, 'content': 'Texto'},
        },
    }

    pdf_bytes = utils_pdf.generate_pdf_bytes(
        ticker='AAPL',
        investor_name='buffett',
        generated_at=SimpleNamespace(strftime=lambda *_: '01/01/2026 10:00'),
        data=data,
    )

    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b'%PDF-FAKE%')
