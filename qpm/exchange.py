"""Exchange connections through ccxt.

  public_exchange(): the real EXCHANGE, no keys -> tickers, candles, order book
  get_exchange():    where orders go
                     paper   -> PaperExchange on top of the live order book (no account)
                     testnet -> TESTNET_EXCHANGE testnet/demo with keys from .env
"""
import os

import ccxt
from dotenv import load_dotenv

import config


def public_exchange():
    """Real exchange without keys: tickers, candles and order books."""
    ex = getattr(ccxt, config.EXCHANGE)({"enableRateLimit": True,
                                         "options": {"defaultType": "spot"}})
    ex.load_markets()
    return ex


def get_exchange(auth: bool = False):
    """The exchange orders go to, chosen by config.EXECUTION."""
    if config.EXECUTION == "paper":
        from qpm.paper import PaperExchange
        return PaperExchange(public_exchange())

    load_dotenv()
    params = {"enableRateLimit": True, "options": {"defaultType": "spot"}}
    if auth:
        params.update(apiKey=os.environ["API_KEY"], secret=os.environ["API_SECRET"])
        if os.environ.get("API_PASSWORD"):          # OKX calls it passphrase
            params["password"] = os.environ["API_PASSWORD"]
    ex = getattr(ccxt, config.TESTNET_EXCHANGE)(params)
    ex.set_sandbox_mode(True)                       # testnet / demo trading
    ex.load_markets()
    return ex


def min_amount(ex, symbol: str, price: float) -> float:
    """Smallest order size the exchange accepts for this symbol at this price."""
    lim = ex.market(symbol)["limits"]
    by_amount = lim["amount"]["min"] or 0
    by_cost = (lim["cost"]["min"] or 0) / price
    return max(by_amount, by_cost) * 1.05  # small buffer for rounding
