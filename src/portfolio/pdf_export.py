from __future__ import annotations

import datetime as dt

from fpdf import FPDF

from src.portfolio.models import PortfolioAnalysisOutput
from src.utils_pdf import _pdf_safe


def _section_title(pdf: FPDF, title: str):
    pdf.set_x(pdf.l_margin)
    pdf.set_font('helvetica', 'B', 12)
    pdf.set_text_color(25, 25, 25)
    pdf.cell(0, 8, _pdf_safe(title), ln=True)
    pdf.ln(1)


def _bullet_lines(pdf: FPDF, items: list[str], fallback: str = 'Sem itens relevantes nesta seção.'):
    if not items:
        items = [fallback]
    pdf.set_font('helvetica', '', 10)
    pdf.set_text_color(30, 30, 30)
    for item in items:
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5, _pdf_safe(f'- {item}'))
    pdf.ln(1)


def generate_portfolio_pdf_bytes(
    portfolio_name: str,
    objective: str,
    persona_name: str,
    output: PortfolioAnalysisOutput,
    generated_at: dt.datetime | None = None,
) -> bytes:
    generated_at = generated_at or dt.datetime.now()

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=18)
    pdf.add_page()

    pdf.set_fill_color(0, 79, 69)
    pdf.rect(0, 0, 210, 30, 'F')
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('helvetica', 'B', 15)
    pdf.set_y(8)
    pdf.cell(0, 8, _pdf_safe(f'Analise de Portfolio: {portfolio_name}'), ln=True, align='C')
    pdf.set_font('helvetica', '', 9)
    pdf.cell(0, 5, _pdf_safe(f'Gerado em: {generated_at.strftime("%d/%m/%Y %H:%M")}'), ln=True, align='C')
    pdf.ln(12)

    pdf.set_text_color(20, 20, 20)
    _section_title(pdf, 'Resumo Executivo')
    pdf.set_font('helvetica', '', 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0,
        5,
        _pdf_safe(
            f'Score geral: {float(output.overall_score or 0.0):.1f}/10 | '
            f'Sentimento: {output.portfolio_sentiment} | '
            f'Confianca ponderada: {float(output.weighted_confidence):.1f}%'
        ),
    )
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0,
        5,
        _pdf_safe(
            f'Objetivo: {objective} | Persona: {persona_name} | '
            f'Diversificacao: {float(output.diversification_score or 0.0):.1f}/10'
        ),
    )
    pdf.ln(2)

    _section_title(pdf, 'Subscores')
    for key, value in (output.subscores or {}).items():
        pdf.set_font('helvetica', '', 10)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, _pdf_safe(f'- {key}: {float(value):.2f}'), ln=True)
    if not output.subscores:
        pdf.set_font('helvetica', '', 10)
        pdf.set_x(pdf.l_margin)
        pdf.cell(0, 5, _pdf_safe('- Subscores indisponíveis.'), ln=True)
    pdf.ln(2)

    _section_title(pdf, 'Composicao da Carteira')
    pdf.set_x(pdf.l_margin)
    pdf.set_font('helvetica', 'B', 9)
    pdf.cell(35, 6, _pdf_safe('Ticker'), border=1)
    pdf.cell(25, 6, _pdf_safe('Mercado'), border=1)
    pdf.cell(35, 6, _pdf_safe('Peso (%)'), border=1)
    pdf.cell(35, 6, _pdf_safe('Sentimento'), border=1)
    pdf.cell(30, 6, _pdf_safe('Confianca'), border=1)
    pdf.ln()
    pdf.set_font('helvetica', '', 9)
    for asset in output.asset_analyses:
        pdf.cell(35, 6, _pdf_safe(asset.ticker), border=1)
        pdf.cell(25, 6, _pdf_safe(asset.market), border=1)
        pdf.cell(35, 6, _pdf_safe(f'{float(asset.normalized_weight):.2f}'), border=1)
        pdf.cell(35, 6, _pdf_safe(asset.sentiment), border=1)
        pdf.cell(30, 6, _pdf_safe(f'{int(asset.confidence)}%'), border=1)
        pdf.ln()
    if not output.asset_analyses:
        pdf.cell(160, 6, _pdf_safe('Sem ativos analisados.'), border=1, ln=True)
    pdf.ln(3)

    _section_title(pdf, 'Alertas de Concentracao')
    _bullet_lines(pdf, list(output.concentration_metrics.alerts or []), fallback='Sem alertas de concentração.')

    _section_title(pdf, 'Forcas')
    _bullet_lines(pdf, list(output.strengths or []))

    _section_title(pdf, 'Fragilidades')
    _bullet_lines(pdf, list(output.weaknesses or []))

    _section_title(pdf, 'Riscos')
    _bullet_lines(pdf, list(output.risks or []))

    _section_title(pdf, 'Sugestoes de Rebalanceamento')
    _bullet_lines(pdf, list(output.rebalancing_suggestions or []))

    _section_title(pdf, 'Parecer Final da Persona')
    persona_text = output.persona_analysis or 'Parecer da persona não disponível.'
    pdf.set_font('helvetica', '', 10)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5, _pdf_safe(persona_text))
    pdf.ln(2)

    if output.failed_assets:
        _section_title(pdf, 'Ativos com Falha')
        for failed in output.failed_assets:
            pdf.set_font('helvetica', '', 10)
            pdf.set_x(pdf.l_margin)
            pdf.multi_cell(
                0,
                5,
                _pdf_safe(
                    f'- {failed.ticker} ({failed.market}) | {failed.error_type}: {failed.error_message}'
                ),
            )
        pdf.ln(2)

    if output.analysis_metadata.warnings:
        _section_title(pdf, 'Avisos da Execucao')
        _bullet_lines(pdf, list(output.analysis_metadata.warnings))

    if pdf.get_y() > 235:
        pdf.add_page()
    pdf.set_y(-28)
    pdf.set_draw_color(160, 160, 160)
    pdf.line(15, pdf.get_y(), 195, pdf.get_y())
    pdf.ln(4)
    pdf.set_font('helvetica', 'B', 8)
    pdf.set_text_color(95, 95, 95)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(
        0,
        4,
        _pdf_safe(
            'Disclaimer: Este relatório foi gerado por IA e não constitui recomendação de compra ou venda de ativos.'
        ),
        align='J',
    )

    return bytes(pdf.output())
