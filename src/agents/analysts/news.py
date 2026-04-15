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
    try:
        results = DDGS().text(
            f'notícias sobre a empresa {company_name} (ticker {ticker}) site:einvestidor.estadao.com.br',
            max_results=5,
            region='br-pt',
            timelimit='3m',
        )
        if not results:
            return []
    except Exception as e:
        print(f"Erro ao buscar notícias (BR): {e}")
        return []

    news = []
    for result in results:
        try:
            url = result['href']
            if '/tag/' in url:
                continue
            r = requests.get(url, timeout=5)
            soup = BeautifulSoup(r.text, 'html.parser')
            soup_content = soup.find('div', class_='content-editor')
            content = soup_content.text if soup_content else 'Conteúdo não encontrado'
            news.append({'title': result['title'], 'url': url, 'body': result['body'], 'content': content})
            time.sleep(1)
        except Exception:
            continue

    return news


def _search_news_international(ticker: str, company_name: str) -> list[News]:
    """Busca notícias para tickers internacionais (NYSE/NASDAQ) via DuckDuckGo em fontes globais."""
    try:
        results = DDGS().text(
            f'{company_name} ({ticker}) stock news site:reuters.com OR site:finance.yahoo.com OR site:bloomberg.com OR site:cnbc.com',
            max_results=5,
            timelimit='1m',
        )
        if not results:
            return []
    except Exception as e:
        print(f"Erro ao buscar notícias (US): {e}")
        return []

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


def analyze(ticker: str, market: str | None = None) -> BaseAgentOutput:
    company_name = stocks.name(ticker, market=market)
    
    # Se market for fornecido, usa ele. Caso contrário, fallback para o sufixo.
    if market:
        is_br = (market == 'BR')
    else:
        is_br = ticker.upper().endswith('.SA')

    # --- NOVO FLUXO DE NOTÍCIAS ---
    # 1. Tenta buscar notícias via Provider (Yahoo Finance - Estável e Grátis)
    try:
        provider_news = stocks.news(ticker, market=market)
    except Exception:
        provider_news = []

    # 2. Tenta buscar notícias via DuckDuckGo (Scraping - Fallback Secundário)
    if is_br:
        mercado_label = 'Brasil (B3)'
        try:
            ddg_news = _search_news_einvestidor(ticker, company_name)
        except Exception:
            ddg_news = []
    else:
        mercado_label = 'Internacional (NYSE/NASDAQ)'
        try:
            ddg_news = _search_news_international(ticker, company_name)
        except Exception:
            ddg_news = []

    # Consolida as notícias (prioridade para Provider)
    all_news = provider_news + ddg_news
    # ------------------------------

    system_message = """
    Você é um analista especializado em pesquisar e analisar notícias de mercado financeiro.
    Sua tarefa é pesquisar e sintetizar as notícias mais relevantes sobre a empresa fornecida, baseando-se nos dados brutos carregados.

    ## OBJETIVOS DA ANÁLISE
    1. Identificar eventos significativos recentes que possam impactar a empresa
    2. Detectar mudanças estratégicas, aquisições, parcerias ou novos projetos
    3. Avaliar a percepção do mercado e da mídia sobre a empresa
    4. Monitorar riscos e oportunidades mencionados nas notícias
    5. Acompanhar declarações importantes da administração

    ## SUA ANÁLISE
    - Resuma cada notícia lida em poucas frases
    - Ao final, forneça uma conclusão objetiva em 3-5 frases sobre o sentimento geral e o impacto de curto/médio prazo.
    - Se não houver notícias coerentes na carga (lista vazia), retorne conteúdo vazio e sentimento NEUTRAL com confiança 0.

    ## DIRETRIZES
    - Mantenha objetividade na análise
    - Destaque fatos concretos
    """

    import datetime
    today = datetime.date.today().isoformat()
    
    user_prompt = f"""
    Avalie os dados de Notícias da empresa {company_name} (Ticker: {ticker}, Mercado: {mercado_label}):
    Data Ref: {today}
    
    NOTÍCIAS CARREGADAS:
    {all_news}
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
        print(f'Erro ao gerar análise de notícias: {e}')
        return BaseAgentOutput(content='Erro ao gerar análise de notícias.', sentiment='NEUTRAL', confidence=0)
