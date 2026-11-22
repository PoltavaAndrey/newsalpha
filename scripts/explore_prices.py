"""Exploration script: daily returns and volatility of one ticker, via our own yfinance plugin.

Usage: python scripts/explore_prices.py [TICKER] [START] [END]
Defaults: AAPL 2024-01-01 2024-12-31. The first run downloads and caches the data in data/raw/yfinance.
"""
import logging
import sys
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

# Lets the script run without `pip install -e .`: puts src/ on the import path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from newsalpha.plugins.market_data.yfinance_source import YFinanceSource  # noqa: E402

TRADING_DAYS = 252  # trading days per year, used to annualise volatility
OUT_DIR = Path("data/exploration")


def load_prices(ticker: str, start: date, end: date) -> pd.DataFrame:
    """Returns one row per trading day with prices and the daily log return."""
    ctx = SimpleNamespace(logger=logging.getLogger("explore"))  # the plugin only needs ctx.logger
    bars = YFinanceSource().fetch([ticker], start, end, ctx)
    df = pd.DataFrame(bar.model_dump() for bar in bars)
    # Bars are stamped at the session close in UTC; the trading date is the New York calendar date.
    df["date"] = df["ts"].dt.tz_convert("America/New_York").dt.date
    df = df.set_index("date")[["open", "high", "low", "close", "adj_close", "volume"]]
    # Log return: ln(P_t / P_{t-1}). Computed on adj_close, so dividends are included.
    df["log_return"] = np.log(df["adj_close"]).diff()
    return df


def summarize(df: pd.DataFrame) -> None:
    returns = df["log_return"].dropna()
    print(f"Trading days: {len(df)} ({df.index[0]} .. {df.index[-1]})")
    print(f"First / last close (as traded, split-adjusted): {df['close'].iloc[0]:.2f} / {df['close'].iloc[-1]:.2f}")
    print(f"First / last adj_close (dividends included):    {df['adj_close'].iloc[0]:.2f} / {df['adj_close'].iloc[-1]:.2f}")
    print(f"Mean daily log return: {returns.mean():+.4%}, daily std: {returns.std():.4%}")
    print(f"Annualised volatility: {returns.std() * np.sqrt(TRADING_DAYS):.1%}")
    print("\nFive largest daily moves (by absolute size):")
    for day in returns.abs().nlargest(5).index:
        print(f"  {day}: {returns[day]:+.2%}")


def plot(df: pd.DataFrame, ticker: str) -> None:
    try:
        import matplotlib

        matplotlib.use("Agg")  # no GUI window needed: we only save a file
        import matplotlib.pyplot as plt
    except ImportError:
        print("\nmatplotlib is not installed, chart skipped (pip install matplotlib)")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    top.plot(df.index, df["adj_close"])
    top.set_title(f"{ticker}: adjusted close")
    bottom.bar(df.index, df["log_return"])
    bottom.set_title("Daily log return")
    fig.tight_layout()
    path = OUT_DIR / f"{ticker}_prices.png"
    fig.savefig(path, dpi=120)
    print(f"\nChart saved to {path}")


def main(ticker: str, start: date, end: date) -> None:
    df = load_prices(ticker, start, end)
    summarize(df)
    plot(df, ticker)


if __name__ == "__main__":
    args = sys.argv[1:]
    main(
        args[0] if len(args) > 0 else "AAPL",
        date.fromisoformat(args[1]) if len(args) > 1 else date(2024, 1, 1),
        date.fromisoformat(args[2]) if len(args) > 2 else date(2024, 12, 31),
    )