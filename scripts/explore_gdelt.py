"""Exploration script (NOT a plugin yet): what does GDELT DOC 2.0 actually return?

Goals:
1. Find out whether article-list mode reaches back to the period we need (probe, see below).
2. See the real fields, the number of records per request and how `seendate` looks.
3. See which domains dominate. Findings will shape the future `news_source` plugin.

Usage: python scripts/explore_gdelt.py 2024-01-08 2024-01-14
"""
import sys
import time
from collections import Counter
from datetime import date, timedelta

import requests

URL = "https://api.gdeltproject.org/api/v2/doc/doc"
# OR-groups must be wrapped in parentheses in GDELT query syntax.
# GDELT rejects phrases shorter than 5 characters ("The specified phrase is too short"), so no "AAPL".
QUERY = '("Apple Inc" OR "iPhone" OR "Apple stock") sourcelang:english'
MAX_RECORDS = 250  # believed to be the API cap per request; the output below will confirm or refute it

PAUSE = 6  # seconds between requests: GDELT asks for roughly one request per 5 seconds
THROTTLE_PAUSE = 30  # seconds to wait after a "slow down" answer before retrying
MAX_ATTEMPTS = 3


def request_articles(start: date, end: date, max_records: int = MAX_RECORDS) -> list[dict]:
    """Fetches articles first seen in [start, end] (both inclusive); retries when throttled."""
    params = {
        "query": QUERY,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": max_records,
        "sort": "DateAsc",
        "startdatetime": start.strftime("%Y%m%d") + "000000",
        "enddatetime": end.strftime("%Y%m%d") + "235959",
    }
    for attempt in range(1, MAX_ATTEMPTS + 1):
        response = requests.get(URL, params=params, timeout=60)
        # GDELT may signal throttling with HTTP 429 or with a plain-text "please limit requests" body.
        body_start = response.text.lstrip()[:60].lower()
        if response.status_code == 429 or body_start.startswith("please limit"):
            print(f"  throttled (attempt {attempt}/{MAX_ATTEMPTS}), waiting {THROTTLE_PAUSE}s...")
            time.sleep(THROTTLE_PAUSE)
            continue
        response.raise_for_status()
        try:
            return response.json().get("articles", [])
        except ValueError:
            # On other errors (e.g. a bad query) GDELT answers with plain text, not JSON.
            # Fail loudly: returning [] here would look like "no articles" and hide the real problem.
            raise RuntimeError(f"GDELT rejected the request: {response.text[:300]!r}") from None
    raise RuntimeError("GDELT keeps throttling us: wait a few minutes or try another network")


def probe_coverage(start: date) -> bool:
    """Compares a recent day with the requested one: does article-list mode reach that far back?"""
    recent = date.today() - timedelta(days=7)
    counts = {}
    for label, day in (("recent", recent), ("requested", start)):
        counts[label] = len(request_articles(day, day, max_records=10))
        print(f"probe, {label} day {day}: {counts[label]} articles")
        time.sleep(PAUSE)
    if counts["recent"] > 0 and counts["requested"] == 0:
        print("\nRecent days work, the requested day is empty: article-list mode probably does not "
              "reach that period. Stopping; we need another source for historical headlines.")
        return False
    return True


def main(start: date, end: date) -> None:
    if not probe_coverage(start):
        return

    articles: list[dict] = []
    day = start
    while day <= end:
        batch = request_articles(day, day)  # one day per request
        print(f"{day}: {len(batch)} articles")
        articles.extend(batch)
        day += timedelta(days=1)
        time.sleep(PAUSE)

    if not articles:
        return
    print("\nFields of one record:", sorted(articles[0]))
    print("seendate examples:", [a["seendate"] for a in articles[:3]])
    print("Top domains:", Counter(a["domain"] for a in articles).most_common(8))
    print("\nFirst titles:")
    for a in articles[:5]:
        print(" -", a["title"])


if __name__ == "__main__":
    first, last = (date.fromisoformat(arg) for arg in sys.argv[1:3])
    main(first, last)