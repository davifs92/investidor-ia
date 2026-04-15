import streamlit as st
import os
from dotenv import set_key, load_dotenv

from src.settings import PROVIDER, MODEL, PROJECT_DIR

st.title('Configurações')
st.divider()

env_file = PROJECT_DIR / '.env'
if not env_file.exists():
    env_file.touch()

# Certifica de que as variaveis estão atualizadas do .env
load_dotenv(env_file, override=True)

st.markdown('### Provedor e Modelo')

provider_options = ['gemini', 'claude', 'openai', 'groq']
current_provider_lower = PROVIDER.lower().strip()
if current_provider_lower not in provider_options:
    current_provider_lower = 'gemini'

provider = st.selectbox('Provedor', provider_options, index=provider_options.index(current_provider_lower))
model = st.text_input('Modelo', value=MODEL)

st.divider()

st.markdown('### API Keys')

google_key = st.text_input('GOOGLE_API_KEY', type='password', value=os.environ.get('GOOGLE_API_KEY', ''))
anthropic_key = st.text_input('ANTHROPIC_API_KEY', type='password', value=os.environ.get('ANTHROPIC_API_KEY', ''))
openai_key = st.text_input('OPENAI_API_KEY', type='password', value=os.environ.get('OPENAI_API_KEY', ''))
groq_key = st.text_input('GROQ_API_KEY', type='password', value=os.environ.get('GROQ_API_KEY', ''))
alpha_vantage_key = st.text_input('ALPHAVANTAGE_API_KEY', type='password', value=os.environ.get('ALPHAVANTAGE_API_KEY', ''))

st.divider()

if st.button('Salvar Requer Reinício'):
    set_key(env_file, 'LLM_PROVIDER', provider)
    set_key(env_file, 'LLM_MODEL', model)

    if google_key:
        set_key(env_file, 'GOOGLE_API_KEY', google_key)
    if anthropic_key:
        set_key(env_file, 'ANTHROPIC_API_KEY', anthropic_key)
    if openai_key:
        set_key(env_file, 'OPENAI_API_KEY', openai_key)
    if groq_key:
        set_key(env_file, 'GROQ_API_KEY', groq_key)
    if alpha_vantage_key:
        set_key(env_file, 'ALPHAVANTAGE_API_KEY', alpha_vantage_key)

    st.success('Configurações salvas no arquivo .env! Reinicie o app para aplicar.')
