"""All knobs of the lab in one place."""

EXCHANGE = "binance"        # any ccxt id with a testnet, e.g. "bybit"
SANDBOX = True              # True = testnet (fake money) for orders
QUOTE = "USDT"              # trade only XXX/USDT pairs
N_ASSETS = 8                # how many symbols to pick by 24h volume
EXCLUDE = {"USDC", "USDT", "DAI", "TUSD", "FDUSD", "USDD", "PYUSD", "EUR", "BUSD"}

TIMEFRAME = "1h"
HISTORY_DAYS = 180          # history used for backtests

MODEL = "inverse_vol"       # equal | inverse_vol | min_variance | max_sharpe
LOOKBACK_H = 168            # hours of history the model sees (7 days)
REBALANCE_H = 24            # re-optimize every N hours
MAX_WEIGHT = 0.35           # cap per asset for optimizer models

FEE = 0.001                 # 0.1% taker fee
SLIPPAGE = 0.0005           # 5 bps assumed slippage per trade
INITIAL_CASH = 10_000.0
MIN_TRADE_USDT = 10.0       # skip tiny rebalancing trades

DATA_FILE = "data/prices.csv"
RESULTS_DIR = "results"
