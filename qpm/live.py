"""Live broker: the same interface as SimBroker, but it talks to the exchange.

dry_run=True (default) only prints the orders it would send.
Orders are aggressive limit IOC orders: they fill now like a market order,
but never worse than `max_slip` away from the best price.
"""
import config
from qpm import orders
from qpm.exchange import min_amount


class LiveBroker:
    def __init__(self, ex, dry_run=True, max_slip=0.002):
        self.ex, self.dry_run, self.max_slip = ex, dry_run, max_slip

    def portfolio_snapshot(self, symbols):
        """Current coins and cash on the exchange account."""
        bal = self.ex.fetch_balance()["total"]
        positions = {s: float(bal.get(s.split("/")[0], 0) or 0) for s in symbols}
        return float(bal.get(config.QUOTE, 0) or 0), positions

    def submit(self, order):
        side = "buy" if order.qty > 0 else "sell"
        book = self.ex.fetch_order_book(order.symbol, limit=5)
        best = book["asks"][0][0] if side == "buy" else book["bids"][0][0]
        price = best * (1 + self.max_slip) if side == "buy" else best * (1 - self.max_slip)
        amount = abs(order.qty)
        if amount < min_amount(self.ex, order.symbol, price):
            print(f"skip {order.symbol}: below exchange minimum")
            return None
        if self.dry_run:
            print(f"[dry-run] IOC {side} {amount:.6f} {order.symbol} @ {price:.4f}")
            return None
        try:
            o = orders.ioc(self.ex, order.symbol, side, amount, price)
        except Exception as e:      # one rejected order must not stop the rebalance
            print(f"FAILED IOC {side} {order.symbol}: {type(e).__name__}: {str(e)[:100]}")
            return None
        print(f"sent IOC {side} {order.symbol}: filled {o.get('filled') or 0:.6g} / {amount:.6g}")
        return o
