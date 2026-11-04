"""Step 2 — pick the symbols and download hourly history.

    python 02_universe_and_data.py
"""
import config
from qpm.data import load_prices, select_universe
from qpm.exchange import public_exchange


def main():
    ex = public_exchange()
    symbols = select_universe(ex)
    print(f"Top {config.N_ASSETS} {config.QUOTE} pairs by 24h volume: {symbols}")
    prices = load_prices(ex, symbols, refresh=True)
    print(f"{len(prices)} hourly bars, {prices.index[0]} -> {prices.index[-1]}")
    print(f"saved to {config.DATA_FILE}")


if __name__ == "__main__":
    main()
