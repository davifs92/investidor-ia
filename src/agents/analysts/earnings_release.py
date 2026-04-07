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

    prompt = f"""
    Você é um analista especializado em extrair e resumir informações relevantes de relatórios financeiros.
    Sua tarefa é analisar o arquivo do último earnings release da empresa {company_name} - {ticker} contido BEM AQUI NA SUA BASE DE CONHECIMENTO (ferramenta RAG).

    Pesquise usando o seu conhecimento contextual e crie um resumo estruturado destacando os pontos mais importantes mencionados no documento.

    ## OBJETIVO
    Fornecer um resumo claro e objetivo dos principais pontos abordados no earnings release, sem adicionar informações externas ou criar dados não presentes no documento original guardado na sua base de conhecimento.

    ## ESTRUTURA DO SEU RESUMO
    Organize sua resposta em formato markdown seguindo esta estrutura:

    ### 1. PRINCIPAIS DESTAQUES
    - Liste os 3-5 pontos mais importantes que a própria empresa destacou no relatório
    - Mantenha-se fiel ao que foi explicitamente mencionado no documento

    ### 2. MENSAGEM DA ADMINISTRAÇÃO
    - Resuma as principais declarações da liderança da empresa
    - Extraia citações relevantes sobre a visão da administração sobre os resultados
    - PS: essa seção é opcional, se não houver conteúdo para resumir, você pode simplesmente ignorar esta seção

    ### 3. DESENVOLVIMENTOS ESTRATÉGICOS
    - Iniciativas, parcerias ou mudanças estratégicas mencionadas
    - Novos produtos, serviços ou mercados destacados no relatório

    ### 4. PERSPECTIVAS FUTURAS
    - Resumo das expectativas e projeções mencionadas pela empresa
    - Planos futuros ou direcionamentos estratégicos comunicados

    ### 5. DESAFIOS E RISCOS
    - Obstáculos ou dificuldades explicitamente mencionados no relatório
    - Fatores de risco que a própria empresa destacou

    ### 6. CONCLUSÃO E OPINIÃO
    - Resuma as principais conclusões e opiniões sobre o relatório
    - Dê sua opinião sobre a empresa e seus resultados, escreva de forma simples e objetiva se o resultado foi positivo, negativo ou misto

    ## DIRETRIZES IMPORTANTES
    - Limite-se EXCLUSIVAMENTE ao conteúdo presente no documento
    - NÃO crie, calcule ou infira dados financeiros não explicitamente mencionados
    - Use as próprias palavras e terminologia da empresa sempre que possível
    - Priorize informações qualitativas e estratégicas sobre números específicos
    - Use bullet points para facilitar a leitura rápida

    ## FORMATO FINAL
    Seu conteúdo deve ser conciso (máximo de 800 palavras), focando apenas nos pontos mais relevantes mencionados no documento.
    (IMPORTANTE) Você deve estruturar a sua resposta em um JSON com a seguinte estrutura:
    {{
        "content": "Conteúdo markdown inteiro da sua análise",
        "sentiment": "Seu sentimento sobre a análise, você deve escolher entre 'BULLISH', 'BEARISH', 'NEUTRAL'",
        "confidence": "um valor numérico inteiro livre de decimal entre 0 e 100",
    }}
    """

    try:
        agent = Agent(
            system_message=prompt,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            knowledge=kb,
            search_knowledge=True,
            retries=3,
        )
        response = agent.run(
            f'Pesquise na sua base de conhecimento RAG sobre o earnings release da empresa {company_name} - {ticker} e analise segundo o formato instruído.'
        )
        return response.content
    except Exception as e:
        print(f'Erro ao analisar o earnings release via Agno: {e}')
        return BaseAgentOutput(content='Erro ao analisar o earnings release', sentiment='NEUTRAL', confidence=0)

