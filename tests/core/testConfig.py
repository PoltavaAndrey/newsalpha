import pytest

from newsalpha.core.config import load_config
from newsalpha.core.errors import ConfigError

BASE = """
run: {name: demo}
company: {name: Apple Inc., tickers: [AAPL]}
period: {start: 2024-01-01, end: 2024-12-31}
pipeline:
  news_sources:
    - {plugin: rss, params: {feeds: ["https://example.com/rss"]}}
"""


def write(tmp_path, name, text):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_load_valid(tmp_path):
    cfg = load_config(write(tmp_path, "a.yaml", BASE))
    assert cfg.company.tickers == ["AAPL"]
    assert cfg.pipeline.news_sources[0].plugin == "rss"
    assert cfg.run.seed == 42


def test_override_merges(tmp_path):
    base = write(tmp_path, "base.yaml", BASE)
    exp = write(tmp_path, "exp.yaml", "run: {name: exp1}\nperiod: {end: 2024-06-30}\n")
    cfg = load_config(base, exp)
    assert cfg.run.name == "exp1" and str(cfg.period.end) == "2024-06-30"
    assert cfg.company.name == "Apple Inc."


def test_typo_in_key_is_error(tmp_path):
    bad = BASE + "  news_sorces: []\n"
    with pytest.raises(ConfigError):
        load_config(write(tmp_path, "bad.yaml", bad))


def test_missing_file():
    with pytest.raises(ConfigError):
        load_config("nope.yaml")