"""Step 6 — Monte Carlo: the range of one-year outcomes, not a single number.

    python 06_monte_carlo.py [--synthetic]
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from qpm import backtest_event
from qpm.data import get_prices
from qpm.research import monte_carlo
from qpm.strategy import PortfolioStrategy


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--synthetic", action="store_true")
    prices = get_prices(p.parse_args().synthetic)

    equity, _ = backtest_event.run(prices, PortfolioStrategy())
    mc = monte_carlo(equity)

    q = mc.quantile([0.05, 0.5, 0.95])
    print("1-year outcomes from 1000 resampled paths:")
    print(f"  return   5% {q.loc[0.05, 'final_return']:+.1%}   median {q.loc[0.5, 'final_return']:+.1%}"
          f"   95% {q.loc[0.95, 'final_return']:+.1%}")
    print(f"  maxDD    5% {q.loc[0.05, 'max_drawdown']:.1%}   median {q.loc[0.5, 'max_drawdown']:.1%}")
    print(f"  chance of losing money: {(mc['final_return'] < 0).mean():.0%}")

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(12, 4))
    axes[0].hist(mc["final_return"], bins=50)
    axes[0].set_title("1-year return")
    axes[1].hist(mc["max_drawdown"], bins=50, color="tab:orange")
    axes[1].set_title("Max drawdown")
    fig.savefig(f"{config.RESULTS_DIR}/06_monte_carlo.png", dpi=120, bbox_inches="tight")
    print(f"chart: {config.RESULTS_DIR}/06_monte_carlo.png")


if __name__ == "__main__":
    main()
