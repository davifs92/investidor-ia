import fitz

from agno.models.base import Model
from agno.models.anthropic import Claude
from agno.models.google import Gemini
from agno.models.openai import OpenAIChat
from agno.models.groq import Groq


import os
from src.settings import PROVIDER, MODEL, API_KEY


def sync_envs():
    """Injeta as chaves do .env no os.environ para satisfazer dependências do Agno/OpenAI/Google."""
    if API_KEY:
        if PROVIDER == 'gemini':
            os.environ['GOOGLE_API_KEY'] = API_KEY
        elif PROVIDER == 'openai':
            os.environ['OPENAI_API_KEY'] = API_KEY
        elif PROVIDER == 'claude':
            os.environ['ANTHROPIC_API_KEY'] = API_KEY
        elif PROVIDER == 'groq':
            os.environ['GROQ_API_KEY'] = API_KEY


def pdf_to_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = '\n'.join([page.get_text('text') for page in doc])
    return text


def pdf_bytes_to_text(pdf_bytes: bytes) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype='pdf')
    text = '\n'.join([page.get_text('text') for page in doc])
    return text


def calc_cagr(data: dict, name: str, length: int = 5) -> float:
    """ps: data precisa estar em ordem decrescente, do mais novo para o mais antigo"""
    values = [d[name] for d in data if name in d and d[name]][:length]
    if len(values) < 2:
        return 0.0
    cagr = (values[0] / values[-1]) ** (1 / (len(values) - 1)) - 1
    return cagr


def get_model(temperature: float = 0.3) -> Model:
    """
    Retorna o modelo LLM configurado via .env (LLM_PROVIDER).

    Providers suportados (via variável LLM_PROVIDER):
        - gemini   → Google Gemini (ex: gemini-2.0-flash)
        - claude   → Claude Anthropic (ex: claude-3-5-sonnet-latest)
        - openai   → GPT (ex: gpt-4o)
        - groq     → Groq (ex: llama-3.3-70b-versatile)
    """
    sync_envs()
    provider = PROVIDER.lower().strip()
    
    if provider == 'gemini':
        return Gemini(id=MODEL, temperature=temperature, api_key=API_KEY)
    elif provider == 'claude':
        return Claude(id=MODEL, temperature=temperature, api_key=API_KEY)
    elif provider == 'openai':
        # Modelos da série 'o1' e modelos 'mini' podem ter restrições de temperatura != 1
        if 'o1' in MODEL or 'mini' in MODEL:
            return OpenAIChat(id=MODEL, api_key=API_KEY)
        return OpenAIChat(id=MODEL, temperature=temperature, api_key=API_KEY)
    elif provider == 'groq':
        return Groq(id=MODEL, temperature=temperature, api_key=API_KEY)
    else:
        raise ValueError(f'Provider "{PROVIDER}" não suportado. Use um dos configurados em .env: gemini, claude, openai ou groq.')
