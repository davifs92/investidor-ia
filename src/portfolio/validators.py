from src.portfolio.models import PortfolioAnalysisInput, SupportedMarket


VALID_MARKETS: set[SupportedMarket] = {'BR', 'US'}


class PortfolioValidationError(ValueError):
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__('; '.join(errors))


def validate_portfolio_input(data: PortfolioAnalysisInput, max_assets: int = 20) -> list[str]:
    errors: list[str] = []
    warnings: list[str] = []

    if not data.items:
        errors.append('Carteira vazia: adicione pelo menos um ativo.')
        raise PortfolioValidationError(errors)

    total_weight = 0.0
    for idx, item in enumerate(data.items, start=1):
        ticker = item.ticker.strip() if item.ticker else ''
        if not ticker:
            errors.append(f'Ativo #{idx} sem ticker informado.')

        if item.market not in VALID_MARKETS:
            errors.append(f"Ativo '{ticker or idx}' com mercado inválido: {item.market}. Use BR ou US.")

        if item.weight < 0:
            errors.append(f"Ativo '{ticker or idx}' com peso negativo: {item.weight}.")

        total_weight += item.weight

    if total_weight <= 0:
        errors.append('Soma total de pesos deve ser maior que zero.')

    if len(data.items) > max_assets:
        warnings.append(
            f'Carteira com {len(data.items)} ativos. Limite recomendado é {max_assets}; a análise pode demorar mais.'
        )

    if errors:
        raise PortfolioValidationError(errors)

    return warnings
