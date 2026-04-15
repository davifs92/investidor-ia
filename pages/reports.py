import json
from hashlib import sha1

import streamlit as st

from pages._utils import Report, display_report
from src.settings import DB_DIR, INVESTORS


def _apply_reports_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

            .stApp,
            [data-testid="stAppViewContainer"],
            [data-testid="stHeader"] {
                background: #fcf9f8;
            }

            section.main > div {
                max-width: 1180px;
                padding-top: 1.1rem;
                padding-bottom: 2.4rem;
            }

            .reports-top {
                display: flex;
                align-items: center;
                justify-content: space-between;
                margin-bottom: 0.9rem;
            }

            .top-title {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 2.05rem;
                line-height: 1.1;
                letter-spacing: -0.03em;
                color: #004f45;
                font-weight: 800;
            }

            .reports-headline {
                margin: 0.3rem 0 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: clamp(2.2rem, 4vw, 3.4rem);
                line-height: 0.95;
                letter-spacing: -0.04em;
                color: #1c1b1b;
                font-weight: 800;
            }

            .reports-sub {
                margin: 0.55rem 0 0.9rem;
                max-width: 740px;
                color: #3e4946;
                font-size: 0.98rem;
                line-height: 1.52;
            }

            div[data-testid="stTextInput"] input {
                border: 0 !important;
                background: #e5e2e1 !important;
                border-radius: 999px !important;
                min-height: 2.42rem !important;
                font-size: 0.9rem !important;
            }

            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                border: 0 !important;
                background: #ebe7e7 !important;
                border-radius: 999px !important;
                min-height: 2.42rem !important;
            }

            div[data-testid="stButton"] button {
                border: 0 !important;
                border-radius: 999px !important;
                min-height: 2.42rem !important;
                font-family: "Plus Jakarta Sans", sans-serif !important;
                font-weight: 700 !important;
                font-size: 0.88rem !important;
            }

            .new-report-btn button {
                background: linear-gradient(95deg, #004f45 0%, #00695c 100%) !important;
                color: white !important;
            }

            [class*="st-key-report-row-"] {
                border-radius: 12px;
                background: #ffffff;
                padding: 0.75rem 0.85rem;
                margin-bottom: 0.58rem;
                box-shadow: 0 24px 32px rgba(28, 27, 27, 0.04);
            }

            .ticker-box {
                width: 64px;
                height: 64px;
                border-radius: 10px;
                background: #f6f3f2;
                display: grid;
                place-items: center;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 2rem;
                font-weight: 800;
                letter-spacing: -0.03em;
                color: #004f45;
                margin: 0 auto;
            }

            .mini-label {
                margin: 0;
                font-size: 0.6rem;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #6e7976;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .mini-value {
                margin: 0.18rem 0 0;
                color: #1c1b1b;
                font-size: 1.6rem;
                line-height: 1.05;
                letter-spacing: -0.03em;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-weight: 800;
            }

            .mini-sub {
                margin: 0.15rem 0 0;
                color: #3e4946;
                font-size: 0.92rem;
                font-weight: 600;
            }

            .sentiment-chip {
                display: inline-flex;
                align-items: center;
                border-radius: 999px;
                padding: 0.3rem 0.6rem;
                font-size: 0.64rem;
                text-transform: uppercase;
                letter-spacing: 0.05em;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-weight: 800;
            }

            .chip-bull {
                background: #c6e6de;
                color: #2f4c46;
            }

            .chip-bear {
                background: #ffdad6;
                color: #93000a;
            }

            .chip-neutral {
                background: #ebe7e7;
                color: #3e4946;
            }

            .empty-zone {
                margin-top: 1.4rem;
                border-top: 1px solid rgba(190, 201, 197, 0.45);
                padding-top: 1.5rem;
                text-align: center;
            }

            .empty-icon {
                width: 62px;
                height: 62px;
                border-radius: 999px;
                margin: 0 auto 0.45rem;
                display: grid;
                place-items: center;
                background: #f0edec;
                color: #7ea29a;
                font-size: 1.4rem;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-weight: 800;
            }

            .actions-wrap {
                margin-top: 1rem;
            }

            .toolbar-actions {
                display: flex;
                justify-content: flex-end;
                align-items: center;
                gap: 0.55rem;
            }

            .list-wrap {
                margin-top: 0.2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_reports() -> list[Report]:
    reports_file = DB_DIR / 'reports.json'
    if reports_file.exists():
        with open(reports_file, 'r') as f:
            content = f.read()
            reports = json.loads(content) if content else []
            if reports:
                parsed = [Report(**report) for report in reports]
                return sorted(parsed, key=lambda x: x.generated_at, reverse=True)
    return []


def _save_reports(reports: list[Report]):
    reports_file = DB_DIR / 'reports.json'
    with open(reports_file, 'w') as f:
        json_reports = [json.loads(report.model_dump_json()) for report in reports]
        json.dump(json_reports, f)


def _delete_report(report: Report):
    reports = _load_reports()
    for i, _report in enumerate(reports):
        if report == _report:
            reports.pop(i)
            break
    _save_reports(reports)


@st.dialog(title='Excluir Relatório')
def _delete_dialog(report: Report):
    st.title('Deletar Relatório?')
    col1, col2 = st.columns(2)
    with col1:
        if st.button('Sim'):
            _delete_report(report)
            st.session_state.selected_report_id = None
            st.rerun()
    with col2:
        if st.button('Não'):
            st.rerun()


def _report_id(report: Report) -> str:
    return f'{report.ticker}|{report.investor_name}|{report.generated_at.isoformat()}'


def _report_widget_key(report: Report) -> str:
    return sha1(_report_id(report).encode('utf-8')).hexdigest()[:12]


def _sentiment(report: Report) -> str:
    return str(report.data.get('investor', {}).get('sentiment', 'NEUTRAL')).upper()


def _chip_html(sentiment: str) -> str:
    if sentiment == 'BULLISH':
        return '<span class="sentiment-chip chip-bull">↗ Bullish</span>'
    if sentiment == 'BEARISH':
        return '<span class="sentiment-chip chip-bear">↘ Bearish</span>'
    return '<span class="sentiment-chip chip-neutral">→ Neutral</span>'


def _format_date_br(dt) -> str:
    months = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun', 'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez']
    return f'{dt.day:02d} {months[dt.month - 1]}, {dt.year}'


def _open_generate_page():
    try:
        st.switch_page('pages/generate.py')
    except Exception:
        st.info('Abra a aba "Gerar Relatório" no menu lateral para criar um novo relatório.')


_apply_reports_styles()

if 'selected_report_id' not in st.session_state:
    st.session_state.selected_report_id = None

reports = _load_reports()

top_left, top_right = st.columns([2, 1.2], gap='small')
with top_left:
    st.markdown('<div class="reports-top"><p class="top-title">Meus Relatórios</p></div>', unsafe_allow_html=True)
with top_right:
    search = st.text_input('Buscar relatório', placeholder='Buscar relatório...', label_visibility='collapsed')

st.markdown('<h1 class="reports-headline">Relatórios Gerados</h1>', unsafe_allow_html=True)
st.markdown(
    '<p class="reports-sub">Acompanhe suas análises anteriores. O Silent Analyst AI mantém um registro histórico de cada insight estratégico gerado para seu portfólio.</p>',
    unsafe_allow_html=True,
)

filter_col, action_col = st.columns([1.1, 1.1], gap='small')
with filter_col:
    sentiment_filter = st.selectbox(
        'Filtrar',
        ['Todos', 'Bullish', 'Neutral', 'Bearish'],
        index=0,
        label_visibility='collapsed',
    )
with action_col:
    st.markdown('<div class="toolbar-actions">', unsafe_allow_html=True)
    st.markdown('<div class="new-report-btn">', unsafe_allow_html=True)
    if st.button('+ Novo Relatório', use_container_width=True):
        _open_generate_page()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

filtered = reports
if search.strip():
    term = search.strip().lower()
    filtered = [
        r
        for r in filtered
        if term in r.ticker.lower()
        or term in INVESTORS.get(r.investor_name, r.investor_name).lower()
        or term in r.investor_name.lower()
    ]

if sentiment_filter != 'Todos':
    filtered = [r for r in filtered if _sentiment(r) == sentiment_filter.upper()]

selected = next((r for r in reports if _report_id(r) == st.session_state.selected_report_id), None)
if selected:
    st.markdown('<div class="actions-wrap">', unsafe_allow_html=True)
    st.markdown('### Relatório Aberto')
    st.caption(
        f'{selected.ticker.upper()} • {INVESTORS.get(selected.investor_name, selected.investor_name)} • '
        f'{selected.generated_at.strftime("%d/%m/%Y %H:%M")}'
    )
    display_report(selected)

    col1, col2 = st.columns([1, 1])
    with col1:
        try:
            from src.utils_pdf import generate_pdf_bytes

            pdf_bytes = generate_pdf_bytes(
                selected.ticker,
                selected.investor_name,
                selected.generated_at,
                selected.data,
            )
            st.download_button(
                label='📄 Baixar Relatório em PDF',
                data=pdf_bytes,
                file_name=f"{selected.ticker}_{selected.investor_name}_{selected.generated_at.strftime('%Y%m%d')}.pdf",
                mime='application/pdf',
                type='primary',
                use_container_width=True,
            )
        except Exception as e:
            st.error(f'Erro ao preparar arquivo para download: {e}')
    with col2:
        if st.button('Excluir relatório', type='tertiary', use_container_width=True):
            _delete_dialog(selected)
    st.markdown('</div>', unsafe_allow_html=True)
    st.divider()

if not filtered:
    st.markdown(
        """
        <div class="empty-zone">
            <div class="empty-icon">✦</div>
            <p>Fim do seu histórico recente.<br/>Refine sua estratégia gerando novas análises.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
for report in filtered:
    rid = _report_id(report)
    widget_key = _report_widget_key(report)
    sentiment = _sentiment(report)
    persona_display = INVESTORS.get(report.investor_name, report.investor_name)
    with st.container(key=f'report-row-{widget_key}'):
        row_col1, row_col2, row_col3, row_col4, row_col5, row_col6 = st.columns(
            [0.95, 1.7, 1.9, 1.5, 1.1, 1],
            gap='small',
        )
        with row_col1:
            st.markdown(f'<div class="ticker-box">{report.ticker.upper()[:4]}</div>', unsafe_allow_html=True)
        with row_col2:
            st.markdown('<p class="mini-label">Empresa</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="mini-sub">{report.ticker.upper()}</p>', unsafe_allow_html=True)
        with row_col3:
            st.markdown('<p class="mini-label">Persona</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="mini-sub">{persona_display}</p>', unsafe_allow_html=True)
        with row_col4:
            st.markdown('<p class="mini-label">Data</p>', unsafe_allow_html=True)
            st.markdown(f'<p class="mini-sub">{_format_date_br(report.generated_at)}</p>', unsafe_allow_html=True)
        with row_col5:
            st.markdown('<p class="mini-label">&nbsp;</p>', unsafe_allow_html=True)
            st.markdown(_chip_html(sentiment), unsafe_allow_html=True)
        with row_col6:
            if st.button('Abrir', key=f'open_{widget_key}', type='primary' if rid == st.session_state.selected_report_id else 'secondary', use_container_width=True):
                st.session_state.selected_report_id = rid
                st.rerun()
