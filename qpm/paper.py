"""Paper exchange: real order book, simulated fills. No account, no keys.

It answers the same calls our code makes on a ccxt exchange (create_order,
cancel_order, fetch_order, fetch_balance ...) and forwards everything else
(markets, precision, order books) to the real public exchange.

Matching rules, against the live order book at the moment of the order:
  market      walks the book until the amount is filled
  limit GTC   fills what crosses now, the rest rests; checked again on fetch
  post-only   rejected if it would cross (it would be a taker)
  IOC         fills what crosses now, cancels the rest
  FOK         fills everything now or nothing
  stop-limit  rests untriggered until the last price touches the trigger
Balances persist in data/paper_account.json between runs.
"""
import json
import os
import uuid

import ccxt

import config

STATE_FILE = "data/paper_account.json"


class PaperExchange:
    def __init__(self, public_ex, cash=config.INITIAL_CASH, fee=config.FEE):
        self.public, self.fee = public_ex, fee
        self.balances, self.orders = {config.QUOTE: cash}, {}
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE) as f:
                s = json.load(f)
            self.balances, self.orders = s["balances"], s["orders"]

    def __getattr__(self, name):                 # markets, precision, order books...
        return getattr(self.public, name)

    # ---------- orders ----------
    def create_order(self, symbol, type, side, amount, price=None, params=None):
        params = params or {}
        o = {"id": uuid.uuid4().hex[:12], "clientOrderId": params.get("clientOrderId"),
             "symbol": symbol, "type": type, "side": side, "amount": amount,
             "price": price, "filled": 0.0, "cost": 0.0, "status": "open",
             "timeInForce": params.get("timeInForce", "GTC"),
             "postOnly": bool(params.get("postOnly")), "triggerPrice": params.get("triggerPrice")}

        if o["triggerPrice"] is None:
            if o["postOnly"] and self._crosses(o):
                raise ccxt.InvalidOrder("paper: post-only order would cross the spread")
            self._match(o)
            if type == "market" or o["timeInForce"] in ("IOC", "FOK"):
                if o["status"] == "open":
                    o["status"] = "canceled"
        self.orders[o["id"]] = o
        self._save()
        return self._view(o)

    def cancel_order(self, id, symbol=None, params=None):
        o = self.orders[id]
        if o["status"] == "open":
            o["status"] = "canceled"
            self._save()
        return self._view(o)

    def fetch_order(self, id, symbol=None, params=None):
        o = self.orders[id]
        if o["status"] == "open":
            self._refresh(o)
        return self._view(o)

    fetch_open_order = fetch_closed_order = fetch_order

    def fetch_open_orders(self, symbol=None, since=None, limit=None, params=None):
        return [self.fetch_order(i) for i, o in list(self.orders.items())
                if o["status"] == "open" and (symbol is None or o["symbol"] == symbol)]

    def fetch_balance(self, params=None):
        return {"total": dict(self.balances), "free": dict(self.balances)}

    # ---------- matching ----------
    def _book(self, symbol):
        return self.public.fetch_order_book(symbol, limit=50)

    def _crosses(self, o):
        book = self._book(o["symbol"])
        if o["side"] == "buy":
            return o["price"] >= book["asks"][0][0]
        return o["price"] <= book["bids"][0][0]

    def _match(self, o):
        """Fill against the book within the limit price (none for market)."""
        book = self._book(o["symbol"])
        levels = book["asks"] if o["side"] == "buy" else book["bids"]
        want = o["amount"] - o["filled"]
        fills = []
        for level in levels:
            px, size = level[0], level[1]
            if o["type"] != "market":
                if (o["side"] == "buy" and px > o["price"]) or (o["side"] == "sell" and px < o["price"]):
                    break
            take = min(want, size)
            fills.append((px, take))
            want -= take
            if want <= 1e-12:
                break
        qty = sum(q for _, q in fills)
        if o["timeInForce"] == "FOK" and qty < o["amount"] - o["filled"] - 1e-12:
            return                                   # all or nothing: nothing
        if qty > 0:
            self._settle(o, fills)

    def _settle(self, o, fills):
        base = o["symbol"].split("/")[0]
        qty = sum(q for _, q in fills)
        cost = sum(p * q for p, q in fills)
        fee = cost * self.fee
        if o["side"] == "buy":
            if self.balances.get(config.QUOTE, 0) < cost + fee:
                raise ccxt.InsufficientFunds(f"paper: need {cost + fee:.2f} {config.QUOTE}")
            self.balances[config.QUOTE] -= cost + fee
            self.balances[base] = self.balances.get(base, 0) + qty
        else:
            if self.balances.get(base, 0) < qty - 1e-12:
                raise ccxt.InsufficientFunds(f"paper: not enough {base}")
            self.balances[base] -= qty
            self.balances[config.QUOTE] = self.balances.get(config.QUOTE, 0) + cost - fee
        o["filled"] += qty
        o["cost"] += cost
        if o["filled"] >= o["amount"] - 1e-12:
            o["status"] = "closed"

    def _refresh(self, o):
        """A resting order fills later if the market comes to it."""
        if o["triggerPrice"] is not None:
            last = self.public.fetch_ticker(o["symbol"])["last"]
            hit = last >= o["triggerPrice"] if o["side"] == "buy" else last <= o["triggerPrice"]
            if not hit:
                return
            o["triggerPrice"] = None                 # triggered: now a plain limit order
        self._match(o)
        self._save()

    # ---------- helpers ----------
    def _view(self, o):
        v = dict(o)
        v["remaining"] = o["amount"] - o["filled"]
        v["average"] = o["cost"] / o["filled"] if o["filled"] else None
        return v

    def _save(self):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w") as f:
            json.dump({"balances": self.balances, "orders": self.orders}, f, indent=1)
