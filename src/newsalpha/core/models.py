"""Data contracts: a common language between pipeline stages."""
import hashlib
from datetime import date, datetime, timezone
from typing import Annotated, Any, Literal
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator, field_validator


def _ensure_utc(dt: datetime) -> datetime:
    """We disallow "naive" time and convert everything to UTC."""
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc)


UtcDatetime = Annotated[datetime, AfterValidator(_ensure_utc)]


def canonicalize_url(url: str) -> str:
    """Converts a URL to its canonical form, ensuring that one article corresponds to one ID."""
    parts = urlsplit(url.strip())
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not k.lower().startswith("utm_")
    ]
    path = parts.path.rstrip("/") or "/"
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, urlencode(sorted(query)), "")
    )


def make_article_id(url: str) -> str:
    """Creates a stable ID for an article — the foundation of pipeline idempotency."""
    return hashlib.sha256(canonicalize_url(url).encode()).hexdigest()[:16]


class _Frozen(BaseModel):
    """Data models are immutable: a stage cannot silently corrupt others' data."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class Article(_Frozen):
    id: str
    source: str
    url: str
    title: str
    body: str | None = None
    published_at: UtcDatetime
    fetched_at: UtcDatetime
    language: str | None = None
    tickers: tuple[str, ...] = ()


class SentimentScore(_Frozen):
    article_id: str
    model: str
    label: Literal["neg", "neu", "pos"]
    score: float = Field(ge=-1.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PriceBar(_Frozen):
    ticker: str
    ts: UtcDatetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    @model_validator(mode="after")
    def _check_price(self) -> "PriceBar":
        if self.low > self.high:
            raise ValueError("low must be <= high")
        return self


class NewsQuery(_Frozen):
    """What we are asking from the news source."""

    keywords: tuple[str, ...] = ()
    tickers: tuple[str, ...] = ()
    start: date
    end: date
    limit: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def _check_period(self) -> "NewsQuery":
        if self.end < self.start:
            raise ValueError("end must be >= start")
        return self


class AnalysisResult(_Frozen):
    analyzer: str
    run_id: str
    metrics: dict[str, float] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""