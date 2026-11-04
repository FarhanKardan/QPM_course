"""Performance numbers from an equity curve (hourly bars)."""
import numpy as np
import pandas as pd

HOURS_PER_YEAR = 24 * 365


def max_drawdown(equity: pd.Series) -> float:
    return float((equity / equity.cummax() - 1).min())


def summary(equity: pd.Series, periods=HOURS_PER_YEAR) -> dict:
    rets = equity.pct_change().dropna()
    years = len(rets) / periods
    total = equity.iloc[-1] / equity.iloc[0] - 1
    vol = rets.std() * np.sqrt(periods)
    sharpe = rets.mean() / rets.std() * np.sqrt(periods) if rets.std() > 0 else 0.0
    mdd = max_drawdown(equity)
    cagr = (1 + total) ** (1 / years) - 1 if years > 0 else 0.0
    return {"total_return": total, "cagr": cagr, "ann_vol": vol,
            "sharpe": sharpe, "max_drawdown": mdd,
            "calmar": cagr / abs(mdd) if mdd < 0 else np.nan}


def print_summary(name: str, equity: pd.Series):
    s = summary(equity)
    print(f"{name:<40} return {s['total_return']:+7.1%}  sharpe {s['sharpe']:5.2f}  "
          f"vol {s['ann_vol']:6.1%}  maxDD {s['max_drawdown']:7.1%}")
    return s
