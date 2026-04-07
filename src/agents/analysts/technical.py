from agno.agent import Agent
from agno.tools.mcp import MCPTools

from src.agents.base import BaseAgentOutput
from src.utils import get_model

def analyze(ticker: str) -> BaseAgentOutput:
    prompt = f"""
    Você é um analista técnico quantitativo especializado em mercado de ações.
    Sua tarefa é analisar o comportamento dos preços e padrões da empresa {ticker}.
    USANDO ESTRITAMENTE as suas ferramentas conectadas ativamente via servidor MCP, chame as funções:
    - calculate_rsi
    - analyze_macd
    - analyze_moving_averages
    
    ## OBJETIVO
    Obtenha os dados via ferramentas e crie um laudo de Análise Técnica identificando o momento gráfico (Compra, Venda ou Neutro).
    NUNCA fabrique dados irreais ou imagine valores.
    
    ## FORMATO DE RESPOSTA
    Desenvolva um Markdown sucinto destacando:
    1. A posição das médias móveis.
    2. O status do Força Relativa (I.F.R / RSI).
    3. A divergência atual do MACD.
    4. Um veredito sumarizado final apontando o sinal unificado indicando 'Overbought', 'Oversold', etc.
    
    Sua resposta DEVE ser retornada no formato JSON encapsulado em BaseAgentOutput, com:
    - content: Markdown do resumo
    - sentiment: (BULLISH, BEARISH ou NEUTRAL)
    - confidence: grau de certeza baseado na convergência dos 3 indicadores (int de 0 a 100).
    """
    
    try:
        # Orquestração do InvestMCP Submodule via stdio transport no ambiente ativo
        technical_mcp_toolkit = MCPTools(
            command="python",
            args=["mcp_servers/investmcp/technical_analysis.py"]
        )
        
        agent = Agent(
            system_message=prompt,
            model=get_model(temperature=0.0),
            response_model=BaseAgentOutput,
            tools=[technical_mcp_toolkit],
            show_tool_calls=False,
            retries=3,
        )
        
        response = agent.run(f"Realize a análise técnica sistêmica usando todas as ferramentas ao seu dispor para o Ticker: {ticker}.")
        return response.content
        
    except Exception as e:
        print(f"Erro Crítico de Inicialização no Submódulo MCP Técnico: {e}")
        return BaseAgentOutput(content=f"Erro de MCP Técnico Inoperante: {e}", sentiment="NEUTRAL", confidence=0)

