class Pipeline:
    def __init__(self, cfg, registry, storage): ...
    def run(self, only: set[str] | None = None) -> RunReport:
        ctx = RunContext.create(self.cfg, self.storage)
        for stage in self.stages:          # ingest → preprocess → enrich → align → analyze → export
            if only and stage.name not in only: continue
            stage.execute(ctx)
        return ctx.report()