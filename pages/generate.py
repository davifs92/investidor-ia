import asyncio
import datetime
import json
from pathlib import Path

import nest_asyncio
import streamlit as st

from pages._utils import Report, display_report
from src.agents.analysts import (
    earnings_release,
    financial,
    macro,
    news,
    technical,
    valuation,
)
from src.agents.investors import (
    barsi,
    buffett,
    graham,
    lynch,
)
from src.data import stocks
from src.settings import API_KEY, DB_DIR, INVESTORS_BR, INVESTORS_US, MODEL, PROVIDER

if not PROVIDER or not MODEL or not API_KEY:
    st.error('Por favor, configure o modelo e a chave de API no menu de configurações')
    st.stop()


def _generate_investor_report(
    ticker: str,
    investor_name: str,
    active_investors: dict,
    market: str,
) -> Report | None:
    if investor_name not in active_investors.keys():
        st.error(f'Investidor {investor_name} não encontrado')
        return

    ticker = ticker.upper()

    # verifica se o ticker existe no provider selecionado
    try:
        stocks.details(ticker, market=market)
    except ValueError:
        st.error(f'Ticker {ticker} não encontrado no mercado selecionado ({market})')
        return

    # ai analysts - execução paralela com asyncio
    # nest_asyncio permite asyncio.run() dentro do event loop do Streamlit
    nest_asyncio.apply()

    async def _run_analysts(market: str) -> tuple:
        return await asyncio.gather(
            asyncio.to_thread(earnings_release.analyze, ticker, market=market),
            asyncio.to_thread(financial.analyze, ticker, market=market),
            asyncio.to_thread(valuation.analyze, ticker, market=market),
            asyncio.to_thread(news.analyze, ticker, market=market),
            asyncio.to_thread(macro.analyze, ticker, market=market),
            asyncio.to_thread(technical.analyze, ticker, market=market),
        )

    st.markdown('#### Analisando empresa em paralelo')
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)

    with col1:
        ph_earnings = st.empty()
        ph_earnings.info('⏳ Earnings...')
    with col2:
        ph_financial = st.empty()
        ph_financial.info('⏳ Finanças...')
    with col3:
        ph_valuation = st.empty()
        ph_valuation.info('⏳ Valuation...')
    with col4:
        ph_news = st.empty()
        ph_news.info('⏳ Notícias...')
    with col5:
        ph_macro = st.empty()
        ph_macro.info('⏳ Macro...')
    with col6:
        ph_tech = st.empty()
        ph_tech.info('⏳ MCP Técnico...')

    (
        earnings_release_analysis,
        financial_analysis,
        valuation_analysis,
        news_analysis,
        macro_analysis,
        technical_analysis,
    ) = asyncio.run(_run_analysts(market=market))

    ph_earnings.success('✅ Earnings')
    ph_financial.success('✅ Finanças')
    ph_valuation.success('✅ Valuation')
    ph_news.success('✅ Notícias')
    ph_macro.success('✅ Macro')
    ph_tech.success('✅ MCP Técnico')

    # final investor analysis
    with st.spinner('Gerando relatório final da Persona...'):
        if investor_name == 'buffett':
            investor_analysis = buffett.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
                macro_analysis=macro_analysis,
                technical_analysis=technical_analysis,
                market=market,
            )

        elif investor_name == 'graham':
            investor_analysis = graham.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
                macro_analysis=macro_analysis,
                technical_analysis=technical_analysis,
                market=market,
            )

        elif investor_name == 'barsi':
            investor_analysis = barsi.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
                macro_analysis=macro_analysis,
                technical_analysis=technical_analysis,
                market=market,
            )

        elif investor_name == 'lynch':
            investor_analysis = lynch.analyze(
                ticker=ticker,
                earnings_release_analysis=earnings_release_analysis,
                financial_analysis=financial_analysis,
                valuation_analysis=valuation_analysis,
                news_analysis=news_analysis,
                macro_analysis=macro_analysis,
                technical_analysis=technical_analysis,
                market=market,
            )

        else:
            raise ValueError(f'Investor {investor_name} not found')

    report_data = {
        'analysts': {
            'earnings_release': earnings_release_analysis.model_dump(),
            'financial': financial_analysis.model_dump(),
            'valuation': valuation_analysis.model_dump(),
            'news': news_analysis.model_dump(),
            'macro': macro_analysis.model_dump(),
            'technical': technical_analysis.model_dump(),
        },
        'investor': investor_analysis.model_dump(),
    }
    return Report(
        ticker=ticker,
        investor_name=investor_name,
        generated_at=datetime.datetime.now(),
        data=report_data,
    )


def _load_reports() -> list[Report]:
    reports_file = Path('db/reports.json')
    if reports_file.exists():
        with open(reports_file, 'r') as f:
            content = f.read()
            reports = json.loads(content) if content else []
            if reports:
                return reports
    return []


def _save_report(report: Report):
    reports_file = DB_DIR / 'reports.json'

    report_dict = json.loads(report.model_dump_json())

    reports = _load_reports()
    reports.append(report_dict)

    with open(reports_file, 'w') as f:
        json.dump(reports, f, indent=4)


def _apply_generate_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

            :root {
                --surface: #fcf9f8;
                --surface-low: #f6f3f2;
                --surface-lowest: #ffffff;
                --primary: #004f45;
                --primary-container: #00695c;
                --on-surface: #1c1b1b;
                --on-surface-variant: #3e4946;
                --tertiary: #703321;
                --error: #ba1a1a;
            }

            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stHeader"] {
                background: var(--surface);
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

            section.main > div {
                max-width: 1150px;
                padding-top: 1.25rem;
                padding-bottom: 2.5rem;
            }

            .hero-kicker {
                font-family: "Plus Jakarta Sans", sans-serif;
                letter-spacing: 0.18em;
                text-transform: uppercase;
                font-size: 0.72rem;
                font-weight: 800;
                color: var(--primary);
            }

            .hero-title {
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: clamp(2rem, 3.8vw, 3.4rem);
                line-height: 1.06;
                letter-spacing: -0.03em;
                color: var(--on-surface);
                max-width: 760px;
                margin-top: 0.4rem;
            }

            .hero-title .highlight {
                color: transparent;
                background: linear-gradient(95deg, var(--primary) 0%, var(--primary-container) 100%);
                -webkit-background-clip: text;
                background-clip: text;
            }

            .hero-subtitle {
                font-family: "Manrope", sans-serif;
                color: var(--on-surface-variant);
                max-width: 700px;
                font-size: 1.06rem;
                line-height: 1.65;
                margin-top: 0.8rem;
                margin-bottom: 1.6rem;
            }

            .form-shell {
                background: var(--surface-lowest);
                border-radius: 14px;
                padding: 1.3rem;
                box-shadow: 0 24px 32px rgba(28, 27, 27, 0.04);
            }

            @media (min-width: 1200px) {
                .form-shell {
                    padding: 1.9rem;
                }
            }

            .field-label {
                margin: 0.3rem 0 0.55rem 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-weight: 800;
                font-size: 0.78rem;
                letter-spacing: 0.06em;
                text-transform: uppercase;
                color: var(--on-surface);
            }

            .field-label.mt {
                margin-top: 1.45rem;
            }

            .field-help {
                margin-top: -0.35rem;
                color: color-mix(in srgb, var(--on-surface-variant) 72%, transparent);
                font-size: 0.73rem;
                line-height: 1.4;
            }

            div[data-testid="stTextInput"] input {
                border: 0 !important;
                background: var(--surface-low) !important;
                border-radius: 10px !important;
                min-height: 3.1rem !important;
                font-weight: 600 !important;
                color: var(--on-surface) !important;
                box-shadow: none !important;
            }

            div[data-testid="stTextInput"] input:focus {
                background: var(--surface-lowest) !important;
                box-shadow: inset 0 -2px 0 var(--primary) !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                border: 0 !important;
                background: var(--surface-low) !important;
                border-radius: 10px !important;
                min-height: 3.05rem !important;
            }

            div[data-testid="stRadio"] > div {
                gap: 0.72rem;
            }

            div[data-testid="stRadio"] label {
                background: var(--surface-low);
                border-radius: 12px;
                border: 2px solid transparent;
                min-height: 4.2rem;
                padding: 0.65rem 0.9rem;
                transition: all 200ms ease;
            }

            div[data-testid="stRadio"] label:has(input:checked) {
                border-color: var(--primary);
                background: var(--surface-lowest);
            }

            div[data-testid="stFormSubmitButton"] button,
            .stDownloadButton > button {
                border: 0 !important;
                border-radius: 12px !important;
                min-height: 3.2rem !important;
                font-family: "Plus Jakarta Sans", sans-serif !important;
                font-weight: 700 !important;
                letter-spacing: -0.01em;
            }

            div[data-testid="stFormSubmitButton"] button {
                background: linear-gradient(96deg, var(--primary) 0%, var(--primary-container) 100%) !important;
                color: white !important;
            }

            .side-card {
                border-radius: 12px;
                background: color-mix(in srgb, var(--primary) 7%, var(--surface-lowest));
                padding: 1.1rem 1.05rem;
            }

            .side-card h4 {
                margin: 0.65rem 0 0.35rem;
                font-family: "Plus Jakarta Sans", sans-serif;
                color: var(--primary);
                font-size: 1rem;
                letter-spacing: -0.01em;
            }

            .side-card p {
                margin: 0;
                color: var(--on-surface-variant);
                font-size: 0.86rem;
                line-height: 1.5;
            }

            .orbit-icon {
                width: 36px;
                height: 36px;
                border-radius: 999px;
                background: color-mix(in srgb, var(--primary) 14%, white);
                color: var(--primary);
                display: flex;
                align-items: center;
                justify-content: center;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .feature-card {
                position: relative;
                overflow: hidden;
                min-height: 210px;
                border-radius: 12px;
                padding: 1rem;
                display: flex;
                align-items: flex-end;
                color: white;
                margin-top: 0.9rem;
                background:
                    linear-gradient(180deg, rgba(0, 0, 0, 0.05) 20%, rgba(0, 0, 0, 0.78) 100%),
                    url('https://images.unsplash.com/photo-1642052502626-7ce4f8f80bb9?auto=format&fit=crop&w=900&q=80')
                    center / cover;
            }

            .feature-tag {
                display: inline-block;
                font-size: 0.6rem;
                letter-spacing: 0.06em;
                padding: 0.17rem 0.52rem;
                background: var(--primary);
                border-radius: 999px;
                text-transform: uppercase;
                font-weight: 800;
                margin-bottom: 0.35rem;
            }

            .feature-title {
                margin: 0;
                font-size: 1.42rem;
                line-height: 1.15;
                letter-spacing: -0.02em;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .legal-card {
                margin-top: 0.9rem;
                border-radius: 12px;
                background: var(--surface-low);
                padding: 0.95rem;
            }

            .legal-title {
                margin: 0;
                color: var(--tertiary);
                text-transform: uppercase;
                font-size: 0.65rem;
                font-weight: 800;
                letter-spacing: 0.07em;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .legal-text {
                margin: 0.42rem 0 0;
                color: var(--on-surface-variant);
                font-size: 0.79rem;
                line-height: 1.45;
            }

            .trend-title {
                margin: 2.25rem 0 0.75rem;
                font-family: "Plus Jakarta Sans", sans-serif;
                letter-spacing: -0.02em;
            }

            .trend-grid {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.8rem;
            }

            .trend-card {
                border-radius: 12px;
                background: var(--surface-low);
                padding: 0.95rem;
            }

            .trend-row {
                display: flex;
                justify-content: space-between;
                align-items: center;
                font-size: 0.76rem;
            }

            .trend-label {
                color: var(--on-surface-variant);
                font-weight: 700;
                text-transform: uppercase;
            }

            .trend-up {
                color: var(--primary);
                font-weight: 700;
            }

            .trend-down {
                color: var(--error);
                font-weight: 700;
            }

            .trend-value {
                margin: 0.45rem 0 0;
                color: var(--on-surface);
                font-weight: 800;
                font-size: 1.75rem;
                line-height: 1;
                font-family: "Plus Jakarta Sans", sans-serif;
                letter-spacing: -0.02em;
            }

            .result-shell {
                margin-top: 1.2rem;
                border-radius: 12px;
                padding: 1rem;
                background: var(--surface-lowest);
            }

            @media (max-width: 900px) {
                .trend-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_hero():
    st.markdown(
        """
        <p class="hero-kicker">Processamento Assistido por IA</p>
        <h1 class="hero-title">Transforme dados brutos em <span class="highlight">decisões inteligentes.</span></h1>
        <p class="hero-subtitle">
            Nossa IA processa milhares de pontos de dados para entregar uma visão analítica fria e calculada
            sobre qualquer ativo do mercado global.
        </p>
        """,
        unsafe_allow_html=True,
    )


def _render_side_panel():
    st.markdown(
        """
        <div class="side-card">
            <div class="orbit-icon">✦</div>
            <h4>Análise 360°</h4>
            <p>Nosso relatório cruza dados de balanços trimestrais, sentimento de mercado e projeções macroeconômicas em tempo real.</p>
        </div>
        <div class="feature-card">
            <div>
                <span class="feature-tag">Novidade</span>
                <p class="feature-title">Previsão de Volatilidade por Deep Learning</p>
            </div>
        </div>
        <div class="legal-card">
            <p class="legal-title">Aviso Legal</p>
            <p class="legal-text">
                Relatórios gerados por IA são ferramentas auxiliares. Não constituem recomendação direta de compra ou venda.
                Invista com cautela.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_trends():
    st.markdown(
        """
        <h3 class="trend-title">Tendências do Dia</h3>
        <div class="trend-grid">
            <div class="trend-card">
                <div class="trend-row"><span class="trend-label">IBOVESPA</span><span class="trend-down">-0,42%</span></div>
                <p class="trend-value">127.450</p>
            </div>
            <div class="trend-card">
                <div class="trend-row"><span class="trend-label">PETR4</span><span class="trend-up">+1,25%</span></div>
                <p class="trend-value">R$ 38,42</p>
            </div>
            <div class="trend-card">
                <div class="trend-row"><span class="trend-label">S&P 500</span><span class="trend-up">+0,15%</span></div>
                <p class="trend-value">5.123,4</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


_apply_generate_styles()
_render_hero()

if 'last_generated_report' not in st.session_state:
    st.session_state['last_generated_report'] = None
if 'generate_market' not in st.session_state:
    st.session_state['generate_market'] = 'Brasil (B3)'
if 'generate_investor' not in st.session_state:
    st.session_state['generate_investor'] = list(INVESTORS_BR.values())[0]

main_col, side_col = st.columns([1.85, 1], gap='large')

with main_col:
    st.markdown('<div class="form-shell">', unsafe_allow_html=True)
    with st.form('generate_report_form'):
        st.markdown('<p class="field-label">Símbolo do Ativo (Ticker)</p>', unsafe_allow_html=True)
        ticker = st.text_input(
            'Ticker',
            placeholder='Ex: PETR4.SA ou AAPL',
            label_visibility='collapsed',
        )
        st.markdown(
            '<p class="field-help">Insira o código oficial da B3 ou Nasdaq/NYSE.</p>',
            unsafe_allow_html=True,
        )

        st.markdown('<p class="field-label mt">Região do Mercado</p>', unsafe_allow_html=True)
        mercado_origem = st.radio(
            'Mercado',
            ['Brasil (B3)', 'EUA (Global)'],
            horizontal=True,
            label_visibility='collapsed',
            key='generate_market',
        )

        if 'Brasil' in mercado_origem:
            active_investors_dict = INVESTORS_BR
        else:
            active_investors_dict = INVESTORS_US

        investor_options = list(active_investors_dict.values())
        if st.session_state.get('generate_investor') not in investor_options:
            st.session_state['generate_investor'] = investor_options[0]

        st.markdown('<p class="field-label mt">Persona de Validação</p>', unsafe_allow_html=True)
        investor = st.selectbox(
            'Selecione a Persona de Validação',
            investor_options,
            label_visibility='collapsed',
            key='generate_investor',
        )

        submitted = st.form_submit_button(
            '🚀  Gerar Relatório Completo',
            use_container_width=True,
            type='primary',
        )
    st.markdown('</div>', unsafe_allow_html=True)

with side_col:
    _render_side_panel()

_render_trends()

if submitted:
    ticker = ticker.strip().upper()
    if not ticker:
        st.warning('Preencha um ticker!')
    else:
        try:
            investor_name = {v: k for k, v in active_investors_dict.items()}[investor]
        except KeyError:
            st.error(f'Investidor {investor} não encontrado')
            investor_name = None

        if investor_name:
            with st.spinner('Iniciando análise e validando ativos...'):
                market_code = 'BR' if 'Brasil' in mercado_origem else 'US'
                generated = _generate_investor_report(
                    ticker=ticker,
                    investor_name=investor_name,
                    active_investors=active_investors_dict,
                    market=market_code,
                )

            if generated:
                _save_report(generated)
                st.session_state['last_generated_report'] = generated

result = st.session_state.get('last_generated_report')
if result:
    st.markdown('<div class="result-shell">', unsafe_allow_html=True)
    st.markdown('### Relatório Gerado')

    try:
        from src.utils_pdf import generate_pdf_bytes

        pdf_bytes = generate_pdf_bytes(result.ticker, result.investor_name, result.generated_at, result.data)
        st.download_button(
            label='📄 Baixar Relatório em PDF',
            data=pdf_bytes,
            file_name=f"{result.ticker}_{result.investor_name}_{result.generated_at.strftime('%Y%m%d')}.pdf",
            mime='application/pdf',
            type='primary',
            use_container_width=True,
        )
    except Exception as e:
        st.error(f'Erro ao disponibilizar PDF: {e}')

    display_report(result)
    st.markdown('</div>', unsafe_allow_html=True)
