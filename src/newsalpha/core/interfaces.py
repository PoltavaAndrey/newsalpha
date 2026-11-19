class NewsSource(Protocol):
    name: str
    def fetch(self, query: NewsQuery, ctx: RunContext) -> Iterable[Article]: ...

class MarketDataSource(Protocol):
    name: str
    def fetch(self, tickers: list[str], start: date, end: date,
              ctx: RunContext) -> Iterable[PriceBar]: ...

class TextProcessor(Protocol):
    name: str
    def process(self, articles: Iterable[Article], ctx: RunContext) -> Iterable[Article]: ...

class SentimentAnalyzer(Protocol):
    name: str
    def score(self, articles: Iterable[Article], ctx: RunContext) -> Iterable[SentimentScore]: ...

class Analyzer(Protocol):
    name: str
    def run(self, dataset: pd.DataFrame, ctx: RunContext) -> AnalysisResult: ...

class Exporter(Protocol):
    name: str
    def export(self, tables: dict[str, pd.DataFrame], ctx: RunContext) -> None: ...