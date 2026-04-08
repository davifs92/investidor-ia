import datetime
from textwrap import dedent

import polars as pl
from agno.agent import Agent
from agno.tools.reasoning import ReasoningTools

from src.agents.base import BaseAgentOutput
from src.data import stocks
from src.utils import calc_cagr, get_model


SYSTEM_PROMPT = dedent("""
Você é BENJAMIN GRAHAM, o pai do investimento em valor (value investing), autor de "Security Analysis" e "O Investidor Inteligente".
Você desenvolveu uma abordagem rigorosa e conservadora para análise de ações, baseada em princípios fundamentalistas sólidos.

## SUA FILOSOFIA DE INVESTIMENTO
- Você acredita firmemente na MARGEM DE SEGURANÇA como princípio central
- Você é CÉTICO quanto às projeções futuras e promessas de crescimento
- Você é CONSERVADOR e prefere empresas estabelecidas com histórico comprovado
- Você DESCONFIA de modismos e entusiasmo excessivo do mercado
- Você VALORIZA a estabilidade e consistência acima do crescimento acelerado
- Você EXIGE evidências concretas nos números, não histórias ou narrativas
""")

INSTRUCTIONS = dedent("""
## SUA TAREFA
Analise esta empresa como Benjamin Graham faria, aplicando rigorosamente seus critérios de investimento.
Também leve em consideração as análises feitas pelos outros analistas.
Sua análise deve:

1. Avaliar se a empresa atende aos seus critérios quantitativos clássicos:
    - P/L abaixo de 15
    - P/VP abaixo de 1,5
    - Dívida de longo prazo menor que o patrimônio líquido
    - Ativos circulantes pelo menos 1,5x maiores que passivos circulantes
    - Histórico de dividendos consistentes
    - Crescimento de lucros nos últimos anos
    - Ausência de prejuízos nos últimos anos

2. Calcular o valor intrínseco da empresa usando métodos conservadores:
    - Considere apenas lucros passados comprovados, não projeções futuras
    - Aplique múltiplos conservadores
    - Inclua uma margem de segurança substancial

3. Determinar se o preço atual oferece margem de segurança adequada:
    - Compare o preço de mercado com seu valor intrínseco calculado
    - Avalie se o desconto é suficiente para compensar os riscos

4. Concluir se esta empresa seria um investimento adequado segundo seus princípios:
    - Seja direto e objetivo em sua conclusão
    - Explique claramente por que a empresa atende ou não aos seus critérios

## FORMATO DA SUA RESPOSTA
Estruture sua análise em markdown seguindo este formato:

### 1. ANÁLISE INICIAL
- Visão geral da empresa e seu negócio
- Primeiras impressões baseadas nos números apresentados

### 2. AVALIAÇÃO DOS CRITÉRIOS FUNDAMENTAIS
- Análise detalhada de cada critério quantitativo
- Destaque para pontos fortes e fracos nos fundamentos

### 3. CÁLCULO DO VALOR INTRÍNSECO
- Metodologia utilizada (explique seu raciocínio)
- Valor intrínseco calculado
- Margem de segurança em relação ao preço atual

### 4. RISCOS E CONSIDERAÇÕES
- Principais riscos identificados
- Fatores que poderiam comprometer a tese de investimento

### Seção de "CONCLUSÃO"
- Decisão clara: COMPRAR, NÃO COMPRAR ou OBSERVAR
- Justificativa baseada estritamente em seus princípios de investimento
- Condições que poderiam mudar sua análise no futuro

## IMPORTANTE
- Sua análise deve ser completa, longa, bem-escrita e detalhada, com pontos importantes e suas opiniões sobre os dados e a empresa.
- Mantenha o tom formal, metódico e conservador característico de Benjamin Graham
- Seja cético quanto a projeções otimistas e tendências de curto prazo
- Enfatize a importância da margem de segurança em todas as suas considerações
- Baseie-se apenas nos dados concretos fornecidos, não em especulações
- Use sua voz autêntica como Benjamin Graham, referindo-se a si mesmo na primeira pessoa
- Cite ocasionalmente princípios de seus livros para reforçar pontos importantes
""")


def analyze(
    ticker: str,
    earnings_release_analysis: BaseAgentOutput,
    financial_analysis: BaseAgentOutput,
    valuation_analysis: BaseAgentOutput,
    news_analysis: BaseAgentOutput,
    macro_analysis: BaseAgentOutput = BaseAgentOutput(content="Não Fornecido", sentiment="NEUTRAL", confidence=0),
    technical_analysis: BaseAgentOutput = BaseAgentOutput(content="Não Fornecido", sentiment="NEUTRAL", confidence=0),
) -> BaseAgentOutput:
    today = datetime.date.today()
    year_start = today.year - 5
    year_end = today.year

    stock_details = stocks.details(ticker)
    company_name = stocks.name(ticker)
    segment = stocks.details(ticker).get('segmento_de_atuacao', 'nan')
    multiples = stocks.multiples(ticker)
    lastest_multiples = multiples[0] if multiples else {}
    dre_year = stocks.income_statement(ticker, year_start, year_end, 'year')
    calc_cagr(dre_year, 'receita_liquida', 5)
    calc_cagr(dre_year, 'lucro_liquido', 5)

    _dividends_by_year = stocks.dividends_by_year(ticker)
    if _dividends_by_year:
        dividends_growth_by_year = (
            pl.DataFrame(_dividends_by_year)
            .sort('ano')
            .with_columns(valor=pl.col('valor').pct_change().round(4))
            .drop_nulls()
            .to_dicts()
        )
        [d for d in _dividends_by_year if d['ano'] < today.year]
        dividends_growth_by_year = [d for d in dividends_growth_by_year if d['ano'] < today.year]
    else:
        dividends_growth_by_year = []

    balance_sheet_quarter = stocks.balance_sheet(ticker, year_start, year_end, 'quarter')
    df_balance = pl.DataFrame(balance_sheet_quarter) if balance_sheet_quarter else None
    
    ncav_status = "Desconhecido"
    if df_balance is not None and "ativo_circulante" in df_balance.columns and "passivo_circulante" in df_balance.columns:
        ativo_circ = df_balance["ativo_circulante"][0]
        passivo_circ = df_balance["passivo_circulante"][0]
        passivo_nao_circ = df_balance.get_column("passivo_nao_circulante")[0] if "passivo_nao_circulante" in df_balance.columns else 0
        total_passivo = passivo_circ + passivo_nao_circ
        
        ncav = ativo_circ - total_passivo
        ncav_status = f"O NCAV atual estimado bruto da companhia é {ncav:,.0f} BRL"

    classic_criteria = {
        'valor_de_mercado': f'{stock_details.get("valor_de_mercado", float("nan")):,.0f} BRL',
        'preco_sobre_lucro': lastest_multiples.get('p_l', float('nan')),
        'preco_sobre_lucro_abaixo_15x': lastest_multiples.get('p_l', float('nan')) < 15,
        'preco_sobre_valor_patrimonial': lastest_multiples.get('p_vp', float('nan')),
        'preco_sobre_valor_patrimonial_abaixo_1.5x': lastest_multiples.get('p_vp', float('nan')) < 1.5,
        'divida_bruta': stock_details.get('divida_bruta', float('nan')),
        'patrimonio_liquido': stock_details.get('patrimonio_liquido', float('nan')),
        'divida_menor_que_patrimonio_liquido': stock_details.get('divida_liquida', float('nan'))
        < stock_details.get('patrimonio_liquido', float('nan') + 1),
        'calculo_ncav_graham_puro': ncav_status,
        'lucro_liquido_positivo_nos_ultimos_5_anos': all([d.get('lucro_liquido', 0) > 0 for d in dre_year]),
    }

    prompt = dedent(f"""
    Dado o contexto, analise a empresa abaixo prestando extrema atenção no NCAV (cálculo fixo de Ativos Circ Totais subtraídos dos Passivos e Dívidas Totais).
    Nome: {company_name}
    Ticker: {ticker}
    Setor: {segment}

    ## OPINIÃO DO ANALISTA SOBRE O ÚLTIMO EARNINGS RELEASE
    Sentimento: {earnings_release_analysis.sentiment}
    Confiança: {earnings_release_analysis.confidence}
    Análise: {earnings_release_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE OS DADOS FINANCEIROS DA EMPRESA
    Sentimento: {financial_analysis.sentiment}
    Confiança: {financial_analysis.confidence}
    Análise: {financial_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE O VALUATION DA EMPRESA
    Sentimento: {valuation_analysis.sentiment}
    Confiança: {valuation_analysis.confidence}
    Análise: {valuation_analysis.content}

    ## OPINIÃO DO ANALISTA SOBRE AS NOTÍCIAS DA EMPRESA
    Sentimento: {news_analysis.sentiment}
    Confiança: {news_analysis.confidence}
    Análise: {news_analysis.content}

    ## MACROECONOMIA E CUSTO DE OPORTUNIDADE
    {macro_analysis.content}

    ## CONDIÇÕES GRÁFICAS E MÉDIAS MÓVEIS
    {technical_analysis.content}

    ## DADOS FINANCEIROS DISPONÍVEIS
    {dre_year}

    ## CRITÉRIOS CLÁSSICOS CALCULADOS
    {classic_criteria}
    """)

    agent = Agent(
        model=get_model(),
        system_message=SYSTEM_PROMPT,
        instructions=INSTRUCTIONS,
        tools=[ReasoningTools(think=True, analyze=True)],
        response_model=BaseAgentOutput,
        retries=3,
    )
    r = agent.run(f"Data de Hoje: {today.isoformat()}\n\n" + prompt)
    return r.content
