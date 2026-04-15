import datetime
import os
import random
import threading
import time

import pandas as pd
import requests
import yfinance as yf
from agno.agent import Agent
from agno.tools.mcp import MCPTools
from decouple import config

from src.agents.base import BaseAgentOutput
from src.cache import cache
from src.utils import get_model


_NO_DATA_MARKERS = (
    'não consigo obter dados',
    'nao consigo obter dados',
    'não tenho acesso',
    'nao tenho acesso',
    'preciso que as ferramentas mcp estejam ativadas',
    'forneça os valores',
    'forneca os valores',
    'autorize',
)
_ALPHA_CACHE_TTL_SECONDS = 60 * 60 * 6  # 6 horas
_ALPHA_MAX_RETRIES = 3
_ALPHA_RETRY_SLEEP_SECONDS = 12
_ALPHA_RATE_LIMIT_COOLDOWN_SECONDS = 75
_alpha_rate_limited_until = 0.0
_alpha_rate_lock = threading.Lock()

_YF_CACHE_TTL_SECONDS = 60 * 30
_YF_MAX_RETRIES = 3
_YF_RETRY_BASE_SECONDS = 2
_YF_MIN_INTERVAL_SECONDS = 1.0
_YF_RATE_LIMIT_COOLDOWN_SECONDS = 60
_yf_rate_limited_until = 0.0
_yf_next_allowed_at = 0.0
_yf_rate_lock = threading.Lock()


def _normalize_ticker(ticker: str, market: str | None = None) -> str:
    ticker_up = ticker.upper().strip()
    if market == 'BR' and not ticker_up.endswith('.SA'):
        return f'{ticker_up}.SA'
    return ticker_up


def _needs_data_fallback(content: str) -> bool:
    text = str(content).lower()
    return any(marker in text for marker in _NO_DATA_MARKERS)


def _ema_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, pd.NA)
    return 100 - (100 / (1 + rs))


def _alpha_remaining_cooldown_seconds() -> int:
    with _alpha_rate_lock:
        remaining = int(_alpha_rate_limited_until - time.time())
    return max(0, remaining)


def _activate_alpha_cooldown(seconds: int = _ALPHA_RATE_LIMIT_COOLDOWN_SECONDS):
    global _alpha_rate_limited_until
    with _alpha_rate_lock:
        _alpha_rate_limited_until = max(_alpha_rate_limited_until, time.time() + max(1, int(seconds)))


def _is_yf_rate_limited_error(message: str) -> bool:
    lower = (message or '').lower()
    return 'too many requests' in lower or 'rate limit' in lower or 'yfratelimiterror' in lower


def _activate_yf_cooldown(seconds: int = _YF_RATE_LIMIT_COOLDOWN_SECONDS):
    global _yf_rate_limited_until, _yf_next_allowed_at
    with _yf_rate_lock:
        until = time.time() + max(1, int(seconds))
        _yf_rate_limited_until = max(_yf_rate_limited_until, until)
        _yf_next_allowed_at = max(_yf_next_allowed_at, _yf_rate_limited_until)


def _wait_for_yf_slot():
    global _yf_next_allowed_at
    while True:
        with _yf_rate_lock:
            now = time.time()
            wait_for_cooldown = max(0.0, _yf_rate_limited_until - now)
            wait_for_interval = max(0.0, _yf_next_allowed_at - now)
            wait_seconds = max(wait_for_cooldown, wait_for_interval)
            if wait_seconds <= 0:
                _yf_next_allowed_at = now + _YF_MIN_INTERVAL_SECONDS
                return
        time.sleep(min(wait_seconds, 2.0))


def _price_history_from_alpha_vantage(ticker: str) -> pd.Series:
    api_key = config('ALPHAVANTAGE_API_KEY', default=os.getenv('ALPHAVANTAGE_API_KEY', '')).strip()
    if not api_key:
        raise ValueError('ALPHAVANTAGE_API_KEY não configurada.')

    cache_key = f'technical_alpha_prices:{ticker}'
    cached = cache.get(cache_key, default=None)
    if isinstance(cached, pd.Series) and not cached.empty:
        return cached

    alpha_remaining = _alpha_remaining_cooldown_seconds()
    if alpha_remaining > 0:
        raise ValueError(f'Alpha Vantage em cooldown global ({alpha_remaining}s restantes).')

    # Prioriza endpoint gratuito; alguns planos tratam o adjusted como premium.
    endpoint_candidates = [
        ('TIME_SERIES_DAILY', ('4. close', '5. adjusted close')),
        ('TIME_SERIES_DAILY_ADJUSTED', ('5. adjusted close', '4. close')),
    ]

    last_error: Exception | None = None
    for function_name, close_keys in endpoint_candidates:
        for attempt in range(1, _ALPHA_MAX_RETRIES + 1):
            try:
                response = requests.get(
                    'https://www.alphavantage.co/query',
                    params={
                        'function': function_name,
                        'symbol': ticker,
                        'outputsize': 'full',
                        'apikey': api_key,
                    },
                    timeout=30,
                )
                response.raise_for_status()
                payload = response.json()

                if isinstance(payload, dict):
                    provider_error = payload.get('Error Message') or payload.get('Information') or payload.get('Note')
                    if provider_error:
                        message = str(provider_error)
                        lower = message.lower()
                        is_premium_block = 'premium endpoint' in lower
                        is_rate_limited = 'rate limit' in lower or 'frequency' in lower or 'too many' in lower

                        # Se for premium e estivermos no adjusted, tenta o próximo endpoint.
                        if is_premium_block and function_name == 'TIME_SERIES_DAILY_ADJUSTED':
                            last_error = ValueError(f'Alpha Vantage: {message}')
                            break

                        if is_rate_limited:
                            _activate_alpha_cooldown()
                            if attempt < _ALPHA_MAX_RETRIES:
                                time.sleep(_ALPHA_RETRY_SLEEP_SECONDS)
                                continue
                        raise ValueError(f'Alpha Vantage: {message}')

                raw_series = payload.get('Time Series (Daily)', {}) if isinstance(payload, dict) else {}
                if not raw_series and isinstance(payload, dict):
                    # fallback defensivo para formatos alternativos
                    ts_key = next((k for k in payload.keys() if k.startswith('Time Series')), None)
                    if ts_key:
                        raw_series = payload.get(ts_key, {})
                if not raw_series:
                    raise ValueError('Alpha Vantage retornou série diária vazia.')

                rows = []
                for day, values in raw_series.items():
                    try:
                        close_value = None
                        for key in close_keys:
                            if values.get(key) is not None:
                                close_value = float(values.get(key))
                                break
                        if close_value is None:
                            continue
                        rows.append((pd.to_datetime(day), close_value))
                    except Exception:
                        continue

                if not rows:
                    raise ValueError('Falha ao parsear preços do Alpha Vantage.')

                df = pd.DataFrame(rows, columns=['date', 'close']).sort_values('date').set_index('date')
                close = df['close'].dropna()
                if close.empty:
                    raise ValueError('Série de preços do Alpha Vantage está vazia após limpeza.')

                cache.set(cache_key, close, expire=_ALPHA_CACHE_TTL_SECONDS)
                return close
            except Exception as exc:
                last_error = exc
                if attempt < _ALPHA_MAX_RETRIES:
                    time.sleep(1)
                    continue
                break

    raise ValueError(f'Falha no Alpha Vantage para {ticker}: {last_error}')


def _price_history_from_yfinance(ticker: str) -> pd.Series:
    cache_key = f'technical_yf_prices:{ticker}'
    cached = cache.get(cache_key, default=None)
    if isinstance(cached, pd.Series) and not cached.empty:
        return cached

    last_error: Exception | None = None
    for attempt in range(1, _YF_MAX_RETRIES + 1):
        try:
            _wait_for_yf_slot()
            df = yf.download(ticker, period='1y', interval='1d', auto_adjust=False, progress=False, threads=False)
            if df is None or df.empty:
                raise ValueError('Histórico de preços vazio no yfinance.')
            close_col = 'Adj Close' if 'Adj Close' in df.columns else 'Close'
            close = df[close_col].dropna()
            if close.empty:
                raise ValueError('Série de preços vazia no yfinance.')
            cache.set(cache_key, close, expire=_YF_CACHE_TTL_SECONDS)
            return close
        except Exception as exc:
            last_error = exc
            message = str(exc)
            if _is_yf_rate_limited_error(message):
                _activate_yf_cooldown()
            if attempt < _YF_MAX_RETRIES:
                base_sleep = _YF_RETRY_BASE_SECONDS * attempt
                time.sleep(base_sleep + random.uniform(0, 0.75))
                continue
            break
    raise ValueError(f'Falha no yfinance para {ticker}: {last_error}')


def _load_price_history(ticker: str) -> tuple[pd.Series, str]:
    try:
        return _price_history_from_alpha_vantage(ticker), 'Alpha Vantage'
    except Exception as alpha_exc:
        print(f'[technical analyst] Falha no Alpha Vantage para {ticker}: {alpha_exc}')
        return _price_history_from_yfinance(ticker), 'yfinance'


def _build_fallback_analysis(ticker: str, market: str | None = None) -> BaseAgentOutput:
    ticker_data = _normalize_ticker(ticker, market=market)
    today = datetime.date.today().isoformat()
    try:
        close, source = _load_price_history(ticker_data)
        if close.empty or len(close) < 210:
            raise ValueError('Histórico insuficiente para calcular SMA200/RSI/MACD.')

        sma50 = close.rolling(window=50).mean()
        sma200 = close.rolling(window=200).mean()
        rsi14 = _ema_rsi(close, period=14)
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        macd = ema12 - ema26
        signal = macd.ewm(span=9, adjust=False).mean()
        hist = macd - signal

        price = float(close.iloc[-1])
        ma50 = float(sma50.iloc[-1])
        ma200 = float(sma200.iloc[-1])
        rsi = float(rsi14.iloc[-1])
        macd_now = float(macd.iloc[-1])
        signal_now = float(signal.iloc[-1])
        hist_now = float(hist.iloc[-1])
        macd_prev = float(macd.iloc[-2])
        signal_prev = float(signal.iloc[-2])
        data_date = close.index[-1].date().isoformat()

        if price > ma50 > ma200:
            ma_status = 'Bullish (preço acima da SMA50 e SMA50 acima da SMA200).'
            ma_signal = 'BULLISH'
        elif price < ma50 < ma200:
            ma_status = 'Bearish (preço abaixo da SMA50 e SMA50 abaixo da SMA200).'
            ma_signal = 'BEARISH'
        else:
            ma_status = 'Neutro/Misto (médias sem alinhamento direcional claro).'
            ma_signal = 'NEUTRAL'

        if rsi > 70:
            rsi_status = 'Sobrecomprado'
        elif rsi < 30:
            rsi_status = 'Sobrevendido'
        else:
            rsi_status = 'Neutro'

        if macd_prev <= signal_prev and macd_now > signal_now:
            macd_status = 'Cruzamento bullish recente (MACD cruzou acima do sinal).'
        elif macd_prev >= signal_prev and macd_now < signal_now:
            macd_status = 'Cruzamento bearish recente (MACD cruzou abaixo do sinal).'
        elif macd_now > signal_now:
            macd_status = 'Momento bullish (MACD acima do sinal).'
        else:
            macd_status = 'Momento bearish (MACD abaixo do sinal).'

        if rsi > 70 and macd_now < signal_now:
            verdict = 'Overbought'
            sentiment = 'BEARISH'
            confidence = 72
        elif rsi < 30 and macd_now > signal_now:
            verdict = 'Oversold'
            sentiment = 'BULLISH'
            confidence = 72
        elif ma_signal == 'BULLISH' and macd_now > signal_now and rsi < 70:
            verdict = 'Bullish'
            sentiment = 'BULLISH'
            confidence = 78
        elif ma_signal == 'BEARISH' and macd_now < signal_now and rsi > 30:
            verdict = 'Bearish'
            sentiment = 'BEARISH'
            confidence = 78
        else:
            verdict = 'Neutral'
            sentiment = 'NEUTRAL'
            confidence = 64

        content = f"""# Análise Técnica — {ticker_data} (Data base: {today})

Base de preços utilizada: fechamento diário até **{data_date}** (fonte: **{source}**).

1. **Posição das médias móveis**
- Preço: `{price:.2f}`
- SMA50: `{ma50:.2f}`
- SMA200: `{ma200:.2f}`
- Leitura: {ma_status}

2. **Força Relativa (RSI 14)**
- RSI14: `{rsi:.2f}` → **{rsi_status}**

3. **Divergência / Momento do MACD (12,26,9)**
- MACD: `{macd_now:.4f}`
- Signal: `{signal_now:.4f}`
- Histograma: `{hist_now:.4f}`
- Leitura: {macd_status}

4. **Veredito Final**
- **{verdict}**
"""
        return BaseAgentOutput(content=content, sentiment=sentiment, confidence=confidence)

    except Exception as exc:
        return BaseAgentOutput(
            content=(
                f'# Análise Técnica — {ticker_data} (Data base: {today})\n\n'
                '1. **Posição das médias móveis**\n'
                '- Dados indisponíveis temporariamente.\n\n'
                '2. **Força Relativa (RSI 14)**\n'
                '- Dados indisponíveis temporariamente.\n\n'
                '3. **Divergência / Momento do MACD (12,26,9)**\n'
                '- Dados indisponíveis temporariamente.\n\n'
                '4. **Veredito Final**\n'
                '- **Neutral (dados de mercado indisponíveis no momento)**\n\n'
                f'Observação técnica: {exc}'
            ),
            sentiment='NEUTRAL',
            confidence=15,
        )


def _coerce_output(content: object) -> BaseAgentOutput:
    if isinstance(content, BaseAgentOutput):
        return content
    text = str(content or '').strip()
    if not text:
        raise ValueError('Resposta vazia do modelo para análise técnica.')
    return BaseAgentOutput(content=text, sentiment='NEUTRAL', confidence=45)


def analyze(ticker: str, market: str | None = None) -> BaseAgentOutput:
    ticker_for_mcp = _normalize_ticker(ticker, market=market)

    system_message = f"""
    Você é um Analista Técnico Quantitativo especialista.
    Sua tarefa é extrair e interpretar dados dos indicadores nativos RSI, MACD e Médias Móveis.
    USANDO ESTRITAMENTE as suas ferramentas conectadas ao MCP, obetenha os valores reais para o Ticker: {ticker_for_mcp}.

    ## OBJETIVO E FORMATO DE RESPOSTA
    Desenvolva um Markdown sucinto destacando:
    1. A posição atual das médias móveis.
    2. O status de Força Relativa (sobrecomprado/sobrevendido).
    3. A divergência atual do MACD.
    4. Veredito final ('Overbought', 'Oversold', etc).

    NUNCA fabrique dados irreais. Use sempre as ferramentas.
    """

    today = datetime.date.today().isoformat()
    try:
        # Orquestração do InvestMCP Submodule via stdio transport no ambiente ativo
        technical_mcp_toolkit = MCPTools(
            command="python mcp_servers/investmcp/technical_analysis.py",
        )

        agent = Agent(
            system_message=system_message,
            model=get_model(temperature=0.0),
            tools=[technical_mcp_toolkit],
            show_tool_calls=False,
            retries=3,
        )

        response = agent.run(f"Data Base: {today}\n\nRealize a análise técnica sistêmica usando todas as ferramentas ao seu dispor para o Ticker: {ticker}.")
        output = _coerce_output(response.content)
        if _needs_data_fallback(output.content):
            print('[technical analyst] MCP indisponível na resposta do modelo. Executando fallback automático de preços.')
            return _build_fallback_analysis(ticker, market=market)
        return output

    except Exception as e:
        print(f"Erro Crítico de Inicialização no Submódulo MCP Técnico: {e}")
        print('[technical analyst] Executando fallback automático de preços.')
        return _build_fallback_analysis(ticker, market=market)
