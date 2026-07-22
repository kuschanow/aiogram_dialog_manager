"""Open registries of the spec subsystem.

Three extension registries exist (in addition to the existing prototype
registries): expression functions, providers and node kinds. All follow the
same principle: a name -> object mapping that users can extend.
"""
from typing import Any, Callable, Optional, TYPE_CHECKING

from aiogram_dialog_manager.spec.errors import (
    SpecValidationError,
    UnknownFunctionError,
    UnknownNodeTypeError,
    UnknownProviderError,
)

if TYPE_CHECKING:
    from aiogram_dialog_manager.spec.node import SpecNode


class NamedCallableRegistry:
    """A name -> callable mapping with duplicate protection."""

    _missing_error: type[Exception] = KeyError
    _kind: str = "callable"

    def __init__(self, initial: Optional[dict[str, Callable]] = None):
        self._items: dict[str, Callable] = dict(initial or {})

    def register(self, name: str, func: Callable, *, replace: bool = False) -> Callable:
        if not replace and name in self._items:
            raise SpecValidationError(f"{self._kind} '{name}' is already registered")
        self._items[name] = func
        return func

    def decorator(self, name: str, *, replace: bool = False) -> Callable[[Callable], Callable]:
        def wrapper(func: Callable) -> Callable:
            return self.register(name, func, replace=replace)
        return wrapper

    def get(self, name: str) -> Callable:
        if name not in self._items:
            raise self._missing_error(f"{self._kind} '{name}' is not registered")
        return self._items[name]

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def copy(self) -> "NamedCallableRegistry":
        return type(self)(self._items)


class FunctionRegistry(NamedCallableRegistry):
    """Registry of pure functions available to ``call`` expression nodes."""

    _missing_error = UnknownFunctionError
    _kind = "function"


class ProviderRegistry(NamedCallableRegistry):
    """Registry of named Python providers — the escape hatch for external data.

    A provider is a callable ``(dialog, context, **kwargs) -> Any``; it may be
    a coroutine function.
    """

    _missing_error = UnknownProviderError
    _kind = "provider"


class NodeRegistry:
    """Open registry of node kinds: ``type`` value -> node class.

    Every standard node (including ``t``) is registered through this same
    public mechanism — user-defined node kinds are first-class citizens.
    """

    def __init__(self):
        self._nodes: dict[str, type] = {}

    def register(self, node_cls: "type[SpecNode]", *, replace: bool = False) -> "type[SpecNode]":
        type_name = node_cls.model_fields["type"].default
        if not isinstance(type_name, str):
            raise SpecValidationError(
                f"Node class {node_cls.__qualname__} must define a string literal default for its 'type' field"
            )
        if not replace and type_name in self._nodes:
            raise SpecValidationError(f"Node type '{type_name}' is already registered")
        self._nodes[type_name] = node_cls
        return node_cls

    def get(self, type_name: str) -> type:
        if type_name not in self._nodes:
            raise UnknownNodeTypeError(f"Node type '{type_name}' is not registered")
        return self._nodes[type_name]

    def create(self, payload: dict[str, Any]) -> "SpecNode":
        return self.get(payload["type"]).model_validate(payload)

    def __contains__(self, type_name: str) -> bool:
        return type_name in self._nodes
