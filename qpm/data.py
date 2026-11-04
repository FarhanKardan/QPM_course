"""Pick symbols and download hourly prices (cached to CSV)."""
import os
import time

import numpy as np
import pandas as pd

import config

LEVERAGED = ("3L", "3S", "2L", "2S", "UP", "DOWN")


def select_universe(ex, n=config.N_ASSETS, allowed_bases=None):
    """Top-n USDT pairs by 24h quote volume, without stablecoins or leveraged tokens.

    allowed_bases: only coins we can also trade on the order exchange.
    """
    rows = []
    for sym, t in ex.fetch_tickers().items():
        if not sym.endswith("/" + config.QUOTE) or sym not in ex.markets:
            continue
        base = sym.split("/")[0]
        if base in config.EXCLUDE or base.endswith(LEVERAGED):
            continue
        if allowed_bases is not None and base not in allowed_bases:
            continue
        rows.append((sym, t.get("quoteVolume") or 0))
    rows.sort(key=lambda r: r[1], reverse=True)
    return [s for s, _ in rows[:n]]


def fetch_history(ex, symbol, days=config.HISTORY_DAYS, timeframe=config.TIMEFRAME):
    """Page through candles (1000 per call works on most exchanges)."""
    tf_ms = ex.parse_timeframe(timeframe) * 1000
    since = ex.milliseconds() - days * 86_400_000
    candles = []
    while since < ex.milliseconds() - tf_ms:
        batch = ex.fetch_ohlcv(symbol, timeframe, since=since, limit=1000)
        if not batch:
            break
        candles += batch
        since = batch[-1][0] + tf_ms
        time.sleep(ex.rateLimit / 1000)
    df = pd.DataFrame(candles, columns=["ts", "open", "high", "low", "close", "volume"])
    df = df.drop_duplicates("ts")
    return df.set_index(pd.to_datetime(df["ts"], unit="ms", utc=True))["close"]


def load_prices(ex=None, symbols=None, refresh=False):
    """Close-price table: rows = hours, columns = symbols."""
    if os.path.exists(config.DATA_FILE) and not refresh:
        return pd.read_csv(config.DATA_FILE, index_col=0, parse_dates=True)
    closes = {s: fetch_history(ex, s) for s in symbols}
    prices = pd.DataFrame(closes).sort_index().ffill().dropna()
    os.makedirs(os.path.dirname(config.DATA_FILE), exist_ok=True)
    prices.to_csv(config.DATA_FILE)
    return prices


def get_prices(synthetic=False):
    """Prices for scripts 03-06: the CSV from step 02, or fake data offline."""
    if synthetic:
        return synthetic_prices()
    if not os.path.exists(config.DATA_FILE):
        raise SystemExit("No data yet: run `python 02_universe_and_data.py` first "
                         "(or add --synthetic to test offline).")
    return load_prices()


def synthetic_prices(n_assets=config.N_ASSETS, days=config.HISTORY_DAYS, seed=7):
    """Fake correlated random-walk prices, to test the pipeline offline."""
    rng = np.random.default_rng(seed)
    hours = days * 24
    common = rng.normal(0, 0.006, hours)
    cols = {}
    for i in range(n_assets):
        vol = 0.004 + 0.003 * i / n_assets
        r = 0.6 * common + rng.normal(0.00005, vol, hours)
        cols[f"SYN{i}/USDT"] = 100 * np.exp(np.cumsum(r))
    idx = pd.date_range("2026-01-01", periods=hours, freq="h", tz="UTC")
    return pd.DataFrame(cols, index=idx)
