import yfinance as yf
import pandas as pd
import time
import threading
from typing import Literal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

from src.cache import cache_it
from src.data_providers.base import BaseDataProvider
from src.data_providers.us.sec_edgar import sec_client

YF_TIMEOUT = 20  # Aumentado para 20s para maior tolerância em rede lenta
YF_MAX_RETRIES = 3
YF_RATE_LIMIT_COOLDOWN_SECONDS = 60
YF_MIN_INTERVAL_SECONDS = 1.0
_yf_rate_limited_until = 0.0
_yf_next_allowed_at = 0.0
_yf_rate_lock = threading.Lock()


def _is_rate_limited_error(message: str) -> bool:
    lower = (message or '').lower()
    return 'too many requests' in lower or 'rate limit' in lower


def _activate_yf_cooldown(seconds: int = YF_RATE_LIMIT_COOLDOWN_SECONDS):
    global _yf_rate_limited_until, _yf_next_allowed_at
    with _yf_rate_lock:
        until = time.time() + max(1, int(seconds))
        _yf_rate_limited_until = max(_yf_rate_limited_until, until)
        _yf_next_allowed_at = max(_yf_next_allowed_at, _yf_rate_limited_until)


def _wait_for_yf_slot(fn_name: str):
    global _yf_next_allowed_at
    while True:
        with _yf_rate_lock:
            now = time.time()
            wait_for_cooldown = max(0.0, _yf_rate_limited_until - now)
            wait_for_interval = max(0.0, _yf_next_allowed_at - now)
            wait_seconds = max(wait_for_cooldown, wait_for_interval)
            if wait_seconds <= 0:
                _yf_next_allowed_at = now + YF_MIN_INTERVAL_SECONDS
                return
        remaining = int(wait_seconds)
        print(f'[USDataProvider] yfinance em cooldown ({remaining}s restantes). Aguardando chamada {fn_name}.')
        time.sleep(min(wait_seconds, 2.0))

def _yf_call(fn, *args, **kwargs):
    """Executa uma função do yfinance com timeout para evitar travamentos de rede."""
    fn_name = getattr(fn, '__name__', repr(fn))

    for attempt in range(1, YF_MAX_RETRIES + 1):
        _wait_for_yf_slot(fn_name)
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(fn, *args, **kwargs)
            try:
                return future.result(timeout=YF_TIMEOUT)
            except FuturesTimeoutError:
                print(f'[USDataProvider] Timeout (>{YF_TIMEOUT}s) em {fn_name} [tentativa {attempt}/{YF_MAX_RETRIES}]')
            except Exception as e:
                message = str(e)
                print(f'[USDataProvider] Erro em {fn_name} [tentativa {attempt}/{YF_MAX_RETRIES}]: {message}')
                if _is_rate_limited_error(message):
                    _activate_yf_cooldown()
                else:
                    return None

        if attempt < YF_MAX_RETRIES:
            time.sleep(min(2 ** (attempt - 1), 4))
    return None


class USDataProvider(BaseDataProvider):
    """Provedor de dados para o mercado Americano (NYSE/NASDAQ). Utiliza yfinance sob o capô, normalizando as métricas para português."""

    @cache_it
    def details(self, ticker: str) -> dict:
        try:
            tk = yf.Ticker(ticker)
            info = _yf_call(lambda: tk.info)
            
            # Tenta pegar preço de múltiplas fontes
            price = None
            if info and isinstance(info, dict):
                price = info.get('regularMarketPrice') or info.get('currentPrice')
            
            if price is None:
                try:
                    price = tk.fast_info.last_price
                except:
                    try:
                        hist = _yf_call(lambda: tk.history(period="5d"))
                        if hist is not None and not hist.empty:
                            price = hist['Close'].iloc[-1]
                    except:
                        price = 0.0

            if not info or not isinstance(info, dict):
                return {
                    'nome': ticker, 
                    'segmento_de_atuacao': 'N/A', 
                    'preco': float(price) if price else 0.0,
                    'descricao': 'Dados detalitados indisponíveis no momento (Timeout Yahoo).'
                }
                
            return {
                'nome': info.get('longName', ticker),
                'segmento_de_atuacao': info.get('sector', 'N/A'),
                'preco': float(price) if price else 0.0,
                'descricao': info.get('longBusinessSummary', '')
            }
        except Exception:
            return {'nome': ticker, 'segmento_de_atuacao': 'N/A', 'descricao': 'Erro ao buscar dados no Yahoo Finance.'}

    @cache_it
    def name(self, ticker: str) -> str:
        return self.details(ticker)['nome']

    def _normalize_df(self, df: pd.DataFrame, mapping: dict) -> list[dict]:
        if df is None or df.empty:
            return []
            
        result = []
        for col in df.columns:
            period_data = df[col].to_dict()
            mapped = {'data': col.strftime('%Y-%m-%d')} if hasattr(col, 'strftime') else {'data': str(col)}
            for pt_key, eng_key in mapping.items():
                val = period_data.get(eng_key, 0.0)
                mapped[pt_key] = float(val) if not pd.isna(val) else 0.0
            result.append(mapped)
            
        return sorted(result, key=lambda x: x['data'], reverse=True)

    @cache_it
    def income_statement(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> list[dict]:
        try:
            financials = sec_client.get_financials(ticker)
            if not financials:
                return []
            
            # Filtra por form (10-K para anual, 10-Q para trimestral)
            target_form = '10-K' if period == 'annual' else '10-Q'
            
            # Agrupa dados por data final (end date)
            metrics = ['receita_liquida', 'lucro_liquido', 'ebit']
            data_by_date = {}
            
            for m in metrics:
                entries = financials.get(m, [])
                for entry in entries:
                    if entry['form'] == target_form:
                        d = entry['data']
                        if d not in data_by_date: data_by_date[d] = {'data': d}
                        data_by_date[d][m] = entry['valor']

            result = list(data_by_date.values())
            # Ordena decrescente
            result.sort(key=lambda x: x['data'], reverse=True)
            return result
        except Exception as e:
            print(f'[USDataProvider] Erro ao buscar income_statement via EDGAR ({ticker}): {e}')
            return []

    @cache_it
    def balance_sheet(
        self,
        ticker: str,
        year_start: int | None = None,
        year_end: int | None = None,
        period: Literal['annual', 'quarter'] = 'annual',
    ) -> list[dict]:
        try:
            financials = sec_client.get_financials(ticker)
            if not financials: return []
            
            target_form = '10-K' if period == 'annual' else '10-Q'
            metrics = ['ativo_total', 'patrimonio_liquido', 'caixa', 'divida']
            data_by_date = {}
            
            for m in metrics:
                entries = financials.get(m, [])
                for entry in entries:
                    if entry['form'] == target_form:
                        d = entry['data']
                        if d not in data_by_date: data_by_date[d] = {'data': d}
                        data_by_date[d][m] = entry['valor']

            # Normaliza campos extras esperados pelo analista
            for d in data_by_date.values():
                d['divida_bruta'] = d.get('divida', 0.0)
                d['caixa_equivalentes'] = d.get('caixa', 0.0)

            result = list(data_by_date.values())
            result.sort(key=lambda x: x['data'], reverse=True)
            return result
        except Exception as e:
            print(f'[USDataProvider] Erro ao buscar balance_sheet via EDGAR ({ticker}): {e}')
            return []

    @cache_it
    def cash_flow(
        self, 
        ticker: str, 
        year_start: int | None = None, 
        year_end: int | None = None
    ) -> list[dict]:
        try:
            financials = sec_client.get_financials(ticker)
            if not financials: return []
            
            # SEC reports Cash Flow mostly in 10-K/10-Q
            target_form = '10-K' # Annual
            metrics = ['fco', 'fci', 'fcf_raw', 'capex']
            data_by_date = {}
            
            for m in metrics:
                entries = financials.get(m, [])
                for entry in entries:
                    if entry['form'] == target_form:
                        d = entry['data']
                        if d not in data_by_date: data_by_date[d] = {'data': d}
                        data_by_date[d][m] = entry['valor']

            # Calcula Fluxo de Caixa Livre: FCF = FCO - Capex
            for d in data_by_date.values():
                d['fc_livre'] = d.get('fco', 0.0) - abs(d.get('capex', 0.0))
                # Renomeia para padrão esperado
                d['fcf'] = d.get('fcf_raw', 0.0)

            result = list(data_by_date.values())
            result.sort(key=lambda x: x['data'], reverse=True)
            return result
        except Exception as e:
            print(f'[USDataProvider] Erro ao buscar cash_flow via EDGAR ({ticker}): {e}')
            return []

    @cache_it
    def multiples(self, ticker: str) -> list[dict]:
        try:
            tk = yf.Ticker(ticker)
            info = _yf_call(lambda: tk.info)
            
            # Tenta pegar preço de múltiplas fontes se info falhar
            price = None
            if info and isinstance(info, dict):
                price = info.get('regularMarketPrice') or info.get('currentPrice')
            
            if price is None:
                # Tenta fast_info (mais leve)
                try:
                    price = tk.fast_info.last_price
                except:
                    # Último recurso: history
                    try:
                        hist = _yf_call(lambda: tk.history(period="5d"))
                        if hist is not None and not hist.empty:
                            price = hist['Close'].iloc[-1]
                    except:
                        price = 0.0

            # Mesmo se info falhar (timeout), retornamos o preço para evitar 'nan' na análise
            if not info or not isinstance(info, dict):
                return [{
                    'ano': 'LTM (Preço apenas)',
                    'preco_atual': float(price) if price else 0.0,
                    'p_l': 0.0,
                    'p_vp': 0.0,
                    'dy': 0.0,
                    'roe': 0.0,
                    'margem_liquida': 0.0,
                    'ev_ebitda': 0.0
                }]
                
            return [{
                'ano': 'LTM',
                'preco_atual': float(price) if price else 0.0,
                'p_l': info.get('trailingPE', 0.0) or 0.0,
                'p_vp': info.get('priceToBook', 0.0) or 0.0,
                'dy': info.get('trailingAnnualDividendYield', 0.0) or 0.0,
                'roe': info.get('returnOnEquity', 0.0) or 0.0,
                'margem_liquida': info.get('profitMargins', 0.0) or 0.0,
                'ev_ebitda': info.get('enterpriseToEbitda', 0.0) or 0.0
            }]
        except Exception as e:
            print(f'[USDataProvider] Erro ao buscar multiples ({ticker}): {e}')
            return []

    @cache_it
    def dividends(self, ticker: str) -> list[dict]:
        try:
            tk = yf.Ticker(ticker)
            divs = _yf_call(lambda: tk.dividends)
            if divs is None or divs.empty:
                return []
            result = []
            for date, value in divs.items():
                result.append({'data_pagamento': date.strftime('%Y-%m-%d'), 'valor': float(value)})
            return sorted(result, key=lambda x: x['data_pagamento'], reverse=True)
        except Exception:
            return []

    @cache_it
    def dividends_by_year(self, ticker: str) -> list[dict]:
        divs = self.dividends(ticker)
        yearly = {}
        for d in divs:
            y = int(d['data_pagamento'][:4])
            yearly[y] = yearly.get(y, 0.0) + d['valor']
        return [{'ano': y, 'valor': round(v, 4)} for y, v in sorted(yearly.items(), key=lambda x: x[0])]

    @cache_it
    def screener(self):
        return []

    @cache_it
    def payouts(self, ticker: str) -> list[dict]:
        return []

    @cache_it
    def news(self, ticker: str) -> list[dict]:
        try:
            tk = yf.Ticker(ticker)
            yf_news = _yf_call(lambda: tk.news)
            if not yf_news:
                return []
            
            result = []
            for item in yf_news[:10]:
                # Suporta novo formato: item['content'] é um dict aninhado
                content_block = item.get('content', {})
                if isinstance(content_block, dict):
                    title = content_block.get('title', '') or item.get('title', '')
                    url = ''
                    canonical = content_block.get('canonicalUrl', {})
                    if isinstance(canonical, dict):
                        url = canonical.get('url', '')
                    if not url:
                        url = content_block.get('url', '') or item.get('link', '')
                    summary = content_block.get('summary', '') or title
                    publisher = content_block.get('provider', {}).get('displayName', '') if isinstance(content_block.get('provider'), dict) else item.get('publisher', '')
                else:
                    # Formato antigo (fallback)
                    title = item.get('title', '')
                    url = item.get('link', '')
                    summary = item.get('body', title)
                    publisher = item.get('publisher', '')
                
                # Filtra itens sem título (placeholders vazios)
                if not title or not url:
                    continue
                    
                result.append({
                    'title': title,
                    'url': url,
                    'body': publisher,
                    'content': summary,
                })
            return result
        except Exception as e:
            print(f'[USDataProvider] Erro ao buscar news ({ticker}): {e}')
            return []

    @cache_it
    def earnings_release(self, ticker: str) -> str:
        """Busca o contexto do último relatório de resultados via SEC EDGAR."""
        try:
            cik = sec_client.get_cik(ticker)
            if not cik: return "Dados de Earnings indisponíveis (CIK não encontrado)."
            
            # Busca submissões recentes
            subs = sec_client.get_submissions(cik)
            filings = subs.get('filings', {}).get('recent', {})
            
            # Localiza o último 10-Q (Trimestral) ou 10-K (Anual)
            forms = filings.get('form', [])
            target_idx = -1
            for i, f in enumerate(forms):
                if f in ['10-Q', '10-K']:
                    target_idx = i
                    break
            
            if target_idx == -1:
                return "Nenhum relatório 10-Q ou 10-K recente encontrado no EDGAR."
                
            report_date = filings.get('reportDate', [])[target_idx]
            report_type = forms[target_idx]
            accession = filings.get('accessionNumber', [])[target_idx]
            
            # Busca dados financeiros para comparação
            financials = sec_client.get_financials(ticker)
            net_income = financials.get('lucro_liquido', [])
            revenue = financials.get('receita_liquida', [])
            
            summary = f"Último relatório oficial: {report_type} protocolado em {report_date}.\n"
            summary += f"Número de Acesso SEC: {accession}\n\n"
            
            if len(net_income) >= 2:
                curr = net_income[0]['valor']
                prev = net_income[1]['valor']
                growth = ((curr / prev) - 1) * 100 if prev != 0 else 0
                summary += f"- Lucro Líquido Recente: ${curr:,.0f} (vs ${prev:,.0f} no período anterior, variação de {growth:.1f}%)\n"
                
            if len(revenue) >= 2:
                curr = revenue[0]['valor']
                prev = revenue[1]['valor']
                growth = ((curr / prev) - 1) * 100 if prev != 0 else 0
                summary += f"- Receita Recente: ${curr:,.0f} (vs ${prev:,.0f} no período anterior, variação de {growth:.1f}%)\n"
            
            summary += "\nContexto adicional: O relatório completo pode ser consultado no portal EDGAR da SEC usando o número de acesso citado."
            return summary
            
        except Exception as e:
            print(f"[USDataProvider] Erro ao processar earnings_release ({ticker}): {e}")
            return "Erro ao extrair dados de Earnings da SEC."

    def earnings_release_pdf_path(self, ticker: str) -> str:
        """
        No mercado americano (SEC EDGAR), os relatórios são primariamente HTML/XBRL.
        O download direto de PDF não está implementado nesta versão.
        """
        raise NotImplementedError("Download de PDF de Earnings Release para o mercado americano (SEC) ainda não disponível. Use a análise baseada em dados (EDGAR API).")
