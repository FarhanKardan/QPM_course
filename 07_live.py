"""Step 7 — run the strategy live. Same PortfolioStrategy, real (testnet) broker.

Every hour it wakes up; on rebalance hours it re-optimizes and trades the difference.

    python 07_live.py --once            # one rebalance now, dry-run
    python 07_live.py --once --send     # one rebalance now, really send to testnet
    python 07_live.py --send            # keep running
"""
import argparse
import time
from datetime import datetime, timedelta, timezone

import pandas as pd

import config
from qpm.backtest_event import Portfolio
from qpm.data import fetch_history
from qpm.exchange import get_exchange, public_exchange
from qpm.live import LiveBroker
from qpm.strategy import PortfolioStrategy


def rebalance(strategy, symbols, broker, data_ex):
    days = strategy.lookback // 24 + 2
    prices = pd.DataFrame({s: fetch_history(data_ex, s, days=days) for s in symbols}).ffill().dropna()
    window = prices.iloc[-(strategy.lookback + 1):]
    weights = strategy.target_weights(window)
    print("target weights:", weights.round(3).to_dict())

    pf = Portfolio()                                   # mirror the real account
    pf.cash, pf.positions = broker.portfolio_snapshot(symbols)
    last = window.iloc[-1]
    print(f"account equity: {pf.equity(last):,.2f} {config.QUOTE}")
    for order in pf.orders_for(weights, last):
        broker.submit(order)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--send", action="store_true")
    p.add_argument("--once", action="store_true", help="rebalance now and exit")
    a = p.parse_args()

    symbols = list(pd.read_csv(config.DATA_FILE, index_col=0, nrows=1).columns)
    strategy = PortfolioStrategy()
    broker = LiveBroker(get_exchange(auth=True), dry_run=not a.send)
    data_ex = public_exchange()

    # the universe comes from the data exchange; the execution venue may not list every pair
    missing = [s for s in symbols if s not in broker.ex.markets]
    if missing:
        print(f"not tradable on the execution exchange, dropped: {missing}")
        symbols = [s for s in symbols if s in broker.ex.markets]
    if not symbols:
        raise SystemExit("no tradable symbols left")
    print(f"live: {strategy} on {symbols}  ({'SEND' if a.send else 'dry-run'})")

    if a.once:
        rebalance(strategy, symbols, broker, data_ex)
        return
    while True:
        now = pd.Timestamp.now(tz="UTC").floor("h")
        if strategy.is_rebalance_time(now):
            print(f"\n=== {now} rebalance ===")
            rebalance(strategy, symbols, broker, data_ex)
        nxt = datetime.now(timezone.utc).replace(minute=0, second=5, microsecond=0) + timedelta(hours=1)
        time.sleep((nxt - datetime.now(timezone.utc)).total_seconds())


if __name__ == "__main__":
    main()
