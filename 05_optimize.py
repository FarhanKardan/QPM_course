"""Step 5 — choose model, lookback and rebalance frequency on train, check on test.

    python 05_optimize.py [--synthetic]
"""
import argparse

from qpm.data import get_prices
from qpm.models import MODELS
from qpm.research import grid_search


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--synthetic", action="store_true")
    prices = get_prices(p.parse_args().synthetic)

    table = grid_search(prices, models=list(MODELS),
                        lookbacks=[72, 168, 336], rebalances=[12, 24, 72])
    print(table.head(10).round(2).to_string(index=False))
    best = table.iloc[0]
    print(f"\nbest on train: {best['model']}, lookback {best['lookback']}h, "
          f"every {best['rebalance']}h -> test sharpe {best['test_sharpe']:.2f}")
    print("If test is much worse than train, the 'best' was mostly luck (overfitting).")


if __name__ == "__main__":
    main()
