"""Shared fixtures for spec subsystem tests."""
import pytest

from aiogram_dialog_manager.spec import EvalScope, ProviderRegistry, SpecRuntime, create_default_function_registry


class FakeDialog:
    """A minimal stand-in for DialogOperator: expression evaluation only needs ``.data``."""

    def __init__(self, data=None):
        self.data = data or {}


@pytest.fixture
def make_scope():
    def factory(*, data=None, context=None, locals_=None, defs=None, translator=None, providers=None, window_name="win", dialog_name="dlg"):
        runtime = SpecRuntime(
            dialog_name=dialog_name,
            defs=defs or {},
            functions=create_default_function_registry(),
            providers=providers or ProviderRegistry(),
            translator=translator,
        )
        return EvalScope(
            runtime=runtime,
            dialog=FakeDialog(data) if data is not None else None,
            context=context or {},
            window_name=window_name,
            locals=locals_ or {},
        )
    return factory


@pytest.fixture
def scope(make_scope):
    return make_scope(data={})
