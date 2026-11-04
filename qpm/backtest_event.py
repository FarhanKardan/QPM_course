"""Event-driven backtest: the market is replayed one event at a time.

    MarketEvent -> broker fills orders queued on the previous bar -> FillEvent
                -> SignalEvent -> strategy checks the clock -> OrderEvent

Slower than vectorized, but it behaves like the live system: weights drift,
orders have sizes, minimums and cash, and fills happen on the next bar.
Swap SimBroker for LiveBroker and the same loop trades for real.
"""
from collections import deque
from dataclasses import dataclass

import pandas as pd

import config


@dataclass
class MarketEvent:
    ts: pd.Timestamp
    prices: pd.Series


@dataclass
class SignalEvent:
    ts: pd.Timestamp
    prices: pd.Series


@dataclass
class OrderEvent:
    symbol: str
    qty: float          # + buy, - sell (in coins)


@dataclass
class FillEvent:
    ts: pd.Timestamp
    symbol: str
    qty: float
    price: float
    fee: float


class Portfolio:
    def __init__(self, cash=config.INITIAL_CASH):
        self.cash = cash
        self.positions = {}          # symbol -> coins

    def equity(self, prices):
        return self.cash + sum(q * prices[s] for s, q in self.positions.items())

    def on_fill(self, f: FillEvent):
        self.positions[f.symbol] = self.positions.get(f.symbol, 0.0) + f.qty
        self.cash -= f.qty * f.price + f.fee

    def orders_for(self, weights: pd.Series, prices: pd.Series, buffer=0.01):
        """Turn target weights into coin quantities (sells first, to free cash)."""
        eq = self.equity(prices) * (1 - buffer)
        orders = []
        for sym, w in weights.items():
            delta = w * eq / prices[sym] - self.positions.get(sym, 0.0)
            if abs(delta * prices[sym]) >= config.MIN_TRADE_USDT:
                orders.append(OrderEvent(sym, delta))
        return sorted(orders, key=lambda o: o.qty)


class SimBroker:
    """Fills every order at the next bar's price, plus slippage and fee."""

    def __init__(self, fee=config.FEE, slippage=config.SLIPPAGE):
        self.fee, self.slippage, self.pending = fee, slippage, []

    def submit(self, order: OrderEvent):
        self.pending.append(order)

    def on_market(self, e: MarketEvent):
        fills = []
        for o in self.pending:
            side = 1 if o.qty > 0 else -1
            price = e.prices[o.symbol] * (1 + side * self.slippage)
            fills.append(FillEvent(e.ts, o.symbol, o.qty, price, abs(o.qty) * price * self.fee))
        self.pending = []
        return fills


def run(prices: pd.DataFrame, strategy, broker=None, portfolio=None, verbose=False):
    broker = broker or SimBroker()
    pf = portfolio or Portfolio()
    queue, equity, trades = deque(), {}, []

    for i, (ts, row) in enumerate(prices.iterrows()):
        queue.append(MarketEvent(ts, row))
        while queue:
            e = queue.popleft()
            if isinstance(e, MarketEvent):
                queue.extend(broker.on_market(e))           # yesterday's orders fill now
                queue.append(SignalEvent(e.ts, e.prices))
            elif isinstance(e, FillEvent):
                pf.on_fill(e)
                trades.append(e)
            elif isinstance(e, SignalEvent):
                equity[e.ts] = pf.equity(e.prices)
                if i >= strategy.lookback and strategy.is_rebalance_time(e.ts):
                    w = strategy.target_weights(prices.iloc[i - strategy.lookback:i + 1])
                    if verbose:
                        print(e.ts, w.round(3).to_dict())
                    queue.extend(pf.orders_for(w, e.prices))
            elif isinstance(e, OrderEvent):
                broker.submit(e)

    return pd.Series(equity), trades
