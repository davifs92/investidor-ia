import time
from typing import TypedDict

import requests
from bs4 import BeautifulSoup
from duckduckgo_search import DDGS
from agno.agent import Agent

from src.utils import get_model
from src.agents.base import BaseAgentOutput
from src.data import stocks


class News(TypedDict):
    title: str
    url: str
    body: str
    content: str


def _search_news_einvestidor(ticker: str, company_name: str) -> list[News]:
    results = DDGS().text(
        f'notícias sobre a empresa {company_name} (ticker {ticker}) site:einvestidor.estadao.com.br',
        max_results=5,
        region='br-pt',
        timelimit='3m',
    )

    news = []
    for result in results:
        url = result['href']
        if '/tag/' in url:
            continue
        r = requests.get(url)
        soup = BeautifulSoup(r.text, 'html.parser')
        soup_content = soup.find('div', class_='content-editor')
        content = soup_content.text if soup_content else 'Conteúdo não encontrado'
        news.append({'title': result['title'], 'url': url, 'body': result['body'], 'content': content})
        time.sleep(1)

    return news


def _search_news_international(ticker: str, company_name: str) -> list[News]:
    """Busca notícias para tickers internacionais (NYSE/NASDAQ) via DuckDuckGo em fontes globais."""
    results = DDGS().text(
        f'{company_name} ({ticker}) stock news site:reuters.com OR site:finance.yahoo.com OR site:bloomberg.com OR site:cnbc.com',
        max_results=5,
        timelimit='1m',
    )

    news = []
    for result in results:
        url = result.get('href', '')
        news.append({
            'title': result.get('title', ''),
            'url': url,
            'body': result.get('body', ''),
            'content': result.get('body', '')  # usa o snippet sem scraping adicional
        })

    return news


def analyze(ticker: str) -> BaseAgentOutput:
    company_name = stocks.name(ticker)
    is_br = ticker.upper().endswith('.SA')

    if is_br:
        news = _search_news_einvestidor(ticker, company_name)
        mercado_label = 'Brasil (B3)'
    else:
        news = _search_news_international(ticker, company_name)
        mercado_label = 'Internacional (NYSE/NASDAQ)'

    system_message = """
    Você é um analista especializado em pesquisar e analisar notícias de mercado financeiro.
    Sua tarefa é buscar e sintetizar as notícias mais relevantes sobre a empresa fornecida.

    ## OBJETIVOS DA ANÁLISE
    1. Identificar eventos significativos recentes que possam impactar a empresa
    2. Detectar mudanças estratégicas, aquisições, parcerias ou novos projetos
    3. Avaliar a percepção do mercado e da mídia sobre a empresa
    4. Monitorar riscos e oportunidades mencionados nas notícias
    5. Acompanhar declarações importantes da administração

    ## SUA ANÁLISE
    - Resuma cada notícia lida em poucas frases
    - Ao final, forneça uma conclusão objetiva em 3-5 frases sobre o sentimento geral e o impacto de curto/médio prazo.
    - Se não houver notícias coerentes na carga, retorne conteúdo vazio e sentimento NEUTRAL com confiança 0.

    ## DIRETRIZES
    - Mantenha objetividade na análise
    - Destaque fatos concretos
    """

    import datetime
    today = datetime.date.today().isoformat()
    
    user_prompt = f"""
    Avalie os dados de Notícias da empresa {company_name} (Ticker: {ticker}, Mercado: {mercado_label}):
    Data Ref: {today}
    
    NOTÍCIAS:
    {news}
    """

    try:
        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=3,
        )
        response = agent.run(user_prompt)
        return response.content
    except Exception as e:
        print(f'Erro ao gerar análise.: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise.', sentiment='NEUTRAL', confidence=0)
