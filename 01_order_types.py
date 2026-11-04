"""Step 1 — every order type on the testnet, safely.

Prices are set far from the market, so nothing fills by accident:
  limit / stop-limit  -> rest in the book, then we cancel them
  post-only at the ask -> rejected (it would be a taker)
  IOC / FOK far away  -> cancelled / killed instantly
Only `--market` sends a real (tiny, testnet) market order.

    python 01_order_types.py                # print what would be sent
    python 01_order_types.py --send         # send to testnet
    python 01_order_types.py --send --market
"""
import argparse
import time

from qpm import orders
from qpm.exchange import get_exchange, min_amount


def show(name, o):
    print(f"{name:<12} id={o['id']}  status={o['status']}  filled={o.get('filled')}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="BTC/USDT")
    p.add_argument("--send", action="store_true", help="really send to the testnet")
    p.add_argument("--market", action="store_true", help="also send one tiny market order")
    a = p.parse_args()

    ex = get_exchange(auth=a.send)
    book = ex.fetch_order_book(a.symbol, limit=5)
    bid, ask = book["bids"][0][0], book["asks"][0][0]
    qty = min_amount(ex, a.symbol, bid * 0.7)
    print(f"{a.symbol}  bid={bid}  ask={ask}  spread={(ask - bid) / bid * 1e4:.1f} bps  qty={qty:.6f}\n")

    # (name, send, cancel afterwards?, is a trigger order?)
    plan = [
        ("LIMIT GTC", lambda: orders.limit(ex, a.symbol, "buy", qty, bid * 0.7), True, False),
        ("POST-ONLY", lambda: orders.post_only(ex, a.symbol, "buy", qty, ask), False, False),
        ("IOC", lambda: orders.ioc(ex, a.symbol, "buy", qty, bid * 0.7), False, False),
        ("FOK", lambda: orders.fok(ex, a.symbol, "buy", qty, bid * 0.7), False, False),
        ("STOP-LIMIT", lambda: orders.stop_limit(ex, a.symbol, "buy", qty,
                                                 ask * 1.31, ask * 1.30), True, True),
    ]
    if not a.send:
        for name, *_ in plan:
            print(f"[dry-run] would send {name}")
        return

    for name, send, needs_cancel, trigger in plan:
        try:
            o = send()
            time.sleep(1)
            o = orders.status(ex, o["id"], a.symbol, trigger)
            show(name, o)
            if needs_cancel and o["status"] in ("open", "unknown"):
                orders.cancel(ex, o["id"], a.symbol, trigger)
                print(f"{'':<12} cancelled")
        except Exception as e:  # post-only at the ask is *expected* to fail
            print(f"{name:<12} rejected: {type(e).__name__}: {str(e)[:90]}")

    if a.market:
        show("MARKET", orders.market(ex, a.symbol, "buy", min_amount(ex, a.symbol, ask)))


if __name__ == "__main__":
    main()
