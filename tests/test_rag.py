import pytest
import os
from unittest.mock import patch, MagicMock

from src.data_providers.br.provider import BRDataProvider
from src.knowledge.pdf_kb import get_earnings_kb
from agno.knowledge.pdf import PDFKnowledgeBase

@patch('src.data_providers.br.provider.requests.get')
@patch('src.data_providers.br.provider.fundamentus.resultados_trimestrais')
def test_earnings_release_pdf_path_br(mock_resultados, mock_requests_get):
    """Testa se o provedor BR consegue baixar e salvar no disco fisicamente o PDF usando tempfile."""
    
    # Mock do retorno da API Fundamentus Legada
    mock_resultados.return_value = [{'download_link': 'http://fakelink.com/pdf.pdf'}]
    
    # Mock do Response HTTP
    mock_response = MagicMock()
    mock_response.content = b"%PDF-1.4 mock pdf bin"
    mock_requests_get.return_value = mock_response

    provider = BRDataProvider()
    pdf_path = provider.earnings_release_pdf_path("MOCK3")

    # Garante que um caminho local real foi retornado e salvo em /tmp/ ou C:/temp
    assert pdf_path is not None
    assert pdf_path.endswith("_earnings.pdf")
    assert "MOCK3" in pdf_path
    assert os.path.exists(pdf_path)

@patch('src.knowledge.pdf_kb.LanceDb')
@patch('src.knowledge.pdf_kb.PDFKnowledgeBase.load')
def test_get_earnings_kb(mock_load, mock_lancedb):
    """Garante que a KnowledgeBase de RAG é devidamente montada localmente no esquema Lancedb e aponta pro path correto."""
    mock_pdf_path = "/tmp/mock_path.pdf"
    
    # Executa a função
    kb = get_earnings_kb(mock_pdf_path, "TEST3")
    
    # Confirmações das instancias internas criadas
    mock_lancedb.assert_called_once()
    assert isinstance(kb, PDFKnowledgeBase)
    assert kb.path == mock_pdf_path
    
    # Confirmar que ordenamos o agente mastigar o parser de PDF forçadamente (Recreate=True)
    mock_load.assert_called_once_with(recreate=True)
