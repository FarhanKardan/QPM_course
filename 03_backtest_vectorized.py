"""Step 3 — compare the four portfolio models with the fast vectorized backtest.

    python 03_backtest_vectorized.py [--synthetic]
"""
import argparse
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

import config
from qpm import backtest_vectorized as vbt
from qpm.data import get_prices
from qpm.metrics import print_summary
from qpm.models import MODELS
from qpm.strategy import PortfolioStrategy


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--synthetic", action="store_true")
    prices = get_prices(p.parse_args().synthetic)

    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 5))
    for model in MODELS:
        s = PortfolioStrategy(model)
        eq = vbt.run(prices, s)
        print_summary(str(s), eq)
        ax.plot(eq, label=model)

    ax.set_title("Vectorized backtest: portfolio models")
    ax.legend()
    fig.savefig(f"{config.RESULTS_DIR}/03_models.png", dpi=120, bbox_inches="tight")
    print(f"\nchart: {config.RESULTS_DIR}/03_models.png")


if __name__ == "__main__":
    main()
