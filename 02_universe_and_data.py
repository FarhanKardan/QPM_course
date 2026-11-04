"""Step 2 — pick the symbols and download hourly history.

Universe = the most traded coins on the data exchange that we can also
trade spot on the order exchange.

    python 02_universe_and_data.py
"""
import config
from qpm.data import load_prices, select_universe
from qpm.exchange import get_exchange, public_exchange, tradable_bases


def main():
    data_ex = public_exchange()
    bases = tradable_bases(get_exchange(auth=False))
    print(f"{config.ORDER_EXCHANGE} spot coins vs {config.ORDER_QUOTE}: {sorted(bases)}")

    symbols = select_universe(data_ex, allowed_bases=bases)
    print(f"Top {len(symbols)} by 24h volume on {config.DATA_EXCHANGE}: {symbols}")
    prices = load_prices(data_ex, symbols, refresh=True)
    print(f"{len(prices)} hourly bars, {prices.index[0]} -> {prices.index[-1]}")
    print(f"saved to {config.DATA_FILE}")


if __name__ == "__main__":
    main()
