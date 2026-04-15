from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from uuid import uuid4

from src.portfolio.models import PortfolioAnalysisInput, PortfolioAnalysisOutput, PortfolioItem
from src.settings import DB_DIR


def _portfolio_reports_file() -> Path:
    path = Path(DB_DIR) / 'portfolio_reports.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('[]')
    return path


def _portfolios_file() -> Path:
    path = Path(DB_DIR) / 'portfolios.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text('[]')
    return path


def _read_list(path: Path) -> list[dict]:
    if not path.exists():
        return []
    content = path.read_text().strip()
    if not content:
        return []
    data = json.loads(content)
    return data if isinstance(data, list) else []


def _write_list(path: Path, data: list[dict]):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def list_portfolio_reports() -> list[dict]:
    reports = _read_list(_portfolio_reports_file())
    return sorted(reports, key=lambda x: str(x.get('generated_at', '')), reverse=True)


def get_portfolio_report(report_id: str) -> dict | None:
    for report in list_portfolio_reports():
        if str(report.get('id')) == report_id:
            return report
    return None


def save_portfolio_report(
    analysis_input: PortfolioAnalysisInput,
    analysis_output: PortfolioAnalysisOutput,
    portfolio_name: str | None = None,
    portfolio_id: str | None = None,
) -> dict:
    now = dt.datetime.now().isoformat()
    report = {
        'id': str(uuid4()),
        'generated_at': now,
        'portfolio_name': portfolio_name or 'Portfólio sem nome',
        'portfolio_id': portfolio_id,
        'objective': analysis_input.objective,
        'persona': analysis_input.persona,
        'reference_currency': analysis_input.reference_currency,
        'assets_count': len(analysis_input.items),
        'items': [item.model_dump(mode='json') for item in analysis_input.items],
        'overall_score': float(analysis_output.overall_score or 0.0),
        'portfolio_sentiment': analysis_output.portfolio_sentiment,
        'data': analysis_output.model_dump(mode='json'),
    }
    reports = _read_list(_portfolio_reports_file())
    reports.append(report)
    _write_list(_portfolio_reports_file(), reports)
    return report


def list_saved_portfolios() -> list[dict]:
    portfolios = _read_list(_portfolios_file())
    return sorted(portfolios, key=lambda x: str(x.get('updated_at', '')), reverse=True)


def get_saved_portfolio(portfolio_id: str) -> dict | None:
    for portfolio in list_saved_portfolios():
        if str(portfolio.get('id')) == portfolio_id:
            return portfolio
    return None


def save_portfolio_composition(
    name: str,
    items: list[dict] | list[PortfolioItem],
    objective: str = 'equilibrio',
    persona: str | None = None,
    reference_currency: str = 'BRL',
    portfolio_id: str | None = None,
) -> dict:
    normalized_items: list[dict] = []
    for item in items:
        if isinstance(item, PortfolioItem):
            normalized_items.append(item.model_dump(mode='json'))
        else:
            normalized_items.append(dict(item))

    if not name or not name.strip():
        raise ValueError('Nome do portfólio é obrigatório.')

    now = dt.datetime.now().isoformat()
    portfolios = _read_list(_portfolios_file())

    if portfolio_id:
        for idx, portfolio in enumerate(portfolios):
            if str(portfolio.get('id')) == portfolio_id:
                updated = dict(portfolio)
                updated['name'] = name.strip()
                updated['items'] = normalized_items
                updated['objective'] = objective
                updated['persona'] = persona
                updated['reference_currency'] = reference_currency
                updated['updated_at'] = now
                portfolios[idx] = updated
                _write_list(_portfolios_file(), portfolios)
                return updated

    created = {
        'id': str(uuid4()),
        'name': name.strip(),
        'items': normalized_items,
        'objective': objective,
        'persona': persona,
        'reference_currency': reference_currency,
        'created_at': now,
        'updated_at': now,
        'last_analyzed_at': None,
    }
    portfolios.append(created)
    _write_list(_portfolios_file(), portfolios)
    return created


def duplicate_saved_portfolio(portfolio_id: str, new_name: str) -> dict:
    source = get_saved_portfolio(portfolio_id)
    if source is None:
        raise ValueError('Portfólio não encontrado para duplicação.')
    return save_portfolio_composition(
        name=new_name,
        items=list(source.get('items', [])),
        objective=str(source.get('objective', 'equilibrio')),
        persona=source.get('persona'),
        reference_currency=str(source.get('reference_currency', 'BRL')),
        portfolio_id=None,
    )


def delete_saved_portfolio(portfolio_id: str) -> bool:
    portfolios = _read_list(_portfolios_file())
    remaining = [p for p in portfolios if str(p.get('id')) != portfolio_id]
    if len(remaining) == len(portfolios):
        return False
    _write_list(_portfolios_file(), remaining)
    return True


def mark_portfolio_analyzed(portfolio_id: str):
    portfolios = _read_list(_portfolios_file())
    now = dt.datetime.now().isoformat()
    changed = False
    for idx, portfolio in enumerate(portfolios):
        if str(portfolio.get('id')) == portfolio_id:
            updated = dict(portfolio)
            updated['last_analyzed_at'] = now
            updated['updated_at'] = now
            portfolios[idx] = updated
            changed = True
            break
    if changed:
        _write_list(_portfolios_file(), portfolios)
