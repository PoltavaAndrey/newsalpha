"""Offline tests: the real `yfinance` module is replaced by a fake one, so no network is needed."""
import logging
import sys
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pandas as pd
import pytest

import newsalpha.plugins.market_data.yfinance_source  # noqa: F401  (importing registers the plugin)
from newsalpha.core.errors import NewsAlphaError, PluginInitError
from newsalpha.core.registry import registry

CTX = SimpleNamespace(logger=logging.getLogger("test"))
START, END = date(2024, 1, 2), date(2024, 12, 31)


def make_frame() -> pd.DataFrame:
    """Looks like Ticker.history(auto_adjust=False): tz-aware midnight New York index."""
    index = pd.DatetimeIndex(["2024-01-02", "2024-07-01"], tz="America/New_York")
    return pd.DataFrame(
        {
            "Open": [185.0, 210.0],
            "High": [186.0, 212.0],
            "Low": [183.0, 209.0],
            "Close": [185.2, 211.0],
            "Adj Close": [184.2, 210.5],
            "Volume": [79_000_000.0, 60_000_000.0],
        },
        index=index,
    )


@pytest.fixture
def fake_yf(monkeypatch):
    state = SimpleNamespace(calls=[], frame=make_frame())

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol

        def history(self, **kwargs):
            state.calls.append((self.symbol, kwargs))
            return state.frame.copy()

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(Ticker=FakeTicker))
    return state


def make_source(tmp_path, **params):
    # Always point the cache to tmp_path so tests never write into the real data/ folder.
    return registry.create("market_source", "yfinance", cache_dir=str(tmp_path), **params)


def fetch(source, tickers=("AAPL",), start=START, end=END):
    return list(source.fetch(list(tickers), start, end, CTX))


def test_registered_and_satisfies_protocol(tmp_path):
    assert make_source(tmp_path).name == "yfinance"


def test_unsupported_interval(tmp_path):
    with pytest.raises(PluginInitError):
        make_source(tmp_path, interval="1h")


def test_end_date_is_inclusive_for_us(fake_yf, tmp_path):
    fetch(make_source(tmp_path))
    _, kwargs = fake_yf.calls[0]
    assert kwargs["start"] == "2024-01-02"
    assert kwargs["end"] == "2025-01-01"  # yfinance `end` is exclusive, so we add one day
    assert kwargs["auto_adjust"] is False


def test_timestamp_is_session_close_in_utc(fake_yf, tmp_path):
    winter, summer = fetch(make_source(tmp_path))
    assert winter.ts == datetime(2024, 1, 2, 21, 0, tzinfo=timezone.utc)  # 16:00 EST = 21:00 UTC
    assert summer.ts == datetime(2024, 7, 1, 20, 0, tzinfo=timezone.utc)  # 16:00 EDT = 20:00 UTC


def test_close_and_adj_close_are_both_kept(fake_yf, tmp_path):
    bar = fetch(make_source(tmp_path))[0]
    assert bar.close == 185.2 and bar.adj_close == 184.2 and bar.volume == 79_000_000.0


def test_nan_bar_is_skipped(fake_yf, tmp_path):
    fake_yf.frame.iloc[0, fake_yf.frame.columns.get_loc("Close")] = float("nan")
    assert len(fetch(make_source(tmp_path))) == 1


def test_empty_answer_raises(fake_yf, tmp_path):
    fake_yf.frame = fake_yf.frame.iloc[0:0]
    with pytest.raises(NewsAlphaError):
        fetch(make_source(tmp_path))


def test_second_run_reads_cache(fake_yf, tmp_path):
    source = make_source(tmp_path)
    first = fetch(source)
    second = fetch(source)
    assert len(fake_yf.calls) == 1  # the second run did not touch "Yahoo"
    assert first == second


def test_refresh_ignores_cache(fake_yf, tmp_path):
    fetch(make_source(tmp_path))
    fetch(make_source(tmp_path, refresh=True))
    assert len(fake_yf.calls) == 2


def test_range_reaching_today_is_not_cached(fake_yf, tmp_path):
    fetch(make_source(tmp_path), end=date.today())
    assert list(tmp_path.iterdir()) == []