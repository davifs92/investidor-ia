import streamlit as st

from src.chat.agent import get_chat_agent
from src.settings import API_KEY, MODEL, PROVIDER, reload_llm_config

reload_llm_config()

if not PROVIDER or not MODEL or not API_KEY:
    st.error('Por favor, configure o modelo e a chave de API no menu de configurações')
    st.stop()


def _apply_chat_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

            :root {
                --surface: #fcf9f8;
                --surface-low: #f6f3f2;
                --surface-lowest: #ffffff;
                --surface-highest: #e5e2e1;
                --primary: #004f45;
                --primary-container: #00695c;
                --on-surface: #1c1b1b;
                --on-surface-variant: #3e4946;
                --outline-variant: #bec9c5;
                --tertiary: #703321;
            }

            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stHeader"] {
                background: var(--surface);
            }

            section.main > div {
                max-width: 1180px;
                padding-top: 1rem;
                padding-bottom: 9rem;
            }

            [data-testid="stSidebar"] {
                background: var(--surface) !important;
                border: 0 !important;
            }

            [data-testid="stSidebarContent"] {
                background: var(--surface) !important;
            }

            [data-testid="stSidebarNav"] {
                font-family: "Plus Jakarta Sans", sans-serif;
                padding-top: 0.6rem;
            }

            [data-testid="stSidebarNav"]::before {
                content: "The Intelligent Investor";
                display: block;
                font-size: 1.42rem;
                letter-spacing: -0.02em;
                line-height: 1.1;
                font-weight: 800;
                color: var(--primary);
                margin: 0.4rem 0 0.25rem 0.85rem;
            }

            [data-testid="stSidebarNav"]::after {
                content: "Silent Analyst AI";
                display: block;
                font-size: 0.72rem;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: color-mix(in srgb, var(--on-surface-variant) 70%, transparent);
                margin: 0 0 1rem 0.9rem;
                font-weight: 700;
            }

            [data-testid="stSidebarNav"] ul {
                gap: 0.42rem;
            }

            [data-testid="stSidebarNav"] a {
                border-radius: 999px 0 0 999px;
                margin-left: 0.6rem;
                padding: 0.58rem 0.9rem;
                color: color-mix(in srgb, var(--on-surface) 65%, transparent);
                font-weight: 600;
                transition: all 180ms ease;
            }

            [data-testid="stSidebarNav"] a:hover {
                background: #f2eeed;
                color: var(--primary);
            }

            [data-testid="stSidebarNav"] a[aria-current="page"] {
                background: var(--surface-lowest);
                color: var(--primary);
                box-shadow: 0 24px 32px rgba(28, 27, 27, 0.04);
                font-weight: 700;
            }

            .topbar {
                margin-top: 0.3rem;
                margin-bottom: 0.95rem;
                min-height: 56px;
                border-radius: 14px;
                background: color-mix(in srgb, var(--surface) 80%, white);
                backdrop-filter: blur(10px);
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 0 1rem;
            }

            .title-wrap {
                display: flex;
                align-items: center;
                gap: 0.95rem;
            }

            .terminal-title {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 1.58rem;
                letter-spacing: -0.03em;
                color: var(--primary);
                font-weight: 800;
            }

            .online-dot {
                width: 8px;
                height: 8px;
                border-radius: 999px;
                background: var(--primary);
                margin-top: 1px;
            }

            .online-label {
                font-size: 0.66rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-weight: 800;
                color: var(--on-surface-variant);
            }

            .top-icons {
                color: color-mix(in srgb, var(--on-surface) 64%, transparent);
                letter-spacing: 0.2em;
                font-size: 1.2rem;
                user-select: none;
            }

            .context-grid {
                display: grid;
                grid-template-columns: 2.2fr 1fr;
                gap: 0.8rem;
                margin-bottom: 1rem;
            }

            .context-main {
                background: var(--surface-low);
                border-radius: 12px;
                padding: 0.9rem;
            }

            .context-health {
                border-radius: 12px;
                color: white;
                padding: 0.9rem;
                background: linear-gradient(110deg, var(--primary) 0%, var(--primary-container) 100%);
            }

            .context-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 0.8rem;
                flex-wrap: wrap;
            }

            .context-main div[data-testid="stRadio"] > div {
                gap: 0.35rem;
            }

            .context-main div[data-testid="stRadio"] label {
                border-radius: 999px;
                background: transparent;
                border: 1px solid transparent;
                min-height: 2.05rem;
                padding: 0.28rem 0.85rem;
                transition: all 180ms ease;
            }

            .context-main div[data-testid="stRadio"] label:has(input:checked) {
                background: var(--surface-lowest);
                color: var(--primary);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
                font-weight: 700;
            }

            .section-label {
                font-size: 0.65rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                font-weight: 800;
                color: var(--on-surface-variant);
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .chip-row {
                display: flex;
                gap: 0.35rem;
                flex-wrap: wrap;
            }

            .chip {
                border-radius: 999px;
                padding: 0.43rem 0.9rem;
                font-size: 0.88rem;
                font-weight: 600;
                color: var(--on-surface-variant);
                background: transparent;
            }

            .chip.active {
                background: var(--surface-lowest);
                color: var(--primary);
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
                font-weight: 700;
            }

            .health-kicker {
                margin: 0;
                font-size: 0.59rem;
                text-transform: uppercase;
                letter-spacing: 0.16em;
                opacity: 0.84;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .health-value {
                margin: 0.3rem 0 0;
                font-size: 1.75rem;
                letter-spacing: -0.03em;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .feed-shell {
                padding-bottom: 0.3rem;
            }

            .msg-row {
                display: flex;
                gap: 0.82rem;
                margin-bottom: 1.05rem;
                align-items: flex-start;
            }

            .msg-row.user {
                justify-content: flex-end;
            }

            .msg-avatar {
                width: 34px;
                height: 34px;
                border-radius: 10px;
                background: var(--primary-container);
                color: white;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 1rem;
                flex: 0 0 auto;
                margin-top: 1px;
            }

            .msg-bubble {
                border-radius: 14px;
                padding: 0.85rem 1rem;
                max-width: min(79%, 900px);
                line-height: 1.62;
                color: var(--on-surface);
            }

            .msg-bubble.assistant {
                background: var(--surface-low);
                border-top-left-radius: 4px;
            }

            .msg-bubble.user {
                background: color-mix(in srgb, var(--surface-highest) 58%, white);
                border-top-right-radius: 4px;
            }

            .msg-bubble strong {
                color: var(--primary);
                font-weight: 800;
            }

            .chat-input-wrap {
                position: fixed;
                bottom: 0;
                left: min(20rem, calc(100vw - 100vw + 20rem));
                right: 0;
                background: linear-gradient(180deg, rgba(252, 249, 248, 0) 0%, rgba(252, 249, 248, 0.95) 34%, #fcf9f8 68%);
                padding: 0.9rem 1.2rem 1rem;
                z-index: 30;
            }

            .chat-input-note {
                margin: 0.35rem 0 0;
                text-align: center;
                font-size: 0.58rem;
                letter-spacing: 0.14em;
                text-transform: uppercase;
                color: color-mix(in srgb, var(--on-surface-variant) 45%, transparent);
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            div[data-testid="stChatInput"] {
                background: var(--surface-lowest);
                border-radius: 12px;
                box-shadow: 0 8px 32px rgba(0, 0, 0, 0.08);
                border: 1px solid color-mix(in srgb, var(--outline-variant) 20%, transparent);
                padding-left: 0.15rem;
            }

            div[data-testid="stChatInput"] textarea {
                font-family: "Manrope", sans-serif !important;
            }

            div[data-testid="stChatInput"] button[kind="secondary"] {
                background: linear-gradient(96deg, var(--primary) 0%, var(--primary-container) 100%) !important;
                border: 0 !important;
                color: white !important;
                border-radius: 10px !important;
                min-width: 2.6rem !important;
                min-height: 2.45rem !important;
            }

            div[data-testid="stButton"] button {
                border: 0 !important;
                border-radius: 10px !important;
                background: var(--surface-low) !important;
                color: var(--on-surface) !important;
                min-height: 2.45rem !important;
                font-family: "Plus Jakarta Sans", sans-serif !important;
                font-weight: 700 !important;
            }

            @media (max-width: 1080px) {
                .context-grid {
                    grid-template-columns: 1fr;
                }

                .msg-bubble {
                    max-width: 92%;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_topbar():
    st.markdown(
        """
        <div class="topbar">
            <div class="title-wrap">
                <h2 class="terminal-title">Analyst Terminal</h2>
                <span class="online-dot"></span>
                <span class="online-label">AI Online</span>
            </div>
            <div class="top-icons">◔ ◉</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_context_strip(investor: str, market_code: str):
    col_main, col_health = st.columns([2.2, 1], gap='small')

    with col_main:
        st.markdown('<div class="context-main">', unsafe_allow_html=True)
        st.markdown('<p class="section-label">Persona</p>', unsafe_allow_html=True)
        persona_name = st.radio(
            'Persona',
            ['Warren Buffett', 'Benjamin Graham', 'Luiz Barsi'],
            horizontal=True,
            index=['buffett', 'graham', 'barsi'].index(investor),
            label_visibility='collapsed',
            key='persona_switch',
        )
        st.markdown('<p class="section-label" style="margin-top:0.35rem;">Market</p>', unsafe_allow_html=True)
        market_name = st.radio(
            'Market',
            ['Brasil', 'EUA'],
            horizontal=True,
            index=0 if market_code == 'BR' else 1,
            label_visibility='collapsed',
            key='market_switch',
        )
        st.markdown('</div>', unsafe_allow_html=True)

    with col_health:
        st.markdown(
            """
            <div class="context-health">
                <p class="health-kicker">Portfolio Health</p>
                <p class="health-value">Excellent (+12.4%)</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    persona_to_id = {
        'Warren Buffett': 'buffett',
        'Benjamin Graham': 'graham',
        'Luiz Barsi': 'barsi',
    }
    investor_id = persona_to_id[persona_name]
    selected_market_code = 'BR' if market_name == 'Brasil' else 'US'
    st.session_state.persona = persona_name
    st.session_state.market_origin = market_name
    return investor_id, selected_market_code


def _render_messages():
    st.markdown('<div class="feed-shell">', unsafe_allow_html=True)
    for message in st.session_state.messages:
        content = message['content'].replace('$', r'\$')
        if message['role'] == 'assistant':
            st.markdown(
                f"""
                <div class="msg-row">
                    <div class="msg-avatar">✦</div>
                    <div class="msg-bubble assistant">{content}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="msg-row user">
                    <div class="msg-bubble user">{content}</div>
                    <div class="msg-avatar" style="background:#1c1b1b;">◉</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.markdown('</div>', unsafe_allow_html=True)


_apply_chat_styles()

if st.button('Novo chat'):
    st.session_state.messages = []

persona_to_id = {
    'Warren Buffett': 'buffett',
    'Benjamin Graham': 'graham',
    'Luiz Barsi': 'barsi',
}

if 'persona' not in st.session_state:
    st.session_state.persona = 'Warren Buffett'
if 'market_origin' not in st.session_state:
    st.session_state.market_origin = 'Brasil'
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {
            'role': 'assistant',
            'content': (
                'Greetings, Ricardo. Estou emulando a filosofia de **Warren Buffett** focando no '
                '**mercado brasileiro**. Quer analisar um ativo específico agora ou revisar a margem '
                'de segurança da sua carteira atual?'
            ),
        }
    ]

_render_topbar()
investor_id = persona_to_id[st.session_state.persona]
market_code = 'BR' if st.session_state.market_origin == 'Brasil' else 'US'
investor_id, market_code = _render_context_strip(investor=investor_id, market_code=market_code)
agent = get_chat_agent(investor=investor_id, market=market_code)
_render_messages()

st.markdown('<div class="chat-input-wrap">', unsafe_allow_html=True)
prompt = st.chat_input('Pergunte sobre qualquer ação, FII ou tese de investimento...')
st.markdown(
    '<p class="chat-input-note">AI can provide inaccurate financial data. Always consult a certified professional.</p>',
    unsafe_allow_html=True,
)
st.markdown('</div>', unsafe_allow_html=True)

if prompt:
    st.session_state.messages.append({'role': 'user', 'content': prompt})
    response = agent.run(prompt, messages=st.session_state.messages, markdown=True, stream=True)
    full_response = ''
    with st.spinner('Analisando contexto e gerando resposta...'):
        for chunk in response:
            full_response += chunk.content or ''
    st.session_state.messages.append({'role': 'assistant', 'content': full_response})
    st.rerun()
