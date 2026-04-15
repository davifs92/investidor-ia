from __future__ import annotations

from src.agents.base import BaseAgentOutput
from . import barsi, buffett, graham, lynch
from src.portfolio.models import PortfolioAnalysisOutput
from src.portfolio.persona_interface import build_portfolio_persona_input

_EMPTY = BaseAgentOutput(content='Não Fornecido', sentiment='NEUTRAL', confidence=0)


def consolidate_portfolio_by_persona(persona: str, output: PortfolioAnalysisOutput) -> str:
    persona_key = (persona or '').strip().lower()
    portfolio_data = build_portfolio_persona_input(output=output, persona=persona_key)

    kwargs = {
        'analysis_mode': 'portfolio',
        'portfolio_data': portfolio_data,
        'ticker': 'PORTFOLIO',
        'earnings_release_analysis': _EMPTY,
        'financial_analysis': _EMPTY,
        'valuation_analysis': _EMPTY,
        'news_analysis': _EMPTY,
        'macro_analysis': _EMPTY,
        'technical_analysis': _EMPTY,
    }

    if persona_key == 'buffett':
        result = buffett.analyze(**kwargs)
    elif persona_key == 'graham':
        result = graham.analyze(**kwargs)
    elif persona_key == 'barsi':
        result = barsi.analyze(**kwargs)
    elif persona_key == 'lynch':
        result = lynch.analyze(**kwargs)
    else:
        raise ValueError(f'Persona não suportada para portfólio: {persona}')

    return result.content


__all__ = [
    'barsi',
    'buffett',
    'graham',
    'lynch',
    'consolidate_portfolio_by_persona',
]
