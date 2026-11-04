"""Step 4 — the same strategy, event by event. Compare with the vectorized result.

    python 04_backtest_event.py [--synthetic] [--verbose]
"""
import argparse
import os
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from qpm import backtest_event, backtest_vectorized as vbt
from qpm.data import get_prices
from qpm.metrics import print_summary
from qpm.strategy import PortfolioStrategy


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--synthetic", action="store_true")
    p.add_argument("--verbose", action="store_true", help="print weights at each rebalance")
    a = p.parse_args()
    prices = get_prices(a.synthetic)
    s = PortfolioStrategy()

    t = time.time()
    eq_vec = vbt.run(prices, s)
    t_vec = time.time() - t

    t = time.time()
    eq_evt, trades = backtest_event.run(prices, s, verbose=a.verbose)
    t_evt = time.time() - t

    print(f"strategy: {s}\n")
    print_summary(f"vectorized ({t_vec:.1f}s)", eq_vec)
    print_summary(f"event-driven ({t_evt:.1f}s)", eq_evt)
    print(f"\nevent-driven trades: {len(trades)}, fees paid: {sum(f.fee for f in trades):,.0f} {config.QUOTE}")

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(eq_vec, label="vectorized")
    ax.plot(eq_evt, label="event-driven")
    ax.set_title(f"Same strategy, two backtests: {s}")
    ax.legend()
    fig.savefig(f"{config.RESULTS_DIR}/04_vec_vs_event.png", dpi=120, bbox_inches="tight")
    print(f"chart: {config.RESULTS_DIR}/04_vec_vs_event.png")


if __name__ == "__main__":
    main()
