"""Evaluation scope: explicit data namespaces + runtime services.

Namespaces are explicit by design (no merged scope, no name collisions):

- ``data.*`` — persistent ``dialog.data``;
- ``ctx.*``  — one-shot render context;
- local names introduced by constructs (``item``, ``index`` inside ``foreach``).

A missing path evaluates to ``None`` (a normal situation for optional data);
type errors during traversal raise — a silent ``None`` would hide script bugs.
"""
from dataclasses import dataclass, field, replace
from typing import Any, Callable, Optional, TYPE_CHECKING

from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError, UnknownPrototypeError
from aiogram_dialog_manager.spec.registries import FunctionRegistry, ProviderRegistry

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator

#: Optional hook ``(msgid, locale) -> str`` used by ``t`` nodes.
Translator = Callable[[str, Optional[str]], str]

_DATA_NAMESPACE = "data"
_CTX_NAMESPACE = "ctx"


class SpecResolver:
    """Resolves a registered prototype by ``type_name`` — the single, swappable
    seam every ``use`` reference (``button``/``menu``/``message``) goes through
    at render time.

    Subclass and override :meth:`resolve` to gate access (e.g. by script author
    and rights), plug a scoped registry, or log — then pass the instance to
    ``compile_dialog(resolver=...)``. The typical override runs a check first
    and delegates the actual lookup to ``super().resolve(...)``.

    Python prototypes are stored as classes and instantiated here (they must
    have a no-argument constructor to be usable from specs); spec entries are
    stored as ready instances.
    """

    def resolve(self, base_cls: type, name: str, scope: "Optional[EvalScope]") -> Any:
        try:
            entry = base_cls._registry[name]
        except KeyError:
            raise UnknownPrototypeError(
                f"{base_cls.__name__} name '{name}' is not registered; "
                f"'use' nodes require the target prototype to be registered"
            ) from None
        return entry() if isinstance(entry, type) else entry


@dataclass(frozen=True)
class SpecRuntime:
    """Per-dialog services shared by every render of a compiled model."""

    dialog_name: str
    defs: dict[str, Any] = field(default_factory=dict)
    functions: FunctionRegistry = field(default_factory=FunctionRegistry)
    providers: ProviderRegistry = field(default_factory=ProviderRegistry)
    translator: Optional[Translator] = None
    #: When set, every spec window stamps its own name into the message data
    #: under this key (the "window name is the state" pattern of wizards).
    window_name_key: Optional[str] = None
    #: How ``use`` references resolve registered prototypes at render time;
    #: override to gate access or plug a custom registry.
    resolver: SpecResolver = field(default_factory=SpecResolver)


@dataclass(frozen=True)
class EvalScope:
    """A single render's evaluation environment."""

    runtime: SpecRuntime
    dialog: "Optional[DialogOperator]" = None
    context: dict[str, Any] = field(default_factory=dict)
    window_name: Optional[str] = None
    locals: dict[str, Any] = field(default_factory=dict)

    def child(self, **new_locals: Any) -> "EvalScope":
        """A nested scope with additional local names (shadowing outer ones)."""
        return replace(self, locals={**self.locals, **new_locals})

    def resolve_path(self, path: str) -> Any:
        root, *parts = path.split(".")
        if root == _DATA_NAMESPACE:
            value: Any = self.dialog.data if self.dialog is not None else {}
        elif root == _CTX_NAMESPACE:
            value = self.context
        else:
            value = self.locals.get(root)
        for part in parts:
            if value is None:
                return None
            if isinstance(value, dict):
                value = value.get(part)
            elif isinstance(value, (list, tuple)) and part.lstrip("-").isdigit():
                index = int(part)
                value = value[index] if -len(value) <= index < len(value) else None
            else:
                raise ExpressionEvaluationError(
                    f"Cannot resolve segment '{part}' of path '{path}': "
                    f"{type(value).__name__} is not traversable"
                )
        return value
