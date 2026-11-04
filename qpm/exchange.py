"""Exchange connections through ccxt.

Two clients:
  * public_exchange(): real DATA_EXCHANGE, no keys -> tickers and candles
  * get_exchange():    ORDER_EXCHANGE testnet, with keys from .env -> orders
"""
import os

import ccxt
from dotenv import load_dotenv

import config


def get_exchange(auth: bool = False, sandbox: bool = config.SANDBOX):
    """The exchange orders go to (testnet by default)."""
    load_dotenv()
    params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
    if auth:
        # Deribit calls these Client ID / Client Secret
        params.update(apiKey=os.environ["API_KEY"], secret=os.environ["API_SECRET"])
    ex = getattr(ccxt, config.ORDER_EXCHANGE)(params)
    if sandbox:
        ex.set_sandbox_mode(True)
    ex.load_markets()
    return ex


def public_exchange():
    """Real data exchange without keys: tickers and candles only."""
    ex = getattr(ccxt, config.DATA_EXCHANGE)({"enableRateLimit": True,
                                              "options": {"defaultType": "spot"}})
    ex.load_markets()
    return ex


def tradable_bases(order_ex) -> set:
    """Coins that have a spot XXX/ORDER_QUOTE market on the order exchange."""
    return {m["base"] for m in order_ex.markets.values()
            if m.get("spot") and m["quote"] == config.ORDER_QUOTE and m.get("active", True)}


def to_order_symbol(data_symbol: str) -> str:
    """BTC/USDT (data) -> BTC/USDC (orders)."""
    return f"{data_symbol.split('/')[0]}/{config.ORDER_QUOTE}"


def min_amount(ex, symbol: str, price: float) -> float:
    """Smallest order size the exchange accepts for this symbol at this price."""
    lim = ex.market(symbol)["limits"]
    by_amount = lim["amount"]["min"] or 0
    by_cost = (lim["cost"]["min"] or 0) / price
    return max(by_amount, by_cost) * 1.05  # small buffer for rounding
