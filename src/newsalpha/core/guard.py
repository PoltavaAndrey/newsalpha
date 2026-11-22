# core/guard.py
"""Run-wide error policy for plugin calls."""
from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from newsalpha.core.models import PluginFailure

if TYPE_CHECKING:
    # Only needed for annotations: everything else is reached through ctx.
    from newsalpha.core.context import RunContext


def run_guarded(
    ctx: "RunContext",
    stage: str,
    plugin: Any,
    fn: Callable[[], Iterable[Any]],
    *,
    required: bool = False,
    default: list[Any] | None = None,
) -> list[Any]:
    """Runs one plugin call under the run-wide error policy.

    - on_error == "fail_fast" or required=True: the exception is re-raised.
    - on_error == "skip_and_log": the failure is recorded in ctx.errors and
      `default` is returned (an empty list if not given).
    """
    try:
        # list() forces lazy generators to run inside the try block.
        return list(fn())
    except Exception as exc:  # not BaseException: Ctrl+C must still stop the run
        ctx.logger.exception("Plugin %s failed in stage %s", plugin.name, stage)
        if required or ctx.config.run.on_error == "fail_fast":
            raise
        ctx.errors.append(PluginFailure(stage=stage, plugin=plugin.name, error=repr(exc)))
        return [] if default is None else default