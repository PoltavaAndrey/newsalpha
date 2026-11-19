"""Configuration: YAML -> validated Pydantic models."""
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from newsalpha.core.errors import ConfigError


class _Strict(BaseModel):
    # extra="forbid": A typo in YAML results in an immediate error, rather than being silently ignored.
    model_config = ConfigDict(extra="forbid")


class PluginSpec(_Strict):
    plugin: str
    params: dict[str, Any] = Field(default_factory=dict)


class RunSection(_Strict):
    name: str
    seed: int = 42


class CompanyConfig(_Strict):
    name: str
    tickers: list[str] = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)


class PeriodConfig(_Strict):
    start: date
    end: date

    @model_validator(mode="after")
    def _check(self) -> "PeriodConfig":
        if self.end < self.start:
            raise ValueError("period.end must be >= period.start")
        return self


class PipelineConfig(_Strict):
    news_sources: list[PluginSpec] = Field(default_factory=list)
    market_sources: list[PluginSpec] = Field(default_factory=list)
    text_processors: list[PluginSpec] = Field(default_factory=list)
    sentiment: list[PluginSpec] = Field(default_factory=list)
    analyzers: list[PluginSpec] = Field(default_factory=list)
    exporters: list[PluginSpec] = Field(default_factory=list)


class AppConfig(_Strict):
    run: RunSection
    company: CompanyConfig
    period: PeriodConfig
    pipeline: PipelineConfig = Field(default_factory=PipelineConfig)
    # modules with plugins that need to be imported for @register to work
    plugin_modules: list[str] = Field(default_factory=list)


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merges dictionaries; lists and scalars from override replace base."""
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def load_config(*paths: str | Path) -> AppConfig:
    """Loads one or more YAML files; later files override earlier ones."""
    merged: dict[str, Any] = {}
    for path in paths:
        try:
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except OSError as e:
            raise ConfigError(f"Cannot read config {path}: {e}") from e
        merged = deep_merge(merged, data)
    try:
        return AppConfig.model_validate(merged)
    except ValidationError as e:
        raise ConfigError(f"Invalid config: {e}") from e