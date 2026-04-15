import datetime
import re

import streamlit as st
from pydantic import BaseModel


class Report(BaseModel):
    ticker: str
    investor_name: str
    generated_at: datetime.datetime
    data: dict


_ANALYST_ORDER = [
    ('financial', 'Financeiro', 'Revenue Growth, Margins & Debt Profile'),
    ('valuation', 'Valuation', 'Intrinsic Value vs Market Price'),
    ('news', 'Noticias', 'Global Impact & Media Sentiment'),
    ('macro', 'Macro', 'Juros, inflacao e atividade economica'),
    ('technical', 'Tecnico', 'Support, Resistance & RSI Metrics'),
    ('earnings_release', 'Earnings', 'Guidance, resultados e surpresa'),
]


def _apply_report_styles():
    st.markdown(
        """
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Manrope:wght@400;500;600;700&display=swap');

            :root {
                --surface: #fcf9f8;
                --surface-low: #f6f3f2;
                --surface-lowest: #ffffff;
                --surface-high: #ebe7e7;
                --surface-highest: #e5e2e1;
                --primary: #004f45;
                --primary-container: #00695c;
                --on-surface: #1c1b1b;
                --on-surface-variant: #3e4946;
                --outline-variant: #bec9c5;
                --error: #ba1a1a;
                --inverse-surface: #313030;
                --inverse-on-surface: #f3f0ef;
            }

            .report-shell {
                margin-top: 1rem;
                max-width: 1040px;
            }

            .report-kicker {
                display: inline-flex;
                align-items: center;
                gap: 0.4rem;
                background: #c6e6de;
                color: #2f4c46;
                border-radius: 999px;
                font-family: "Plus Jakarta Sans", sans-serif;
                padding: 0.25rem 0.6rem;
                font-size: 0.62rem;
                text-transform: uppercase;
                letter-spacing: 0.08em;
                font-weight: 800;
                margin-bottom: 0.55rem;
            }

            .report-hero {
                display: grid;
                grid-template-columns: 2fr 1fr;
                gap: 1rem;
                align-items: end;
                margin-bottom: 0.7rem;
            }

            .report-ticker-wrap {
                display: flex;
                align-items: center;
                gap: 0.8rem;
            }

            .report-logo {
                width: 56px;
                height: 56px;
                border-radius: 10px;
                background: linear-gradient(180deg, #151515 0%, #262626 100%);
                display: grid;
                place-items: center;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 1.25rem;
                font-weight: 800;
                color: #ffffff;
                position: relative;
                overflow: hidden;
            }

            .report-logo::after {
                content: "";
                position: absolute;
                left: 12px;
                top: 8px;
                width: 12px;
                height: 38px;
                background: #f6f3f2;
                border-radius: 2px;
            }

            .report-ticker {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: clamp(2.2rem, 4vw, 3.2rem);
                line-height: 0.92;
                letter-spacing: -0.04em;
                color: var(--on-surface);
            }

            .report-sub {
                margin: 0.25rem 0 0;
                color: var(--on-surface-variant);
                font-size: 0.96rem;
            }

            .report-reco-label {
                margin: 0 0 0.35rem;
                text-align: right;
                font-size: 0.6rem;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                color: var(--on-surface-variant);
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .report-reco {
                text-align: right;
                font-family: "Plus Jakarta Sans", sans-serif;
                font-size: 3.1rem;
                line-height: 1;
                letter-spacing: -0.04em;
                font-weight: 800;
                color: var(--primary);
                margin: 0;
            }

            .report-grid {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0.65rem;
                margin: 0.8rem 0 2rem;
            }

            .metric-card {
                background: var(--surface-low);
                border-radius: 12px;
                padding: 0.82rem;
            }

            .metric-k {
                margin: 0;
                color: var(--on-surface-variant);
                font-size: 0.63rem;
                letter-spacing: 0.07em;
                text-transform: uppercase;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .metric-v {
                margin: 0.4rem 0 0;
                font-size: 2rem;
                line-height: 1;
                letter-spacing: -0.03em;
                color: var(--on-surface);
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .metric-sub {
                margin: 0.35rem 0 0;
                font-size: 0.68rem;
                color: var(--on-surface-variant);
            }

            .metric-card.confidence {
                background: linear-gradient(120deg, var(--primary) 0%, var(--primary-container) 100%);
            }

            .metric-card.confidence .metric-k,
            .metric-card.confidence .metric-v,
            .metric-card.confidence .metric-sub {
                color: white;
            }

            .report-h2 {
                margin: 0.2rem 0 0.65rem;
                font-family: "Plus Jakarta Sans", sans-serif;
                letter-spacing: -0.02em;
            }

            .report-shell [data-testid="stExpander"] {
                border: 0 !important;
                box-shadow: none !important;
                background: transparent !important;
            }

            .report-shell [data-testid="stExpander"] details {
                border-radius: 12px;
                background: var(--surface-lowest);
                box-shadow: 0 24px 32px rgba(28, 27, 27, 0.04);
                margin-bottom: 0.65rem;
            }

            .report-shell [data-testid="stExpander"] summary {
                border-radius: 12px;
                min-height: 64px;
            }

            .seg-badges {
                display: flex;
                gap: 0.4rem;
                flex-wrap: wrap;
                margin-bottom: 0.65rem;
            }

            .seg-badge {
                border-radius: 999px;
                font-size: 0.65rem;
                padding: 0.2rem 0.55rem;
                font-weight: 700;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .seg-neutral {
                background: #e5e2e1;
                color: #3e4946;
            }

            .seg-bull {
                background: #c6e6de;
                color: #004f45;
            }

            .seg-bear {
                background: #ffdad6;
                color: #93000a;
            }

            .seg-body {
                color: var(--on-surface);
                line-height: 1.75;
            }

            .seg-grid {
                display: grid;
                grid-template-columns: 1.2fr 0.9fr;
                gap: 1rem;
                margin-top: 0.4rem;
            }

            .seg-mini-table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 0.55rem;
                font-size: 0.78rem;
            }

            .seg-mini-table th {
                text-align: left;
                font-size: 0.58rem;
                letter-spacing: 0.09em;
                text-transform: uppercase;
                color: var(--on-surface-variant);
                padding-bottom: 0.28rem;
            }

            .seg-mini-table td {
                padding: 0.22rem 0;
                color: var(--on-surface);
            }

            .mini-chart {
                border-radius: 10px;
                min-height: 126px;
                background: linear-gradient(180deg, #dcd9d9 0%, #cfcaca 100%);
                padding: 0.8rem;
                display: flex;
                align-items: flex-end;
                gap: 0.25rem;
            }

            .mini-chart span {
                display: block;
                flex: 1;
                border-radius: 2px 2px 0 0;
                background: rgba(0, 79, 69, 0.72);
            }

            .verdict {
                margin-top: 1.7rem;
                border-radius: 24px;
                background: linear-gradient(120deg, #313030 0%, #2b2a2a 66%, #1f3b37 100%);
                padding: 1.4rem;
                color: var(--inverse-on-surface);
            }

            .verdict-head {
                display: flex;
                align-items: center;
                gap: 0.6rem;
                margin-bottom: 0.6rem;
            }

            .verdict-avatar {
                width: 44px;
                height: 44px;
                border-radius: 999px;
                display: grid;
                place-items: center;
                background: #84d5c5;
                color: #00201b;
                font-weight: 800;
                font-family: "Plus Jakarta Sans", sans-serif;
            }

            .verdict-title {
                margin: 0;
                font-family: "Plus Jakarta Sans", sans-serif;
                letter-spacing: -0.01em;
                font-size: 1.45rem;
            }

            .verdict-sub {
                margin: 0.2rem 0 0.85rem;
                color: #84d5c5;
                font-size: 0.82rem;
            }

            .verdict-content {
                margin: 0;
                font-size: 0.98rem;
                line-height: 1.7;
                color: #f3f0ef;
            }

            .verdict-foot {
                margin-top: 0.85rem;
                padding-top: 0.85rem;
                border-top: 1px solid rgba(243, 240, 239, 0.25);
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 0.7rem;
            }

            .foot-k {
                margin: 0;
                font-size: 0.56rem;
                color: #84d5c5;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                font-weight: 800;
            }

            .foot-v {
                margin: 0.2rem 0 0;
                font-size: 0.72rem;
                color: #f3f0ef;
            }

            .disclaimer {
                margin-top: 0.95rem;
                color: #6e7976;
                font-size: 0.72rem;
                line-height: 1.5;
            }

            @media (max-width: 980px) {
                .report-hero {
                    grid-template-columns: 1fr;
                }

                .report-reco-label,
                .report-reco {
                    text-align: left;
                }

                .report-grid {
                    grid-template-columns: 1fr 1fr;
                }

                .seg-grid {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _safe_analysts(report: Report) -> dict:
    return report.data.get('analysts', {}) if isinstance(report.data, dict) else {}


def _safe_investor(report: Report) -> dict:
    return report.data.get('investor', {}) if isinstance(report.data, dict) else {}


def _sentiment_class(sentiment: str) -> str:
    if sentiment == 'BULLISH':
        return 'seg-bull'
    if sentiment == 'BEARISH':
        return 'seg-bear'
    return 'seg-neutral'


def _consensus_from_analysts(analysts: dict) -> tuple[int, int, int]:
    bullish = 0
    bearish = 0
    neutral = 0
    for data in analysts.values():
        sentiment = str(data.get('sentiment', '')).upper()
        if sentiment == 'BULLISH':
            bullish += 1
        elif sentiment == 'BEARISH':
            bearish += 1
        else:
            neutral += 1
    return bullish, neutral, bearish


def _extract_price_like(text: str) -> str:
    if not text:
        return 'N/A'
    match = re.search(r'(R\$ ?\d+[.,]?\d*|\$\d+[.,]?\d*)', text)
    return match.group(1) if match else 'N/A'


def _short_text(text: str, max_chars: int = 260) -> str:
    clean = re.sub(r'\s+', ' ', text).strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 3].rstrip() + '...'


def display_report(report: Report):
    _apply_report_styles()

    analysts = _safe_analysts(report)
    investor = _safe_investor(report)

    sentiment = str(investor.get('sentiment', 'NEUTRAL')).upper()
    confidence = int(investor.get('confidence', 0))
    investor_text = str(investor.get('content', 'Sem resumo final da persona disponível.')).replace('$', r'\$')
    bullish, neutral, bearish = _consensus_from_analysts(analysts)
    extracted_price = _extract_price_like(investor_text)
    ticker_label = report.ticker.upper()

    st.markdown('<div class="report-shell">', unsafe_allow_html=True)
    st.markdown('<span class="report-kicker">AI Analysis Live</span>', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="report-hero">
            <div>
                <div class="report-ticker-wrap">
                    <div class="report-logo">{ticker_label[:1]}</div>
                    <div>
                        <h1 class="report-ticker">{ticker_label}</h1>
                        <p class="report-sub">{report.investor_name.title()} • {report.generated_at.strftime('%d/%m/%Y %H:%M')}</p>
                    </div>
                </div>
            </div>
            <div>
                <p class="report-reco-label">Overall Recommendation</p>
                <p class="report-reco">{sentiment}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="report-grid">
            <div class="metric-card">
                <p class="metric-k">Preco Referencia</p>
                <p class="metric-v">{extracted_price}</p>
                <p class="metric-sub">Extraido da analise consolidada</p>
            </div>
            <div class="metric-card">
                <p class="metric-k">Cobertura</p>
                <p class="metric-v">{len(analysts)} analistas</p>
                <p class="metric-sub">Escopo de visao 360</p>
            </div>
            <div class="metric-card">
                <p class="metric-k">Analyst Consensus</p>
                <p class="metric-v">{bullish}B / {neutral}N / {bearish}S</p>
                <p class="metric-sub">Bull, neutral, bearish</p>
            </div>
            <div class="metric-card confidence">
                <p class="metric-k">AI Confidence</p>
                <p class="metric-v">{confidence}%</p>
                <p class="metric-sub">Confianca do parecer final</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<h2 class="report-h2">Deep Dive Analysis</h2>', unsafe_allow_html=True)
    for idx, (key, title, subtitle) in enumerate(_ANALYST_ORDER):
        analysis = analysts.get(key)
        if not isinstance(analysis, dict):
            continue

        seg_sentiment = str(analysis.get('sentiment', 'NEUTRAL')).upper()
        seg_confidence = int(analysis.get('confidence', 0))
        seg_content = str(analysis.get('content', '')).replace('$', r'\$')
        expander_title = f'{title}  •  {subtitle}'
        with st.expander(expander_title, expanded=idx == 0):
            if idx == 0:
                preview = _short_text(seg_content, 240)
                st.markdown(
                    f"""
                    <div class="seg-badges">
                        <span class="seg-badge {_sentiment_class(seg_sentiment)}">Sentimento: {seg_sentiment}</span>
                        <span class="seg-badge seg-neutral">Confianca: {seg_confidence}%</span>
                    </div>
                    <div class="seg-grid">
                        <div>
                            <div class="seg-body">{preview}</div>
                            <table class="seg-mini-table">
                                <thead>
                                    <tr><th>Metric</th><th>Value</th><th>Signal</th></tr>
                                </thead>
                                <tbody>
                                    <tr><td>Consistencia</td><td>{seg_confidence}%</td><td>{seg_sentiment}</td></tr>
                                    <tr><td>Cobertura</td><td>{len(analysts)} agentes</td><td>360 View</td></tr>
                                    <tr><td>Tese</td><td>Qualitativa</td><td>Em andamento</td></tr>
                                </tbody>
                            </table>
                        </div>
                        <div class="mini-chart">
                            <span style="height:60%"></span>
                            <span style="height:74%"></span>
                            <span style="height:66%"></span>
                            <span style="height:86%"></span>
                            <span style="height:92%"></span>
                            <span style="height:70%"></span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div class="seg-badges">
                        <span class="seg-badge {_sentiment_class(seg_sentiment)}">Sentimento: {seg_sentiment}</span>
                        <span class="seg-badge seg-neutral">Confianca: {seg_confidence}%</span>
                    </div>
                    <div class="seg-body">{seg_content}</div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown(
        f"""
        <div class="verdict">
            <div class="verdict-head">
                <div class="verdict-avatar">{report.investor_name[:1].upper()}</div>
                <div>
                    <p class="verdict-title">The Oracle's Verdict</p>
                    <p class="verdict-sub">AI Persona: {report.investor_name.title()}</p>
                </div>
            </div>
            <p class="verdict-content">{investor_text}</p>
            <div class="verdict-foot">
                <div>
                    <p class="foot-k">Key Moat</p>
                    <p class="foot-v">Disciplina de execucao e vantagem competitiva sustentavel.</p>
                </div>
                <div>
                    <p class="foot-k">Capital Allocation</p>
                    <p class="foot-v">Alocacao focada em retorno e consistencia de longo prazo.</p>
                </div>
            </div>
        </div>
        <p class="disclaimer">
            Este relatório foi gerado por um sistema de IA e nao constitui recomendacao de investimento.
            Use apenas como apoio e sempre considere seu perfil de risco.
        </p>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)
