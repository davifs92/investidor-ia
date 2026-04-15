import datetime
from fpdf import FPDF, HTMLMixin

try:
    import markdown2 as _md
except Exception:
    _md = None
    try:
        import markdown as _md_alt
    except Exception:
        _md_alt = None
    else:
        _md_alt = _md_alt
else:
    _md_alt = None


def _pdf_safe(text: str) -> str:
    """Normaliza texto para charset suportado pelas fontes core do FPDF."""
    if not text:
        return ''
    replacements = {
        '—': '-',
        '–': '-',
        '“': '"',
        '”': '"',
        '’': "'",
        '‘': "'",
        '…': '...',
        '•': '- ',
        '\u00a0': ' ',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text.encode('latin-1', errors='replace').decode('latin-1')


def _to_html(text: str) -> str:
    """Converte markdown para HTML com fallback entre bibliotecas."""
    if _md is not None:
        return _md.markdown(text)
    if _md_alt is not None:
        return _md_alt.markdown(text)
    return text

# Subclasse para rodapé customizado com suporte a HTML
class MyFPDF(FPDF, HTMLMixin):
    def footer(self):
        # O footer só deve ser desenhado se houver uma página aberta
        if self.page_no() > 0:
            try:
                self.set_y(-15)
                self.set_font('helvetica', 'I', 8)
                self.set_text_color(128, 128, 128)
                # O placeholder {nb} será substituído pelo total de páginas pelo alias_nb_pages
                self.cell(0, 10, f'Página {self.page_no()}/{{nb}}', align='C')
            except Exception:
                pass

def _ensure_page(pdf: FPDF) -> None:
    """Garante que exista ao menos uma página aberta antes de qualquer escrita."""
    if pdf.page_no() == 0:
        pdf.add_page()

def generate_pdf_bytes(ticker: str, investor_name: str, generated_at: datetime.datetime, data: dict) -> bytes:
    # Cores baseadas no sentimento
    sentiment = data['investor'].get('sentiment', 'NEUTRAL')
    if sentiment == 'BULLISH':
        header_bg = (46, 125, 50) # Verde
        header_text = (255, 255, 255)
    elif sentiment == 'BEARISH':
        header_bg = (198, 40, 40) # Vermelho
        header_text = (255, 255, 255)
    else:
        header_bg = (255, 179, 0) # Âmbar
        header_text = (0, 0, 0)

    # Inicia instância do PDF
    pdf = MyFPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.alias_nb_pages()
    _ensure_page(pdf)

    # Banner de Cabeçalho
    _ensure_page(pdf)
    pdf.set_fill_color(*header_bg)
    pdf.rect(0, 0, 210, 45, 'F')
    
    pdf.set_text_color(*header_text)
    pdf.set_font('helvetica', 'B', 18)
    pdf.set_y(10)
    pdf.cell(0, 10, _pdf_safe(f"Relatório de Análise: {ticker}"), align='C', ln=True)
    
    pdf.set_font('helvetica', '', 12)
    pdf.cell(0, 8, _pdf_safe(f"Investidor: {investor_name}"), align='C', ln=True)
    
    pdf.set_font('helvetica', 'I', 10)
    pdf.cell(0, 6, _pdf_safe(f"Gerado em: {generated_at.strftime('%d/%m/%Y %H:%M')}"), align='C', ln=True)
    
    # Sentimento
    pdf.ln(20)
    pdf.set_text_color(0, 0, 0)
    pdf.set_fill_color(245, 245, 245)
    pdf.set_font('helvetica', 'B', 14)
    pdf.cell(
        0,
        12,
        _pdf_safe(f"  SENTIMENTO FINAL: {sentiment} ({data['investor'].get('confidence', 0)}%)"),
        fill=True,
        ln=True,
    )
    pdf.ln(5)

    # Conteúdo da Persona
    pdf.set_font('helvetica', '', 11)
    v_content = _pdf_safe(data['investor'].get('content', ''))
    if v_content:
        html_content = _to_html(v_content)
        try:
            _ensure_page(pdf)
            pdf.write_html(_pdf_safe(html_content))
        except Exception:
            _ensure_page(pdf)
            pdf.multi_cell(0, 5, _pdf_safe(v_content))
    
    pdf.ln(10)
    
    # Análises detalhadas
    pdf.set_font('helvetica', 'B', 14)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(0, 10, _pdf_safe("Análises Detalhadas dos Especialistas"), ln=True, align='C')
    pdf.ln(5)

    for group, label in [('earnings_release', 'Earnings Release'), ('financial', 'Financial'), ('valuation', 'Valuation'), ('news', 'News')]:
        if group in data.get('analysts', {}):
            analysis = data['analysts'][group]
            pdf.set_fill_color(252, 252, 252)
            pdf.set_font('helvetica', 'B', 12)
            pdf.set_text_color(21, 101, 192)
            pdf.cell(0, 10, _pdf_safe(f"  Especialista: {label}"), fill=True, ln=True)
            
            pdf.set_text_color(80, 80, 80)
            pdf.set_font('helvetica', 'I', 10)
            pdf.cell(
                0,
                8,
                _pdf_safe(f"  Status: {analysis.get('sentiment', 'N/A')} | Confiança: {analysis.get('confidence', 0)}%"),
                ln=True,
            )
            
            pdf.set_text_color(0, 0, 0)
            pdf.set_font('helvetica', '', 11)
            raw_content = _pdf_safe(analysis.get('content', ''))
            if raw_content:
                a_html = _to_html(raw_content)
                try:
                    _ensure_page(pdf)
                    pdf.write_html(_pdf_safe(a_html))
                except Exception:
                    _ensure_page(pdf)
                    pdf.multi_cell(0, 5, _pdf_safe(raw_content))
            pdf.ln(8)

    # Disclaimer
    _ensure_page(pdf)
    if pdf.get_y() > 230:
        pdf.add_page()
    pdf.set_y(-60)
    pdf.set_draw_color(150, 150, 150)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(5)
    pdf.set_font('helvetica', 'B', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.multi_cell(
        0,
        5,
        _pdf_safe(
            "Disclaimer: Este relatório foi gerado por um sistema de Inteligência Artificial e NÃO constitui recomendação de investimento."
        ),
        align='J',
    )

    # Retorna os bytes do PDF
    return bytes(pdf.output())
