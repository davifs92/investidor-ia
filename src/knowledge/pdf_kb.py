from agno.knowledge.pdf import PDFKnowledgeBase, PDFReader
from agno.vectordb.lancedb import LanceDb, SearchType
from agno.embedder.openai import OpenAIEmbedder
from agno.embedder.google import GeminiEmbedder

from src.settings import PROVIDER, API_KEY

def get_earnings_kb(pdf_path: str, ticker: str) -> PDFKnowledgeBase:
    """
    Instancia o Banco Vetorial efêmero contendo os pedaços (chunks) do PDF de Release de Resultados lido.
    Utiliza o LanceDb na pasta temp do sistema operacional para isolar e evitar concorrência ou base suja.
    """
    lancedb_tmp_dir = f"/tmp/lancedb_investidor_ia/earnings_{ticker}"
    
    vector_db = LanceDb(
        table_name="earnings_table",
        uri=lancedb_tmp_dir,
        search_type=SearchType.vector,
    )

    # Seleciona o embedder baseado no provider
    if PROVIDER == 'gemini':
        embedder = GeminiEmbedder(api_key=API_KEY)
    else:
        # Default para OpenAI, garantindo que a chave seja passada
        embedder = OpenAIEmbedder(api_key=API_KEY)

    knowledge_base = PDFKnowledgeBase(
        path=pdf_path,
        vector_db=vector_db,
        reader=PDFReader(chunk=True),
        embedder=embedder
    )

    # Carrega os vetores destrutivamente para garantir o relatório novo toda a vez que rodar
    knowledge_base.load(recreate=True)
    
    return knowledge_base
