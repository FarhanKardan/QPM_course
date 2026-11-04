"""The strategy: every N hours, look back L hours and re-optimize weights.

The same object is used by the vectorized backtest, the event-driven
backtest and the live loop. That is the point of the design.
"""
import pandas as pd

import config
from qpm.models import MODELS


class PortfolioStrategy:
    def __init__(self, model=config.MODEL, lookback=config.LOOKBACK_H,
                 rebalance_every=config.REBALANCE_H):
        self.model = model
        self.lookback = lookback
        self.rebalance_every = rebalance_every

    def is_rebalance_time(self, ts: pd.Timestamp) -> bool:
        hours_since_epoch = int(ts.timestamp() // 3600)
        return hours_since_epoch % self.rebalance_every == 0

    def target_weights(self, price_window: pd.DataFrame) -> pd.Series:
        rets = price_window.pct_change().dropna()
        return MODELS[self.model](rets)

    def __repr__(self):
        return f"{self.model}(lookback={self.lookback}h, every={self.rebalance_every}h)"
