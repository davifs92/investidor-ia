from pathlib import Path
from decouple import config

PROJECT_DIR = Path(__file__).parent.parent

CACHE_DIR = PROJECT_DIR / 'cache'
CACHE_DIR.mkdir(exist_ok=True, parents=True)

DB_DIR = PROJECT_DIR / 'db'
DB_DIR.mkdir(exist_ok=True, parents=True)

# LLMs via .env
PROVIDER = config('LLM_PROVIDER', default='gemini').lower()

# Default models by provider if not explicitly configured
_DEFAULT_MODELS = {
    'gemini': 'gemini-2.0-flash',
    'claude': 'claude-3-5-sonnet-latest',
    'openai': 'gpt-4o',
    'groq': 'llama-3.3-70b-versatile',
}
MODEL = config('LLM_MODEL', default=_DEFAULT_MODELS.get(PROVIDER, ''))

# Resolve the active API key based on the selected provider
_API_KEY_MAP = {
    'gemini': config('GOOGLE_API_KEY', default=''),
    'claude': config('ANTHROPIC_API_KEY', default=''),
    'openai': config('OPENAI_API_KEY', default=''),
    'groq': config('GROQ_API_KEY', default=''),
}
API_KEY = _API_KEY_MAP.get(PROVIDER, '')

# investors
INVESTORS_BR = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'barsi': 'Luiz Barsi',
}

INVESTORS_US = {
    'buffett': 'Warren Buffett',
    'graham': 'Benjamin Graham',
    'lynch': 'Peter Lynch',
}

# Retrocompatibilidade
INVESTORS = INVESTORS_BR
