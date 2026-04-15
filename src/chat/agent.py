from textwrap import dedent

from agno.agent import Agent
from agno.storage.sqlite import SqliteStorage
from agno.memory.v2.memory import Memory
from agno.memory.v2.db.sqlite import SqliteMemoryDb
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.reasoning import ReasoningTools

from src.utils import get_model
from src.chat.tools import StocksTools
from src.settings import DB_DIR
from src.agents.investors.barsi import SYSTEM_PROMPT as barsi_system_prompt
from src.agents.investors.buffett import SYSTEM_PROMPT as buffet_system_prompt
from src.agents.investors.graham import SYSTEM_PROMPT as graham_system_prompt

# Banco de dados separados para evitar conflitos de Schema no SQLite
storage = SqliteStorage(table_name='chat_agent_storage', db_file=DB_DIR / 'chat_storage.db')
memory = Memory(
    model=get_model(),
    db=SqliteMemoryDb(table_name='chat_agent_memory', db_file=DB_DIR / 'chat_memory.db'),
)


def get_chat_agent(investor: str, market: str | None = None) -> Agent:
    match investor:
        case 'buffett':
            system_prompt = buffet_system_prompt
        case 'barsi':
            system_prompt = barsi_system_prompt
        case 'graham':
            system_prompt = graham_system_prompt
        case _:
            raise ValueError(f'Investor {investor} not found')

    market_context = f"O mercado selecionado pelo usuário é: {market}. Priorize busca de dados neste mercado." if market else ""

    return Agent(
        model=get_model(temperature=0.5),
        system_message=system_prompt,
        instructions=dedent(
            f"""
            {market_context}
            Comece analisando a pergunta do usuário e veja se você pode responder com os dados disponíveis.
            Se precisar de mais dados, use as funções disponíveis. Elas devem ser usadas para obter os dados necessários e responder ao usuário.
            Você tem acesso livre aos dados das ações e ao uso das funções disponíveis, se aproveite delas para responder ao usuário.
            Caso você use alguma função disponível, não informe ao usuário que você usou uma função, apenas responda a pergunta.
            """
        ),
        tools=[ReasoningTools(think=True, analyze=True), StocksTools(market=market), DuckDuckGoTools()],
        show_tool_calls=True,
        storage=storage,
        memory=memory,
        enable_agentic_memory=True,
        enable_user_memories=True,
        add_history_to_messages=True,
        num_history_runs=20,
        markdown=True,
    )
