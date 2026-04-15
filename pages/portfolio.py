from __future__ import annotations

import streamlit as st

from src.portfolio import PortfolioAnalysisOutput, PortfolioAnalyzer, generate_portfolio_pdf_bytes
from src.portfolio.persistence import (
    delete_saved_portfolio,
    duplicate_saved_portfolio,
    get_portfolio_report,
    get_saved_portfolio,
    list_portfolio_reports,
    list_saved_portfolios,
    mark_portfolio_analyzed,
    save_portfolio_composition,
    save_portfolio_report,
)
from src.portfolio.ui_helpers import (
    OBJECTIVE_OPTIONS,
    build_portfolio_input,
    composition_rows_for_table,
    get_persona_options,
    sanitize_row,
    sector_market_heatmap_data,
)

try:
    import plotly.graph_objects as go
except Exception:
    go = None


st.title('Analise de Portfolio')
st.caption('Monte sua carteira, escolha objetivo e persona, e gere uma leitura consolidada.')


def _default_row() -> dict:
    return {
        'ticker': '',
        'market': 'BR',
        'weight': 0.0,
        'quantity': None,
        'avg_price': None,
    }


if 'portfolio_rows' not in st.session_state:
    st.session_state.portfolio_rows = [_default_row()]
if 'portfolio_result' not in st.session_state:
    st.session_state.portfolio_result = None
if 'portfolio_persona_label' not in st.session_state:
    st.session_state.portfolio_persona_label = None
if 'portfolio_selected_id' not in st.session_state:
    st.session_state.portfolio_selected_id = None
if 'portfolio_reference_currency' not in st.session_state:
    st.session_state.portfolio_reference_currency = 'BRL'
if 'portfolio_saved_name' not in st.session_state:
    st.session_state.portfolio_saved_name = 'Minha Carteira'
if 'portfolio_current_objective' not in st.session_state:
    st.session_state.portfolio_current_objective = 'equilibrio'
if 'portfolio_current_persona_id' not in st.session_state:
    st.session_state.portfolio_current_persona_id = 'buffett'


st.markdown('#### Portfolios Salvos')
saved_portfolios = list_saved_portfolios()
portfolio_option_ids = [''] + [str(p.get('id')) for p in saved_portfolios]
portfolio_option_labels = ['(nenhum selecionado)'] + [
    f"{p.get('name', 'Sem nome')} • {len(p.get('items', []))} ativos"
    for p in saved_portfolios
]
if st.session_state.portfolio_selected_id not in portfolio_option_ids:
    st.session_state.portfolio_selected_id = ''

selection_col, name_col = st.columns([2, 2])
selected_portfolio_id = selection_col.selectbox(
    'Carteira salva',
    options=portfolio_option_ids,
    format_func=lambda pid: portfolio_option_labels[portfolio_option_ids.index(pid)],
    index=portfolio_option_ids.index(st.session_state.portfolio_selected_id),
)
st.session_state.portfolio_selected_id = selected_portfolio_id
portfolio_name_input = name_col.text_input('Nome da carteira', value=st.session_state.portfolio_saved_name)
st.session_state.portfolio_saved_name = portfolio_name_input

action_a, action_b, action_c, action_d = st.columns(4)
if action_a.button('Salvar composicao', use_container_width=True):
    try:
        saved = save_portfolio_composition(
            name=portfolio_name_input,
            items=st.session_state.portfolio_rows,
            objective=st.session_state.get('portfolio_objective', 'equilibrio'),
            persona=st.session_state.get('portfolio_persona_id'),
            reference_currency=st.session_state.get('portfolio_reference_currency', 'BRL'),
            portfolio_id=selected_portfolio_id or None,
        )
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.session_state.portfolio_selected_id = str(saved.get('id', ''))
        st.success('Composição salva com sucesso.')
        st.rerun()

if action_b.button('Carregar', use_container_width=True, disabled=not selected_portfolio_id):
    selected = get_saved_portfolio(selected_portfolio_id) if selected_portfolio_id else None
    if selected is None:
        st.error('Portfólio selecionado não foi encontrado.')
    else:
        st.session_state.portfolio_rows = list(selected.get('items', [])) or [_default_row()]
        st.session_state.portfolio_objective = selected.get('objective', 'equilibrio')
        if selected.get('persona'):
            st.session_state.portfolio_persona_id = str(selected.get('persona'))
        st.session_state.portfolio_reference_currency = str(selected.get('reference_currency', 'BRL'))
        st.session_state.portfolio_saved_name = str(selected.get('name', 'Minha Carteira'))
        st.success('Composição carregada.')
        st.rerun()

if action_c.button('Duplicar', use_container_width=True, disabled=not selected_portfolio_id):
    if not selected_portfolio_id:
        st.error('Selecione um portfólio para duplicar.')
    else:
        duplicate_name = f'{portfolio_name_input or "Minha Carteira"} (copia)'
        created = duplicate_saved_portfolio(selected_portfolio_id, duplicate_name)
        st.session_state.portfolio_selected_id = str(created.get('id', ''))
        st.success('Portfólio duplicado.')
        st.rerun()

confirm_delete = action_d.checkbox('Confirmar exclusao', value=False, key='portfolio_confirm_delete')
if action_d.button('Excluir', use_container_width=True, disabled=not selected_portfolio_id or not confirm_delete):
    if delete_saved_portfolio(selected_portfolio_id):
        st.session_state.portfolio_selected_id = ''
        st.success('Portfólio excluído.')
        st.rerun()
    st.error('Não foi possível excluir o portfólio selecionado.')

st.divider()


toolbar_a, toolbar_b, _ = st.columns([1, 1, 4])
if toolbar_a.button('Adicionar ativo', use_container_width=True):
    st.session_state.portfolio_rows.append(_default_row())
    st.rerun()
if toolbar_b.button('Remover ultimo', use_container_width=True, disabled=len(st.session_state.portfolio_rows) <= 1):
    st.session_state.portfolio_rows.pop()
    st.rerun()


updated_rows: list[dict] = []
for idx, row in enumerate(st.session_state.portfolio_rows):
    row = sanitize_row(row)
    with st.container(border=True):
        st.markdown(f'**Ativo {idx + 1}**')
        c1, c2, c3, c4, c5 = st.columns([1.5, 1, 1, 1, 1])
        ticker = c1.text_input('Ticker', value=row['ticker'], key=f'portfolio_ticker_{idx}')
        market = c2.selectbox('Mercado', options=['BR', 'US'], index=['BR', 'US'].index(row['market']), key=f'portfolio_market_{idx}')
        weight = c3.number_input('Peso (%)', min_value=0.0, max_value=100.0, value=float(row['weight']), step=0.1, key=f'portfolio_weight_{idx}')
        quantity = c4.number_input('Quantidade', min_value=0.0, value=float(row['quantity'] or 0.0), step=1.0, key=f'portfolio_quantity_{idx}')
        avg_price = c5.number_input('Preco Medio', min_value=0.0, value=float(row['avg_price'] or 0.0), step=0.01, key=f'portfolio_avg_price_{idx}')

        updated_rows.append(
            {
                'ticker': ticker,
                'market': market,
                'weight': weight,
                'quantity': quantity if quantity > 0 else None,
                'avg_price': avg_price if avg_price > 0 else None,
            }
        )

st.session_state.portfolio_rows = updated_rows

markets = {r.get('market', 'BR') for r in updated_rows if r.get('market')}
persona_options = get_persona_options(markets)
persona_ids = list(persona_options.keys())
persona_labels = [persona_options[k] for k in persona_ids]

default_persona_id = persona_ids[0]
if st.session_state.get('portfolio_persona_id') not in persona_ids:
    st.session_state.portfolio_persona_id = default_persona_id

left, middle, right = st.columns(3)
objective_id = left.selectbox(
    'Objetivo da Carteira',
    options=list(OBJECTIVE_OPTIONS.keys()),
    format_func=lambda x: OBJECTIVE_OPTIONS[x],
    index=list(OBJECTIVE_OPTIONS.keys()).index(st.session_state.get('portfolio_objective', 'equilibrio')),
)
persona_label = middle.selectbox(
    'Persona',
    options=persona_labels,
    index=persona_labels.index(persona_options[st.session_state.portfolio_persona_id]) if persona_options[st.session_state.portfolio_persona_id] in persona_labels else 0,
)
reference_currency = right.selectbox(
    'Moeda de Referencia',
    options=['BRL', 'USD'],
    index=['BRL', 'USD'].index(st.session_state.get('portfolio_reference_currency', 'BRL')),
)
st.session_state.portfolio_reference_currency = reference_currency

persona_id = {v: k for k, v in persona_options.items()}[persona_label]
st.session_state.portfolio_persona_id = persona_id
st.session_state.portfolio_objective = objective_id
st.session_state.portfolio_current_objective = objective_id
st.session_state.portfolio_current_persona_id = persona_id

if len(updated_rows) > 20:
    st.warning('Carteira com mais de 20 ativos pode demorar mais para processar.')

if st.button('Gerar Analise de Portfolio', type='primary', use_container_width=True):
    try:
        analysis_input = build_portfolio_input(
            rows=updated_rows,
            objective=objective_id,
            persona=persona_id,
            reference_currency=reference_currency,
        )
    except ValueError as exc:
        st.error(str(exc))
    else:
        st.markdown('#### Progresso da Analise por Ativo')
        status_placeholders: dict[int, any] = {}
        for idx, item in enumerate(analysis_input.items):
            ph = st.empty()
            ph.info(f'⏳ {item.ticker} ({item.market}) aguardando')
            status_placeholders[idx] = ph

        progress_bar = st.progress(0.0, text=f'0/{len(analysis_input.items)} concluidos')
        tracker = {'cached': 0, 'failed': 0}

        def _progress_callback(event: dict):
            asset_id = int(event.get('asset_id', -1))
            ticker = event.get('ticker', 'N/A')
            market = event.get('market', 'N/A')
            status = event.get('status', '')
            ph = status_placeholders.get(asset_id)

            if status == 'running' and ph is not None:
                ph.info(f'🔄 {ticker} ({market}) analisando...')
            elif status == 'done' and ph is not None:
                used_cache = bool(event.get('used_cached_analysis', False))
                if used_cache:
                    tracker['cached'] += 1
                    ph.success(f'♻️ {ticker} ({market}) concluido via cache')
                else:
                    ph.success(f'✅ {ticker} ({market}) concluido')
            elif status == 'failed' and ph is not None:
                tracker['failed'] += 1
                error_type = event.get('error_type', 'Erro')
                ph.error(f'❌ {ticker} ({market}) falhou: {error_type}')

            completed = int(event.get('completed', 0))
            total = int(event.get('total', len(analysis_input.items)))
            if total > 0 and completed >= 0:
                ratio = min(max(completed / total, 0.0), 1.0)
                progress_bar.progress(
                    ratio,
                    text=(
                        f'{completed}/{total} concluidos'
                        f' | cache hits: {tracker["cached"]}'
                        f' | falhas: {tracker["failed"]}'
                    ),
                )

        with st.spinner('Executando analise consolidada da carteira...'):
            analyzer = PortfolioAnalyzer()
            output = analyzer.analyze(analysis_input, progress_callback=_progress_callback)
        st.session_state.portfolio_result = output.model_dump(mode='json')
        st.session_state.portfolio_persona_label = persona_label
        saved_report = save_portfolio_report(
            analysis_input=analysis_input,
            analysis_output=output,
            portfolio_name=portfolio_name_input or 'Portfólio sem nome',
            portfolio_id=selected_portfolio_id or None,
        )
        st.session_state.portfolio_last_report_id = str(saved_report.get('id', ''))
        if selected_portfolio_id:
            mark_portfolio_analyzed(selected_portfolio_id)
        st.success('Analise de portfolio concluida.')


def _render_result(output: PortfolioAnalysisOutput, persona_name: str | None):
    st.divider()
    st.subheader('Resultado Consolidado')

    c1, c2, c3 = st.columns(3)
    c1.metric('Score Geral', f'{float(output.overall_score or 0.0):.1f}/10')
    c1.progress(min(max(float(output.overall_score or 0.0) / 10.0, 0.0), 1.0))
    c2.metric('Sentimento', output.portfolio_sentiment)
    c2.metric('Confianca Ponderada', f'{float(output.weighted_confidence):.1f}%')
    c3.metric('Score Diversificacao', f'{float(output.diversification_score or 0.0):.1f}/10')

    st.markdown('#### Subscores')
    if output.subscores:
        st.dataframe(
            [{'Dimensao': k, 'Score': round(float(v), 2)} for k, v in output.subscores.items()],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info('Subscores indisponiveis para esta analise.')

    st.markdown('#### Composicao da Carteira')
    st.dataframe(composition_rows_for_table(output.asset_analyses), use_container_width=True, hide_index=True)

    st.markdown('#### Visualizacoes Graficas')
    if go is None:
        st.warning('Plotly nao disponivel neste ambiente. Graficos nao foram renderizados.')
    else:
        chart1, chart2, chart3 = st.columns(3)

        with chart1:
            fig = go.Figure(
                data=[
                    go.Pie(
                        labels=[a.ticker for a in output.asset_analyses],
                        values=[float(a.normalized_weight) for a in output.asset_analyses],
                        hole=0.45,
                    )
                ]
            )
            fig.update_layout(title='Alocacao por Ativo', legend_title='Ativos', margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with chart2:
            breakdown = output.sentiment_breakdown or {'BULLISH': 0.0, 'NEUTRAL': 0.0, 'BEARISH': 0.0}
            fig = go.Figure()
            fig.add_trace(go.Bar(name='BULLISH', x=['Sentimento Ponderado'], y=[breakdown.get('BULLISH', 0.0)]))
            fig.add_trace(go.Bar(name='NEUTRAL', x=['Sentimento Ponderado'], y=[breakdown.get('NEUTRAL', 0.0)]))
            fig.add_trace(go.Bar(name='BEARISH', x=['Sentimento Ponderado'], y=[breakdown.get('BEARISH', 0.0)]))
            fig.update_layout(
                barmode='stack',
                title='Distribuicao de Sentimento (%)',
                yaxis_title='Percentual',
                legend_title='Classe',
                margin=dict(l=10, r=10, t=45, b=10),
            )
            st.plotly_chart(fig, use_container_width=True)

        with chart3:
            x, y, z = sector_market_heatmap_data(
                output.concentration_metrics.market_weights,
                output.concentration_metrics.sector_weights,
            )
            fig = go.Figure(data=go.Heatmap(z=z, x=x, y=y, text=z, texttemplate='%{text}', colorscale='YlGnBu'))
            fig.update_layout(title='Mapa de Calor de Concentracao', margin=dict(l=10, r=10, t=45, b=10))
            st.plotly_chart(fig, use_container_width=True)

    st.markdown('#### Alertas')
    alerts = list(output.concentration_metrics.alerts or [])
    if output.objective_fit:
        alerts.extend([str(a) for a in output.objective_fit.get('alerts', [])])
    alerts.extend(output.risks[:2])
    if alerts:
        for alert in alerts:
            st.warning(alert)
    else:
        st.success('Sem alertas relevantes de concentracao e risco.')

    col_left, col_right = st.columns(2)
    with col_left:
        st.markdown('#### Forcas')
        for item in output.strengths:
            st.markdown(f'- {item}')
    with col_right:
        st.markdown('#### Fragilidades')
        for item in output.weaknesses:
            st.markdown(f'- {item}')

    st.markdown('#### Sugestoes de Rebalanceamento')
    for item in output.rebalancing_suggestions:
        st.markdown(f'- {item}')

    st.markdown('#### Parecer Final da Persona')
    persona_header = persona_name or 'Persona'
    if output.persona_analysis:
        st.info(f'**{persona_header}**\n\n{output.persona_analysis}')
    else:
        st.info('Parecer da persona indisponivel para esta analise.')

    if output.failed_assets:
        st.markdown('#### Ativos com Falha')
        st.dataframe(
            [
                {
                    'Ticker': a.ticker,
                    'Mercado': a.market,
                    'Erro': a.error_type,
                    'Mensagem': a.error_message,
                }
                for a in output.failed_assets
            ],
            use_container_width=True,
            hide_index=True,
        )

    if output.analysis_metadata.warnings:
        with st.expander('Avisos da Execucao'):
            for warning in output.analysis_metadata.warnings:
                st.markdown(f'- {warning}')


if st.session_state.portfolio_result:
    parsed = PortfolioAnalysisOutput(**st.session_state.portfolio_result)
    _render_result(parsed, st.session_state.get('portfolio_persona_label'))
    pdf_bytes = generate_portfolio_pdf_bytes(
        portfolio_name=st.session_state.get('portfolio_saved_name', 'Portfólio'),
        objective=st.session_state.get('portfolio_current_objective', 'equilibrio'),
        persona_name=st.session_state.get('portfolio_persona_label', 'Persona'),
        output=parsed,
    )
    st.download_button(
        'Baixar PDF da Analise de Portfolio',
        data=pdf_bytes,
        file_name='portfolio_analise.pdf',
        mime='application/pdf',
        use_container_width=True,
    )

st.divider()
st.markdown('#### Analises de Portfolio Salvas')
saved_reports = list_portfolio_reports()
if not saved_reports:
    st.info('Nenhuma análise de portfólio salva ainda.')
else:
    report_ids = [str(r.get('id')) for r in saved_reports]
    default_report_id = st.session_state.get('portfolio_last_report_id', report_ids[0])
    if default_report_id not in report_ids:
        default_report_id = report_ids[0]
    selected_report_id = st.selectbox(
        'Histórico de análises',
        options=report_ids,
        format_func=lambda rid: (
            f"{next((r.get('portfolio_name', 'Carteira') for r in saved_reports if str(r.get('id')) == rid), 'Carteira')}"
            f" • {next((r.get('generated_at', '') for r in saved_reports if str(r.get('id')) == rid), '')[:16]}"
            f" • score {next((float(r.get('overall_score', 0.0)) for r in saved_reports if str(r.get('id')) == rid), 0.0):.1f}"
        ),
    )
    if st.button('Abrir analise salva', use_container_width=True):
        selected_report = get_portfolio_report(selected_report_id)
        if selected_report is None:
            st.error('Relatório não encontrado.')
        else:
            st.session_state.portfolio_result = selected_report.get('data')
            st.session_state.portfolio_persona_label = selected_report.get('persona')
            st.session_state.portfolio_current_objective = selected_report.get('objective', 'equilibrio')
            st.session_state.portfolio_saved_name = selected_report.get('portfolio_name', 'Minha Carteira')
            st.session_state.portfolio_last_report_id = selected_report_id
            st.success('Análise salva carregada.')
            st.rerun()
