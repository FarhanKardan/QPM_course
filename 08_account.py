"""Step 8 — look at the account like an exchange screen: balances, open orders, history.

In paper mode the orders live in data/paper_account.json, not on any exchange,
so this script is the "exchange UI". It also writes results/account.html.

    python 08_account.py                 # show everything
    python 08_account.py --cancel-all    # cancel every open order
    python 08_account.py --reset         # wipe the paper account (back to 10,000 USDT)
"""
import argparse
import html
import os
import webbrowser
from datetime import datetime

import pandas as pd

import config
from qpm import paper
from qpm.exchange import get_exchange, public_exchange


def balances_table(ex, prices_ex):
    rows = []
    for coin, qty in ex.fetch_balance()["total"].items():
        if not qty or abs(qty) < 1e-12:
            continue
        price = 1.0 if coin == config.QUOTE else prices_ex.fetch_ticker(f"{coin}/{config.QUOTE}")["last"]
        rows.append({"coin": coin, "amount": qty, "price": price, "value_usdt": qty * price})
    df = pd.DataFrame(rows).sort_values("value_usdt", ascending=False)
    df["weight"] = df["value_usdt"] / df["value_usdt"].sum()
    return df


def orders_table(ex):
    if config.EXECUTION != "paper":
        return pd.DataFrame(ex.fetch_open_orders())
    rows = [ex._view(o) for o in ex.orders.values()]
    cols = ["id", "symbol", "type", "side", "timeInForce", "postOnly", "price",
            "triggerPrice", "amount", "filled", "average", "status"]
    return pd.DataFrame(rows, columns=cols)


def write_html(bal, orders, equity, path=f"{config.RESULTS_DIR}/account.html"):
    def table(df):
        return df.to_html(index=False, float_format=lambda x: f"{x:,.6g}", border=0, na_rep="")
    open_o = orders[orders["status"] == "open"] if len(orders) else orders
    page = f"""<!doctype html><html><head><meta charset="utf-8"><title>Paper account</title>
<style>body{{font-family:system-ui,sans-serif;background:#0A1424;color:#EEF2F7;padding:32px}}
h1{{font-size:28px}} h2{{color:#C8F55A;font-size:20px;margin-top:32px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th{{text-align:left;color:#7CB7FF;border-bottom:1px solid #22406A;padding:6px}}
td{{border-bottom:1px solid #16263D;padding:6px;font-variant-numeric:tabular-nums}}
.eq{{font-size:40px;font-weight:700}}</style></head><body>
<h1>Paper account · {html.escape(config.EXCHANGE)} live order book</h1>
<p>updated {datetime.now():%Y-%m-%d %H:%M}</p>
<p class="eq">{equity:,.2f} {config.QUOTE}</p>
<h2>Balances</h2>{table(bal)}
<h2>Open orders ({len(open_o)})</h2>{table(open_o)}
<h2>Order history ({len(orders)})</h2>{table(orders.iloc[::-1])}
</body></html>"""
    os.makedirs(config.RESULTS_DIR, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(page)
    return path


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cancel-all", action="store_true")
    p.add_argument("--reset", action="store_true")
    p.add_argument("--no-browser", action="store_true")
    a = p.parse_args()

    if a.reset:
        if os.path.exists(paper.STATE_FILE):
            os.remove(paper.STATE_FILE)
        print(f"paper account reset to {config.INITIAL_CASH:,.0f} {config.QUOTE}")
        return

    ex = get_exchange(auth=True)
    if a.cancel_all:
        for o in ex.fetch_open_orders():
            ex.cancel_order(o["id"], o["symbol"])
            print(f"cancelled {o['symbol']} {o['side']} {o['id']}")

    bal = balances_table(ex, public_exchange())
    orders = orders_table(ex)
    equity = bal["value_usdt"].sum()

    pd.set_option("display.width", 160)
    pd.set_option("display.float_format", lambda x: f"{x:,.6g}")
    print(f"\nEQUITY  {equity:,.2f} {config.QUOTE}   (start {config.INITIAL_CASH:,.0f}, "
          f"P&L {equity - config.INITIAL_CASH:+,.2f})\n")
    print("BALANCES")
    print(bal.to_string(index=False))
    if len(orders):
        open_o = orders[orders["status"] == "open"]
        print(f"\nOPEN ORDERS ({len(open_o)})")
        print(open_o.to_string(index=False) if len(open_o) else "  none")
        print(f"\nLAST 10 ORDERS (of {len(orders)})")
        print(orders.tail(10).iloc[::-1][["symbol", "type", "side", "timeInForce",
                                         "amount", "filled", "average", "status"]].to_string(index=False))

    path = write_html(bal, orders, equity)
    print(f"\npage: {path}")
    if not a.no_browser:
        webbrowser.open("file://" + os.path.abspath(path))


if __name__ == "__main__":
    main()
