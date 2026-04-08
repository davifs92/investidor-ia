import urllib.request
import json
import os
from agno.agent import Agent
from src.agents.base import BaseAgentOutput
from src.utils import get_model


def get_selic() -> str:
    """Retorna a taxa Selic atual via API do Banco Central do Brasil."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.11/dados/ultimos/1?formato=json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data[0]['valor']
    except Exception:
        return "10.50 (Fallback Mode)"


def get_ipca() -> str:
    """Retorna o IPCA (inflação) acumulado 12 meses via API do Banco Central do Brasil."""
    try:
        url = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados/ultimos/1?formato=json"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data[0]['valor']
    except Exception:
        return "N/A (Fallback Mode)"


def get_fed_funds() -> str:
    """Retorna o Fed Funds Rate atual via FRED API (Federal Reserve de St. Louis)."""
    fred_api_key = os.environ.get('FRED_API_KEY', '')
    if not fred_api_key:
        return "5.25 (FRED_API_KEY não configurada no .env)"
    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id=FEDFUNDS&api_key={fred_api_key}&sort_order=desc&limit=1&file_type=json"
        )
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data['observations'][0]['value']
    except Exception:
        return "5.25 (Fallback Mode)"

def analyze(ticker: str) -> BaseAgentOutput:
    is_br = ticker.upper().endswith(".SA")

    if is_br:
        taxa = get_selic()
        ipca = get_ipca()
        mercado = "Brasil (B3)"
        contexto_macro = (
            f"A taxa básica de juros (Selic) está em {taxa}% a.a. "
            f"O IPCA (inflação acumulada 12m) está em {ipca}%."
        )
    else:
        taxa = get_fed_funds()
        mercado = "Estados Unidos (NYSE/NASDAQ)"
        contexto_macro = f"O Fed Funds Rate atual está em {taxa}% a.a."

    system_message = f"""
    Você é um experiente Analista Macroeconômico focado em Custo de Oportunidade.
    Sua tarefa é avaliar como o atual cenário de juros e o ambiente macroeconômico regional impactam a atratividade do ativo {ticker} frente a outros investimentos de taxa básica ou renda fixa.
    Seja simples (máximo de 150 a 200 palavras). Foque na correlação Selic/FedRate vs Risco na bolsa.
    """

    import datetime
    today = datetime.date.today().isoformat()

    user_prompt = f"""
    Avalie o ativo: {ticker} (Mercado: {mercado})
    Contexto Macroeconômico: {contexto_macro}

    Emita sua visão macro focada no custo de oportunidade hoje.
    """

    try:
        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.3),
            response_model=BaseAgentOutput,
            retries=2
        )
        response = agent.run(f"Data Base: {today}\n\n{user_prompt}")
        return response.content
    except Exception as e:
        return BaseAgentOutput(content=f"Erro Macro: {e}", sentiment="NEUTRAL", confidence=0)
