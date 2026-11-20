from datetime import date, datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from newsalpha.core.models import Article, NewsQuery, SentimentScore, make_article_id, PriceBar


def test_article_id_ignores_tracking_and_case():
    a = make_article_id("https://Example.com/news/1/?utm_source=x#top")
    b = make_article_id("https://example.com/news/1")
    assert a == b


def test_naive_datetime_rejected():
    with pytest.raises(ValidationError):
        Article(id="1", source="s", url="u", title="t",
                published_at=datetime(2024, 1, 1), fetched_at=datetime.now(timezone.utc))


def test_datetime_converted_to_utc():
    tz = timezone(timedelta(hours=2))
    art = Article(id="1", source="s", url="u", title="t",
                  published_at=datetime(2024, 1, 1, 12, tzinfo=tz),
                  fetched_at=datetime.now(timezone.utc))
    assert art.published_at.hour == 10 and art.published_at.tzinfo == timezone.utc


def test_models_are_frozen():
    s = SentimentScore(article_id="1", model="m", label="pos", score=0.5)
    with pytest.raises(ValidationError):
        s.score = 0.9


def test_score_range():
    with pytest.raises(ValidationError):
        SentimentScore(article_id="1", model="m", label="pos", score=2)


def test_query_period_validation():
    with pytest.raises(ValidationError):
        NewsQuery(start=date(2024, 2, 1), end=date(2024, 1, 1))


def test_price_bar_low_high_validation():
    with pytest.raises(ValidationError):
        PriceBar(ticker="AAPL", ts=datetime.now(timezone.utc), open=100, high=90, low=95, close=92)