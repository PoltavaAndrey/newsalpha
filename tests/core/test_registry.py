import pytest

from newsalpha.core.errors import DuplicatePluginError, PluginNotFoundError, PluginInterfaceError, PluginInitError
from newsalpha.core.registry import PluginRegistry


def make_registry():
    reg = PluginRegistry()

    @reg.register("news_source", "fake")
    class FakeSource:
        def __init__(self, n: int = 1):
            self.n = n

        def fetch(self, query, ctx):
            return []

    return reg


def test_runtime_check_does_not_validate_signature():
    reg = PluginRegistry()

    @reg.register("news_source", "bad_signature")
    class BadSignature:
        def fetch(self): # wrong: no query and ctx parameters 
            ...
    
    source = reg.create("news_source", "bad_signature")

    with pytest.raises(TypeError):
        source.fetch("query", "ctx")

def test_create_with_params_and_name_injected():
    reg = make_registry()
    src = reg.create("news_source", "fake", n=3)
    assert src.n == 3 and src.name == "fake"


def test_unknown_plugin_lists_available():
    reg = make_registry()
    with pytest.raises(PluginNotFoundError, match="fake"):
        reg.get("news_source", "nope")


def test_duplicate_registration():
    reg = make_registry()
    with pytest.raises(DuplicatePluginError):
        reg.register("news_source", "fake")(type("Other", (), {}))


def test_unknown_kind():
    with pytest.raises(ValueError):
        PluginRegistry().register("banana", "x")


def test_interface_check_on_create():
    reg = PluginRegistry()

    @reg.register("news_source", "broken")
    class Broken:  # there is no fetch method
        pass

    with pytest.raises(PluginInterfaceError):
        reg.create("news_source", "broken")
 

def test_wrong_init_params():
    reg = make_registry()

    with pytest.raises(PluginInitError):
        reg.create("news_source", "fake", wrong_param=1)