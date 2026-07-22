"""Tests for the open registries: functions, providers, node kinds."""
from typing import Literal

import pytest
from pydantic import Field

from aiogram_dialog_manager.spec import (
    EvaluableNode,
    FunctionRegistry,
    NodeRegistry,
    ProviderRegistry,
    SpecValidationError,
    UnknownFunctionError,
    UnknownNodeTypeError,
    UnknownProviderError,
)


class TestNamedCallableRegistry:
    def test_register_and_get(self):
        registry = FunctionRegistry()
        registry.register("double", lambda x: x * 2)
        assert registry.get("double")(21) == 42

    def test_register_duplicate_raises(self):
        registry = FunctionRegistry({"f": len})
        with pytest.raises(SpecValidationError, match="function 'f' is already registered"):
            registry.register("f", str)

    def test_register_replace(self):
        registry = FunctionRegistry({"f": len})
        registry.register("f", str, replace=True)
        assert registry.get("f") is str

    def test_decorator(self):
        registry = FunctionRegistry()

        @registry.decorator("triple")
        def triple(x):
            return x * 3

        assert registry.get("triple") is triple

    def test_get_missing_function_raises(self):
        with pytest.raises(UnknownFunctionError, match="function 'nope' is not registered"):
            FunctionRegistry().get("nope")

    def test_get_missing_provider_raises(self):
        with pytest.raises(UnknownProviderError, match="provider 'nope' is not registered"):
            ProviderRegistry().get("nope")

    def test_contains(self):
        registry = FunctionRegistry({"f": len})
        assert "f" in registry
        assert "g" not in registry

    def test_copy_is_independent(self):
        registry = FunctionRegistry({"f": len})
        clone = registry.copy()
        clone.register("g", str)
        assert isinstance(clone, FunctionRegistry)
        assert "g" in clone
        assert "g" not in registry


class TestNodeRegistry:
    def test_register_and_create(self):
        registry = NodeRegistry()

        @registry.register
        class MyNode(EvaluableNode):
            type: Literal["my_node"] = "my_node"
            value: int = 0

        node = registry.create({"type": "my_node", "value": 5})
        assert isinstance(node, MyNode)
        assert node.value == 5
        assert "my_node" in registry
        assert "other" not in registry

    def test_register_duplicate_raises(self):
        registry = NodeRegistry()

        class ANode(EvaluableNode):
            type: Literal["a"] = "a"

        registry.register(ANode)
        with pytest.raises(SpecValidationError, match="Node type 'a' is already registered"):
            registry.register(ANode)

    def test_register_replace(self):
        registry = NodeRegistry()

        class ANode(EvaluableNode):
            type: Literal["a"] = "a"

        registry.register(ANode)
        registry.register(ANode, replace=True)
        assert registry.get("a") is ANode

    def test_register_without_type_default_raises(self):
        registry = NodeRegistry()

        class BadNode(EvaluableNode):
            type: str = Field(...)

        with pytest.raises(SpecValidationError, match="string literal default"):
            registry.register(BadNode)

    def test_get_missing_raises(self):
        with pytest.raises(UnknownNodeTypeError, match="Node type 'ghost' is not registered"):
            NodeRegistry().get("ghost")
