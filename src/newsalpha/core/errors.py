"""All exceptions in the project inherit from a single base class — making it easy to catch `except NewsAlphaError`."""


class NewsAlphaError(Exception):
    """Base error for the project."""


class ConfigError(NewsAlphaError):
    """Config not found or failed validation."""


class PluginNotFoundError(NewsAlphaError):
    """Requested plugin not found in the registry."""


class DuplicatePluginError(NewsAlphaError):
    """Two plugins registered under the same (kind, name)."""


class PluginInterfaceError(NewsAlphaError):
    """Plugin class does not satisfy the interface of its kind."""


class PluginInitError(NewsAlphaError):
    """Plugin could not be created with the given params."""