"""Portfolio models. Each takes a returns window and returns long-only weights summing to 1."""
import numpy as np
import pandas as pd
from scipy.optimize import minimize

import config


def equal(rets: pd.DataFrame) -> pd.Series:
    return pd.Series(1 / rets.shape[1], index=rets.columns)


def inverse_vol(rets: pd.DataFrame) -> pd.Series:
    """Naive risk parity: weight each asset by 1 / volatility."""
    inv = 1 / rets.std()
    return inv / inv.sum()


def _optimize(rets, objective):
    n = rets.shape[1]
    res = minimize(objective, np.full(n, 1 / n), method="SLSQP",
                   bounds=[(0, config.MAX_WEIGHT)] * n,
                   constraints=[{"type": "eq", "fun": lambda w: w.sum() - 1}])
    w = np.clip(res.x, 0, None)
    return pd.Series(w / w.sum(), index=rets.columns)


def min_variance(rets: pd.DataFrame) -> pd.Series:
    """Markowitz minimum-variance portfolio."""
    cov = rets.cov().values * 1e4   # hourly variances are ~1e-5: scale so SLSQP moves
    return _optimize(rets, lambda w: w @ cov @ w)


def max_sharpe(rets: pd.DataFrame) -> pd.Series:
    """Markowitz tangency portfolio (risk-free = 0). Most sensitive to noise."""
    mu, cov = rets.mean().values, rets.cov().values
    return _optimize(rets, lambda w: -(w @ mu) / np.sqrt(w @ cov @ w + 1e-12))


MODELS = {"equal": equal, "inverse_vol": inverse_vol,
          "min_variance": min_variance, "max_sharpe": max_sharpe}
