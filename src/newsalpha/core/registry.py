"""Plugin registry: (kind, name) -> class."""
import importlib
from collections.abc import Callable, Iterable
from typing import Any, TypeVar

from newsalpha.core.errors import DuplicatePluginError, PluginNotFoundError
from newsalpha.core.interfaces import PROTOCOLS

T = TypeVar("T", bound=type)


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[tuple[str, str], type] = {}

    def register(self, kind: str, name: str) -> Callable[[T], T]:
        """Registration decorator: @registry.register("news_source", "rss")."""
        if kind not in PROTOCOLS:
            raise ValueError(f"Unknown plugin kind {kind!r}. Known: {sorted(PROTOCOLS)}")

        def decorator(cls: T) -> T:
            key = (kind, name)
            if key in self._plugins:
                raise DuplicatePluginError(f"Plugin {key} is already registered")
            cls.name = name  # type: ignore[attr-defined]
            self._plugins[key] = cls
            return cls

        return decorator

    def get(self, kind: str, name: str) -> type:
        try:
            return self._plugins[(kind, name)]
        except KeyError:
            available = self.names(kind)
            raise PluginNotFoundError(
                f"No {kind} plugin named {name!r}. Available: {available}"
            ) from None

    def create(self, kind: str, name: str, **params: Any) -> Any:
        """Factory: creates an instance and checks that it satisfies the interface."""
        instance = self.get(kind, name)(**params)
        if not isinstance(instance, PROTOCOLS[kind]):
            raise TypeError(f"{name!r} does not satisfy the {kind} interface")
        return instance

    def names(self, kind: str) -> list[str]:
        return sorted(n for (k, n) in self._plugins if k == kind)


def load_plugin_modules(modules: Iterable[str]) -> None:
    """Registration decorator is called when the module is imported, so plugins modules need to be imported."""
    for module in modules:
        importlib.import_module(module)


# Global plugin registry; a fresh PluginRegistry() is created in tests.
registry = PluginRegistry()
register = registry.register