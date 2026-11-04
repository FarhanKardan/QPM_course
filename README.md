# QPM Crypto Lab

از انتخاب نماد تا اجرای زنده، در هفت قدم کوچک. جلسه‌ی پایانی دوره‌ی **مدیریت کمی پرتفوی** (THALES × Quant Circle).

```
انتخاب نمادها ← مدل پرتفوی ← بک‌تست (Vectorized و Event-driven) ← بهینه‌سازی ← مونت‌کارلو ← اجرای زنده
```

## نصب

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

**حالت پیش‌فرض: Paper Trading.** سفارش‌ها روی اردربوک **زنده‌ی Bybit** شبیه‌سازی می‌شوند و هیچ حساب، کلید یا ثبت‌نامی لازم نیست. موجودی حساب کاغذی (۱۰٬۰۰۰ USDT) در `data/paper_account.json` می‌ماند؛ برای شروع از صفر، این فایل را پاک کن.

قوانین شبیه‌سازی (`qpm/paper.py`):

| سفارش | رفتار |
|---|---|
| Market | روی سطوح اردربوک راه می‌رود تا کامل پر شود |
| Limit | بخشی که الان کراس می‌کند پر می‌شود، بقیه در دفتر می‌ماند |
| Post-only | اگر کراس کند رد می‌شود |
| IOC | آنچه الان ممکن است پر می‌شود، بقیه کنسل |
| FOK | همه یا هیچ |
| Stop-limit | تا قیمت به trigger نرسد فعال نمی‌شود |

**حالت testnet (اختیاری):** اگر حساب دمو در یک صرافی داری، در `config.py` بگذار `EXECUTION = "testnet"` و `TESTNET_EXCHANGE` را تنظیم کن (پیش‌فرض OKX Demo Trading). بعد `cp .env.example .env` و کلیدها را وارد کن.

> داده‌ی تاریخی و اردربوک از API عمومی Bybit خوانده می‌شود که از امارات باز است و کلید نمی‌خواهد.

## قدم‌ها

| قدم | فایل | چه می‌کند |
|---|---|---|
| ۱ | `01_order_types.py` | همه‌ی انواع سفارش: Limit، Post-only، IOC، FOK، Stop-limit، Market |
| ۲ | `02_universe_and_data.py` | انتخاب ۸ جفت‌ارز پرحجم USDT و دانلود داده‌ی ساعتی ۱۸۰ روز |
| ۳ | `03_backtest_vectorized.py` | مقایسه‌ی چهار مدل پرتفوی با بک‌تست سریع |
| ۴ | `04_backtest_event.py` | همان استراتژی به‌صورت event-driven و مقایسه با vectorized |
| ۵ | `05_optimize.py` | انتخاب مدل و پارامترها روی train و سنجش روی test |
| ۶ | `06_monte_carlo.py` | توزیع بازده و افت سرمایه‌ی یک‌ساله با bootstrap |
| ۷ | `07_live.py` | اجرای زنده: هر N ساعت بهینه‌سازی دوباره و معامله‌ی اختلاف |

```bash
python 01_order_types.py            # فقط نشان می‌دهد چه می‌فرستد
python 01_order_types.py --send     # ارسال به حساب کاغذی (یا testnet)
python 02_universe_and_data.py
python 03_backtest_vectorized.py
python 04_backtest_event.py
python 05_optimize.py
python 06_monte_carlo.py
python 07_live.py --once            # یک ریبالانس، dry-run
python 07_live.py --once --send     # یک ریبالانس روی حساب کاغذی (یا testnet)
```

بدون اینترنت؟ قدم‌های ۳ تا ۶ را با `--synthetic` روی داده‌ی ساختگی اجرا کن.

## مدل‌های پرتفوی (`qpm/models.py`)

| مدل | ایده |
|---|---|
| `equal` | وزن برابر؛ بنچمارک ساده |
| `inverse_vol` | وزن ∝ ۱/نوسان؛ Risk Parity ساده (پیش‌فرض) |
| `min_variance` | Markowitz حداقل واریانس |
| `max_sharpe` | Markowitz بیشترین شارپ؛ حساس‌ترین به خطای تخمین |

همه‌ی تنظیمات در `config.py` است: مدل، طول پنجره (`LOOKBACK_H`)، فاصله‌ی ریبالانس (`REBALANCE_H`)، کارمزد و slippage.

## معماری

```
qpm/
├── exchange.py            اتصال ccxt: داده‌ی عمومی، و مقصد سفارش (paper یا testnet)
├── paper.py               صرافی کاغذی روی اردربوک زنده
├── orders.py              یک تابع برای هر نوع سفارش + TWAP
├── data.py                انتخاب نماد و دانلود داده
├── models.py              مدل‌های وزن‌دهی
├── strategy.py            استراتژی: هر N ساعت، پنجره‌ی L ساعته، مدل M
├── backtest_vectorized.py بک‌تست ماتریسی
├── backtest_event.py      بک‌تست رویدادمحور: Market → Fill → Signal → Order
├── research.py            grid search و مونت‌کارلو
└── live.py                LiveBroker: همان رابط SimBroker، ولی واقعی
```

**نکته‌ی اصلی طراحی:** کلاس `PortfolioStrategy` در هر سه جا یکی است: بک‌تست vectorized، بک‌تست event-driven و اجرای زنده. فقط broker عوض می‌شود.

### Vectorized یا Event-driven؟

| | Vectorized | Event-driven |
|---|---|---|
| سرعت | خیلی سریع | کندتر |
| وزن‌ها بین ریبالانس‌ها | ثابت (فرض ساده‌کننده) | با قیمت drift می‌کنند |
| سفارش | ندارد؛ فقط turnover × هزینه | مقدار، حداقل معامله، نقدینگی |
| زمان اجرا | close همان کندل | کندل بعدی |
| کاربرد | جست‌وجوی پارامتر | اعتبارسنجی نهایی و پل به لایو |

## صرافی دیگر

منبع داده: `EXCHANGE` در `config.py`. مقصد سفارش در حالت testnet: `TESTNET_EXCHANGE`. کد با پارامترهای یکپارچه‌ی ccxt نوشته شده است.

> این کد آموزشی است، نه توصیه‌ی سرمایه‌گذاری.
