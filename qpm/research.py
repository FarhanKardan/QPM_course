"""Parameter search (train / test split) and a simple Monte Carlo."""
import itertools

import numpy as np
import pandas as pd

from qpm import backtest_vectorized as vbt
from qpm.metrics import max_drawdown, summary
from qpm.strategy import PortfolioStrategy


def grid_search(prices, models, lookbacks, rebalances, train_frac=0.7, metric="sharpe"):
    """Pick parameters on the first 70% of history, then check them on the last 30%."""
    split = int(len(prices) * train_frac)
    test_start = prices.index[split]
    # the test run starts early only so the model has history; we score from test_start
    train, test = prices.iloc[:split], prices.iloc[split - max(lookbacks):]
    rows = []
    for m, lb, rb in itertools.product(models, lookbacks, rebalances):
        s = PortfolioStrategy(m, lb, rb)
        eq_train = vbt.run(train, s).iloc[lb:]          # skip the warm-up with no position
        eq_test = vbt.run(test, s).loc[test_start:]
        rows.append({"model": m, "lookback": lb, "rebalance": rb,
                     f"train_{metric}": summary(eq_train)[metric],
                     f"test_{metric}": summary(eq_test)[metric]})
    return pd.DataFrame(rows).sort_values(f"train_{metric}", ascending=False)


def monte_carlo(equity: pd.Series, n_paths=1000, horizon_days=365, block=7, seed=0):
    """Block bootstrap of daily returns: what range of outcomes could we expect?

    We resample blocks of `block` consecutive days, keeping short-term
    autocorrelation, and stitch them into `n_paths` possible years.
    """
    rng = np.random.default_rng(seed)
    daily = equity.resample("1D").last().pct_change().dropna().values
    n_blocks = int(np.ceil(horizon_days / block))
    finals, mdds = [], []
    for _ in range(n_paths):
        starts = rng.integers(0, len(daily) - block, n_blocks)
        path = np.concatenate([daily[s:s + block] for s in starts])[:horizon_days]
        curve = pd.Series(np.cumprod(1 + path))
        finals.append(curve.iloc[-1] - 1)
        mdds.append(max_drawdown(curve))
    return pd.DataFrame({"final_return": finals, "max_drawdown": mdds})
