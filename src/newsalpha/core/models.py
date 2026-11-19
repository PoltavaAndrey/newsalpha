class Article(BaseModel):
    id: str                       # хеш от canonical_url
    source: str                   # имя плагина-источника
    url: HttpUrl
    title: str
    body: str | None
    published_at: datetime        # ВСЕГДА в UTC, tz-aware
    fetched_at: datetime
    language: str | None = None
    tickers: list[str] = []       # заполняет entity_linker

class SentimentScore(BaseModel):
    article_id: str
    model: str                    # "vader", "finbert", ...
    label: Literal["neg", "neu", "pos"]
    score: float                  # [-1, 1]
    confidence: float | None = None

class PriceBar(BaseModel):
    ticker: str
    ts: datetime                  # UTC
    open: float; high: float; low: float; close: float
    volume: float | None = None