"""RunContext: everything the plugin needs to know about the current run."""
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from newsalpha.core.config import AppConfig


def _new_run_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:6]}"


@dataclass
class RunContext:
    config: AppConfig
    run_id: str = field(default_factory=_new_run_id)
    storage: Any = None  # At stage 2, we will replace it with the Storage interface.
    logger: logging.Logger = field(default_factory=lambda: logging.getLogger("newsalpha"))