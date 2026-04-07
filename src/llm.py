"""
Wrapper de conven\u00eancia para chamadas diretas ao LLM via framework Agno.

Utiliza get_model() de src/utils.py para abstra\u00e7\u00e3o agn\u00f3stica de provider
(Google Gemini, OpenAI, OpenRouter), conforme configurado nas settings do usu\u00e1rio.

Nota: os agentes anal\u00edticos (analysts/) e investidores (investors/) usam
o Agno Agent diretamente. Este m\u00f3dulo serve como wrapper de conven\u00eancia
para chamadas pontuais que n\u00e3o justificam a instancia\u00e7\u00e3o de um Agent completo.
"""
from typing import TypeVar

from agno.agent import Agent
from pydantic import BaseModel

from src.utils import get_model


T = TypeVar('T', bound=BaseModel)


def ask(
    message: str,
    temperature: float = 0.8,
    response_model: type[T] | None = None,
) -> str | T:
    """
    Envia uma mensagem ao LLM configurado e retorna a resposta.

    O parse estruturado para Pydantic \u00e9 delegado integralmente ao Agno
    via response_model \u2014 sem manipula\u00e7\u00e3o manual de strings JSON.
    O retry em caso de falha de parse \u00e9 gerenciado pelo pr\u00f3prio Agent (retries=3).

    Args:
        message: O prompt a ser enviado ao modelo.
        temperature: Criatividade da resposta (0.0 \u2013 1.0). Default 0.8.
        response_model: Classe Pydantic para parse estruturado do output.
                        Se None, retorna a resposta como string plain.

    Returns:
        Inst\u00e2ncia de response_model se especificado, caso contr\u00e1rio str.

    Raises:
        ValueError: Se a API key ou o provider n\u00e3o estiverem configurados.
        Exception: Se o modelo falhar ap\u00f3s os retries internos do Agno.
    """
    agent = Agent(
        model=get_model(temperature=temperature),
        response_model=response_model,
        retries=3,
    )
    response = agent.run(message)
    return response.content
