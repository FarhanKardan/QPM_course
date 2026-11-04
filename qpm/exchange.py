"""Exchange connection through ccxt. Keys come from the .env file.

Orders go to the testnet (config.SANDBOX). Historical data always comes
from the real exchange's public API, which needs no keys.
"""
import os

import ccxt
from dotenv import load_dotenv

import config


def get_exchange(auth: bool = False, sandbox: bool = config.SANDBOX):
    load_dotenv()
    params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
    if auth:
        params.update(apiKey=os.environ["API_KEY"], secret=os.environ["API_SECRET"])
    ex = getattr(ccxt, config.EXCHANGE)(params)
    if sandbox:
        ex.set_sandbox_mode(True)
    ex.load_markets()
    return ex


def public_exchange():
    """Real-exchange client without keys: tickers and candles only."""
    return get_exchange(auth=False, sandbox=False)


def min_amount(ex, symbol: str, price: float) -> float:
    """Smallest order size the exchange accepts for this symbol at this price."""
    lim = ex.market(symbol)["limits"]
    by_amount = lim["amount"]["min"] or 0
    by_cost = (lim["cost"]["min"] or 0) / price
    return max(by_amount, by_cost) * 1.05  # small buffer for rounding
