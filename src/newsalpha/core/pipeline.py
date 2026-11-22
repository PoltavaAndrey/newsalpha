from dataclasses import dataclass, field
from typing import Protocol


# Maps a config section to a registry plugin kind (single source of truth).
SECTION_TO_KIND = {
    "news_sources": "news_source",
    "market_sources": "market_source",
    "text_processors": "text_processor",
    "sentiment": "sentiment",
    "analyzers": "analyzer",
    "exporters": "exporter",
}


class Stage(Protocol):
    name: str

    def execute(self, ctx: "RunContext") -> "StageReport": ...


@dataclass
class StageReport:
    stage: str
    duration_s: float
    errors: list[str] = field(default_factory=list)


@dataclass
class RunReport:
    run_id: str
    stages: list[StageReport] = field(default_factory=list)


class Pipeline:
    STAGE_ORDER = ["ingest", "preprocess", "enrich", "align", "analyze", "export"]

    def __init__(self, cfg, registry, storage):
        self.cfg, self.storage = cfg, storage
        # Fail early: all plugins are created (and validated) before any work starts.
        self.stages: list[Stage] = build_stages(cfg, registry)

    def run(self, only: set[str] | None = None) -> RunReport:
        self._validate_only(only)
        ctx = RunContext(config=self.cfg, storage=self.storage)
        report = RunReport(run_id=ctx.run_id)
        for stage in self.stages:
            if only and stage.name not in only:
                continue
            report.stages.append(stage.execute(ctx))
        return report

    def _validate_only(self, only):
        unknown = (only or set()) - set(self.STAGE_ORDER)
        if unknown:
            raise ConfigError(f"Unknown stages: {sorted(unknown)}")