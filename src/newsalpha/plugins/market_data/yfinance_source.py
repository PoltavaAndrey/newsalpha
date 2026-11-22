"""Market data source backed by yfinance (daily bars only, for now).

Design notes:
- yfinance is an unofficial scraper of Yahoo Finance, so every successful download is cached
  to disk (the "raw" layer): re-runs are reproducible and do not hammer Yahoo.
- Both `Close` (split-adjusted) and `Adj Close` (split- and dividend-adjusted) are kept.
- `end` follows the project convention (inclusive), while yfinance treats it as exclusive.
"""
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pandas as pd

from newsalpha.core.errors import NewsAlphaError, PluginInitError
from newsalpha.core.models import PriceBar
from newsalpha.core.registry import register

if TYPE_CHECKING:
    from newsalpha.core.context import RunContext

NEW_YORK = ZoneInfo("America/New_York")

# A daily bar only becomes known after the session closes, so we stamp it with the close time.
# Early-close days (13:00) get a later timestamp than reality: the safe direction for look-ahead.
MARKET_CLOSE = time(16, 0)

PRICE_COLUMNS = ["Open", "High", "Low", "Close", "Adj Close"]
ALL_COLUMNS = [*PRICE_COLUMNS, "Volume"]


@register("market_source", "yfinance")
class YFinanceSource:
    name: str  # injected by the @register decorator

    def __init__(
        self,
        interval: str = "1d",
        cache_dir: str = "data/raw/yfinance",
        refresh: bool = False,
    ) -> None:
        if interval != "1d":
            raise PluginInitError(f"yfinance plugin supports only interval='1d' for now, got {interval!r}")
        self.interval = interval
        self.cache_dir = Path(cache_dir)
        self.refresh = refresh  # True = ignore the cache and download again

    def fetch(
        self, tickers: list[str], start: date, end: date, ctx: "RunContext"
    ) -> Iterable[PriceBar]:
        # A generator: bars are produced lazily, run_guarded() forces it with list().
        for ticker in tickers:
            frame = self._load(ticker, start, end, ctx)
            yield from self._to_bars(ticker, frame, ctx)

    def _load(self, ticker: str, start: date, end: date, ctx: "RunContext") -> pd.DataFrame:
        path = self.cache_dir / f"{ticker}_{self.interval}_{start}_{end}.csv"
        # A range that reaches today contains a partial (still forming) bar: never cache it.
        cacheable = end < date.today()

        if cacheable and not self.refresh and path.exists():
            ctx.logger.info("yfinance: %s loaded from cache %s", ticker, path)
            return pd.read_csv(path, index_col="Date", parse_dates=True)

        frame = self._download(ticker, start, end)
        if frame.empty:
            # An empty answer usually means a wrong ticker or Yahoo throttling: fail loudly.
            raise NewsAlphaError(f"yfinance returned no data for {ticker} ({start}..{end})")

        if cacheable:
            path.parent.mkdir(parents=True, exist_ok=True)
            frame.to_csv(path)
        return frame

    def _download(self, ticker: str, start: date, end: date) -> pd.DataFrame:
        import yfinance as yf  # imported lazily: the module stays importable without the package

        frame = yf.Ticker(ticker).history(
            start=start.isoformat(),
            end=(end + timedelta(days=1)).isoformat(),  # yfinance treats `end` as exclusive
            interval=self.interval,
            auto_adjust=False,  # keep both Close and Adj Close
            actions=False,  # no dividend / split columns
        )
        if frame.empty:
            return frame
        # The daily index is midnight in New York; drop the tz but keep the local calendar date.
        frame = frame[ALL_COLUMNS]
        frame.index = frame.index.tz_localize(None)
        frame.index.name = "Date"
        return frame

    @staticmethod
    def _to_bars(ticker: str, frame: pd.DataFrame, ctx: "RunContext") -> Iterable[PriceBar]:
        for day, row in frame.iterrows():
            if row[PRICE_COLUMNS].isna().any():
                ctx.logger.warning("yfinance: %s %s has NaN prices, bar skipped", ticker, day.date())
                continue
            yield PriceBar(
                ticker=ticker,
                ts=datetime.combine(day.date(), MARKET_CLOSE, tzinfo=NEW_YORK),
                open=float(row["Open"]),
                high=float(row["High"]),
                low=float(row["Low"]),
                close=float(row["Close"]),
                adj_close=float(row["Adj Close"]),
                volume=None if pd.isna(row["Volume"]) else float(row["Volume"]),
            )