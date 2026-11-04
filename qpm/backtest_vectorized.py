"""Vectorized backtest: the whole history as matrices, a few lines of pandas.

Fast, so it suits parameter search. Its simplifications:
  * weights stay fixed between rebalances (no drift), as if re-balanced every bar
  * you trade at the bar's close and earn from the next bar (the shift(1))
  * cost = turnover x (fee + slippage); no order sizes, no minimums, no cash
"""
import pandas as pd

import config


def compute_weights(prices: pd.DataFrame, strategy) -> pd.DataFrame:
    w = pd.DataFrame(index=prices.index, columns=prices.columns, dtype=float)
    for i, ts in enumerate(prices.index):
        if i >= strategy.lookback and strategy.is_rebalance_time(ts):
            w.loc[ts] = strategy.target_weights(prices.iloc[i - strategy.lookback:i + 1])
    return w.ffill().fillna(0.0)


def run(prices: pd.DataFrame, strategy, fee=config.FEE, slippage=config.SLIPPAGE,
        initial=config.INITIAL_CASH) -> pd.Series:
    rets = prices.pct_change().fillna(0.0)
    w = compute_weights(prices, strategy)
    gross = (w.shift(1).fillna(0.0) * rets).sum(axis=1)       # no look-ahead
    turnover = w.diff().abs().sum(axis=1).fillna(w.iloc[0].abs().sum())
    net = gross - turnover * (fee + slippage)
    return (1 + net).cumprod() * initial
