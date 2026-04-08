import datetime

from agno.agent import Agent

from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import get_model
from src.knowledge.pdf_kb import get_earnings_kb

def analyze(ticker: str) -> BaseAgentOutput:
    company_name = stocks.name(ticker)
    try:
        earnings_release_path = stocks.earnings_release_pdf_path(ticker)
        kb = get_earnings_kb(earnings_release_path, ticker)
    except Exception as e:
        print(f'Erro ao baixar ou processar o earnings release RAG: {e}')
        return BaseAgentOutput(content='Erro ao preaparar o relatório para leitura vetorial RAG', sentiment='NEUTRAL', confidence=0)

    system_message = f"""
    Você é um analista especializado em extrair e resumir informações relevantes de relatórios financeiros.
    Sua tarefa é analisar o arquivo do último earnings release da empresa {company_name} - {ticker} contido BEM AQUI NA SUA BASE DE CONHECIMENTO (ferramenta RAG).

    Pesquise usando o seu conhecimento contextual e crie um resumo estruturado destacando os pontos mais importantes mencionados no documento.

    ## OBJETIVO
    Fornecer um resumo claro e objetivo dos principais pontos abordados no earnings release, sem adicionar informações externas ou criar dados não presentes no documento original guardado na sua base de conhecimento.

    ## ESTRUTURA DO SEU RESUMO
    Organize sua resposta em formato markdown seguindo esta estrutura:

    ### 1. PRINCIPAIS DESTAQUES
    ### 2. MENSAGEM DA ADMINISTRAÇÃO (Opcional)
    ### 3. DESENVOLVIMENTOS ESTRATÉGICOS
    ### 4. PERSPECTIVAS FUTURAS
    ### 5. DESAFIOS E RISCOS
    ### 6. CONCLUSÃO E OPINIÃO

    ## DIRETRIZES IMPORTANTES
    - Limite-se EXCLUSIVAMENTE ao conteúdo presente no documento
    - NÃO crie, calcule ou infira dados financeiros não explicitamente mencionados
    - Use as próprias palavras e terminologia da empresa sempre que possível
    - Priorize informações qualitativas e estratégicas sobre números específicos
    - Use bullet points para facilitar a leitura rápida
    - Seu conteúdo deve ser conciso (máximo de 800 palavras).
    """

    today = datetime.date.today().isoformat()

    try:
        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            knowledge=kb,
            search_knowledge=True,
            retries=3,
        )
        response = agent.run(
            f'Data: {today}. Pesquise na sua base de conhecimento RAG sobre o earnings release da empresa {company_name} - {ticker} e analise segundo o formato instruído.'
        )
        return response.content
    except Exception as e:
        print(f'Erro ao analisar o earnings release via Agno: {e}')
        return BaseAgentOutput(content='Erro ao analisar o earnings release', sentiment='NEUTRAL', confidence=0)

