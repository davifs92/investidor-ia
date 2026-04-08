from agno.agent import Agent
from agno.tools.mcp import MCPTools

from src.agents.base import BaseAgentOutput
from src.utils import get_model

def analyze(ticker: str) -> BaseAgentOutput:
    system_message = f"""
    Você é um Analista Técnico Quantitativo especialista.
    Sua tarefa é extrair e interpretar dados dos indicadores nativos RSI, MACD e Médias Móveis.
    USANDO ESTRITAMENTE as suas ferramentas conectadas ao MCP, obetenha os valores reais para o Ticker: {ticker}.

    ## OBJETIVO E FORMATO DE RESPOSTA
    Desenvolva um Markdown sucinto destacando:
    1. A posição atual das médias móveis.
    2. O status de Força Relativa (sobrecomprado/sobrevendido).
    3. A divergência atual do MACD.
    4. Veredito final ('Overbought', 'Oversold', etc).

    NUNCA fabrique dados irreais. Use sempre as ferramentas.
    """
    
    import datetime
    today = datetime.date.today().isoformat()
    try:
        # Orquestração do InvestMCP Submodule via stdio transport no ambiente ativo
        technical_mcp_toolkit = MCPTools(
            command="python",
            args=["mcp_servers/investmcp/technical_analysis.py"]
        )
        
        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.0),
            response_model=BaseAgentOutput,
            tools=[technical_mcp_toolkit],
            show_tool_calls=False,
            retries=3,
        )
        
        response = agent.run(f"Data Base: {today}\n\nRealize a análise técnica sistêmica usando todas as ferramentas ao seu dispor para o Ticker: {ticker}.")
        return response.content
        
    except Exception as e:
        print(f"Erro Crítico de Inicialização no Submódulo MCP Técnico: {e}")
        return BaseAgentOutput(content=f"Erro de MCP Técnico Inoperante: {e}", sentiment="NEUTRAL", confidence=0)

