import asyncio
import datetime
import json
from pathlib import Path

import nest_asyncio

import streamlit as st

from src.data import stocks
from src.agents.analysts import (
    earnings_release,
    financial,
    valuation,
    news,
    macro,
    technical,
)
from src.agents.investors import (
    buffett,
    graham,
    barsi,
    lynch,
)
from src.settings import DB_DIR, INVESTORS_BR, INVESTORS_US, PROVIDER, MODEL, API_KEY
from pages._utils import Report, display_report


if not PROVIDER or not MODEL or not API_KEY:
    st.error('Por favor, configure o modelo e a chave de API no menu de configurações')
    st.stop()


st.set_page_config(layout='centered')


def _generate_investor_report(
    ticker: str,
    investor_name: str,
    active_investors: dict,
) -> Report | None:
    if investor_name not in active_investors.keys():
        st.error(f'Investidor {investor_name} não encontrado')
        return

    ticker = ticker.upper()

    # verifica se o ticker existe
    try:
        stocks.details(ticker)
    except ValueError:
        st.error(f'Ticker {ticker} não encontrado')
        return

    # ai analysts — execução paralela com asyncio
    # nest_asyncio permite asyncio.run() dentro do event loop do Streamlit
    nest_asyncio.apply()

    async def _run_analysts() -> tuple:
        return await asyncio.gather(
            asyncio.to_thread(earnings_release.analyze, ticker),
            asyncio.to_thread(financial.analyze, ticker),
            asyncio.to_thread(valuation.analyze, ticker),
            asyncio.to_thread(news.analyze, ticker),
            asyncio.to_thread(macro.analyze, ticker),
            asyncio.to_thread(technical.analyze, ticker),
        )

    st.markdown("#### Analisando empresa em paralelo...")
    col1, col2, col3 = st.columns(3)
    col4, col5, col6 = st.columns(3)
    
    with col1: ph_earnings = st.empty(); ph_earnings.info("⏳ Earnings...")
    with col2: ph_financial = st.empty(); ph_financial.info("⏳ Finanças...")
    with col3: ph_valuation = st.empty(); ph_valuation.info("⏳ Valuation...")
    with col4: ph_news = st.empty(); ph_news.info("⏳ Notícias...")
    with col5: ph_macro = st.empty(); ph_macro.info("⏳ Macro...")
    with col6: ph_tech = st.empty(); ph_tech.info("⏳ MCP Técnico...")

    (
        earnings_release_analysis,
        financial_analysis,
        valuation_analysis,
        news_analysis,
        macro_analysis,
        technical_analysis,
    ) = asyncio.run(_run_analysts())

    ph_earnings.success("✅ Earnings")
    ph_financial.success("✅ Finanças")
    ph_valuation.success("✅ Valuation")
    ph_news.success("✅ Notícias")
    ph_macro.success("✅ Macro")
    ph_tech.success("✅ MCP Técnico")

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


st.title('Gerar Relatório Analítico de Ações')

ticker = st.text_input('Insira o Ticker da ação (ex: PETR4.SA ou AAPL)')
mercado_origem = st.radio("Selecione o Mercado Origem", ["🇧🇷 Brasil (B3)", "🇺🇸 EUA (NYSE/NASDAQ)"])

if "Brasil" in mercado_origem:
    active_investors_dict = INVESTORS_BR
else:
    active_investors_dict = INVESTORS_US

investor = st.selectbox('Selecione a Persona de Validação', list(active_investors_dict.values()))

try:
    investor_name = {v: k for k, v in active_investors_dict.items()}[investor]
except KeyError:
    st.error(f'Investidor {investor} não encontrado')
    investor_name = None

result = None
if st.button('Gerar Relatório Completo'):
    if not ticker:
        st.warning("Preencha um ticker!")
        st.stop()
        
    result = _generate_investor_report(ticker, investor_name, active_investors_dict)
    if result:
        _save_report(result)
        display_report(result)

