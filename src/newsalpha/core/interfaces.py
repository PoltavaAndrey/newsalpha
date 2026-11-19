"""Plugin contracts. The core knows only these interfaces, not the specific implementations."""
from collections.abc import Iterable
from datetime import date
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from newsalpha.core.models import (
    AnalysisResult,
    Article,
    NewsQuery,
    PriceBar,
    SentimentScore,
)

if TYPE_CHECKING:
    import pandas as pd

    from newsalpha.core.context import RunContext


@runtime_checkable
class NewsSource(Protocol):
    name: str

    def fetch(self, query: NewsQuery, ctx: "RunContext") -> Iterable[Article]: ...


@runtime_checkable
class MarketDataSource(Protocol):
    name: str

    def fetch(
        self, tickers: list[str], start: date, end: date, ctx: "RunContext"
    ) -> Iterable[PriceBar]: ...


@runtime_checkable
class TextProcessor(Protocol):
    name: str

    def process(self, articles: Iterable[Article], ctx: "RunContext") -> Iterable[Article]: ...


@runtime_checkable
class SentimentAnalyzer(Protocol):
    name: str

    def score(
        self, articles: Iterable[Article], ctx: "RunContext"
    ) -> Iterable[SentimentScore]: ...


@runtime_checkable
class Analyzer(Protocol):
    name: str

    def run(self, dataset: "pd.DataFrame", ctx: "RunContext") -> AnalysisResult: ...


@runtime_checkable
class Exporter(Protocol):
    name: str

    def export(self, tables: "dict[str, pd.DataFrame]", ctx: "RunContext") -> None: ...


# The "plugin type -> interface" mapping: the registry uses this to verify the objects that have been created.
PROTOCOLS: dict[str, type] = {
    "news_source": NewsSource,
    "market_source": MarketDataSource,
    "text_processor": TextProcessor,
    "sentiment": SentimentAnalyzer,
    "analyzer": Analyzer,
    "exporter": Exporter,
}