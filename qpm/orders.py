"""One small function per order type. Each returns the ccxt order dict.

ccxt's unified params keep this the same on Binance and Bybit:
timeInForce = GTC (default) | IOC | FOK, postOnly = True, triggerPrice = ...
"""
import time
import uuid


def _prep(ex, symbol, amount, price=None):
    amount = float(ex.amount_to_precision(symbol, amount))
    price = float(ex.price_to_precision(symbol, price)) if price is not None else None
    return amount, price


def _cid(tag):
    # clientOrderId makes a retry safe: the exchange rejects a duplicate id
    return f"{tag}{uuid.uuid4().hex[:16]}"


def market(ex, symbol, side, amount):
    """Fill now at whatever the book offers. You pay the spread + slippage."""
    amount, _ = _prep(ex, symbol, amount)
    # Some exchanges (OKX) size a market BUY in quote currency; ccxt converts
    # amount x price into that cost, so we pass the current ask as `price`.
    price = ex.fetch_order_book(symbol, limit=5)["asks"][0][0] if side == "buy" else None
    return ex.create_order(symbol, "market", side, amount, price,
                           {"clientOrderId": _cid("mkt")})


def limit(ex, symbol, side, amount, price):
    """Rest in the book (GTC) until filled or cancelled."""
    amount, price = _prep(ex, symbol, amount, price)
    return ex.create_order(symbol, "limit", side, amount, price,
                           {"clientOrderId": _cid("lmt")})


def post_only(ex, symbol, side, amount, price):
    """Maker-only: rejected/cancelled if it would cross the spread."""
    amount, price = _prep(ex, symbol, amount, price)
    return ex.create_order(symbol, "limit", side, amount, price,
                           {"postOnly": True, "clientOrderId": _cid("po")})


def ioc(ex, symbol, side, amount, price):
    """Immediate-or-cancel: fill what you can now, cancel the rest."""
    amount, price = _prep(ex, symbol, amount, price)
    return ex.create_order(symbol, "limit", side, amount, price,
                           {"timeInForce": "IOC", "clientOrderId": _cid("ioc")})


def fok(ex, symbol, side, amount, price):
    """Fill-or-kill: the whole amount now, or nothing at all."""
    amount, price = _prep(ex, symbol, amount, price)
    return ex.create_order(symbol, "limit", side, amount, price,
                           {"timeInForce": "FOK", "clientOrderId": _cid("fok")})


def stop_limit(ex, symbol, side, amount, price, trigger):
    """Becomes a limit order only after the market touches `trigger`."""
    amount, price = _prep(ex, symbol, amount, price)
    trigger = float(ex.price_to_precision(symbol, trigger))
    return ex.create_order(symbol, "limit", side, amount, price,
                           {"triggerPrice": trigger, "clientOrderId": _cid("stp")})


def cancel(ex, order_id, symbol, trigger=False):
    return ex.cancel_order(order_id, symbol, {"trigger": True} if trigger else {})


def status(ex, order_id, symbol, trigger=False):
    """Look an order up as open first, then as closed (Bybit keeps them apart)."""
    params = {"trigger": True} if trigger else {}
    for fn in ("fetch_open_order", "fetch_closed_order", "fetch_order"):
        try:
            return getattr(ex, fn)(order_id, symbol, params)
        except Exception:
            continue
    return {"id": order_id, "status": "unknown", "filled": None}


def twap(ex, symbol, side, total, slices, interval_s, dry_run=True):
    """Split `total` into equal market orders spread over time."""
    child = total / slices
    fills = []
    for i in range(slices):
        if dry_run:
            print(f"[dry-run] slice {i + 1}/{slices}: {side} {child:.6f} {symbol}")
        else:
            fills.append(market(ex, symbol, side, child))
        if i < slices - 1:
            time.sleep(interval_s)
    return fills
