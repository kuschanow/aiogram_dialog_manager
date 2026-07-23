"""``use`` nodes: plugging existing registered prototypes into spec dialogs.

The first real dialog rewritten to the spec immediately needed reusable Python
button prototypes (shared cancel/skip handlers) — ``use`` is the standard way
to reference them: a lookup by ``type_name`` in the shared prototype
registries. The used prototype keeps its own ``type_name``, so existing
``ButtonFilter``/handler wiring works without changes.

Resolution timing differs deliberately:

- ``use_button`` / ``use_menu`` resolve **lazily at render time** — the target
  may be registered after the spec dialog is compiled (e.g. models loaded from
  a DB before Python modules finish importing);
- ``use_message`` resolves **at compile time** — the send/edit paths dispatch
  on the concrete prototype (``isinstance`` checks), so the window's message
  prototype must be the real registered object, not a proxy.
"""
from typing import Any, Literal, Optional, TYPE_CHECKING

from pydantic import Field

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import AdditionalReplyMenuParameters, MenuInstance
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.spec.content import BaseContentSpec
from aiogram_dialog_manager.spec.errors import UnknownPrototypeError
from aiogram_dialog_manager.spec.node import EvaluableNode, SpecNode, Value, evaluate_value, node_registry
from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


def resolve_prototype(base_cls: type, name: str) -> Any:
    """Resolve a prototype from ``base_cls._registry`` by ``type_name``.

    Python prototypes are stored as classes and are instantiated here (they
    must have a no-argument constructor to be usable from specs); spec entries
    are stored as ready instances.
    """
    try:
        entry = base_cls._registry[name]
    except KeyError:
        raise UnknownPrototypeError(
            f"{base_cls.__name__} name '{name}' is not registered; "
            f"'use' nodes require the target prototype to be registered"
        ) from None
    return entry() if isinstance(entry, type) else entry


async def _merge_context(context_spec: Optional[dict[str, Value]], scope: EvalScope) -> Optional[dict[str, Any]]:
    """The context passed to the used prototype: the render context with the
    node's ``context`` expressions evaluated and merged on top."""
    if context_spec is None:
        return scope.context
    overrides = {key: await evaluate_value(value, scope) for key, value in context_spec.items()}
    return {**scope.context, **overrides}


@node_registry.register
class UseButtonNode(EvaluableNode):
    """Renders an existing button prototype inside a spec menu.

    The resulting instance keeps the target's own ``type_name`` — existing
    ``ButtonFilter`` handlers keep working unchanged. ``context`` values are
    expressions merged over the render context, so ``foreach`` can
    parameterize used buttons per item.
    """

    type: Literal["use_button"] = "use_button"
    name: str = Field(..., min_length=1)
    context: Optional[dict[str, Value]] = None

    async def evaluate(self, scope: EvalScope) -> ButtonInstance:
        prototype = resolve_prototype(ButtonPrototype, self.name)
        return await prototype.get_instance(scope.dialog, await _merge_context(self.context, scope))


@node_registry.register
class UseMenuNode(SpecNode):
    """A window menu delegated to an existing registered menu prototype."""

    type: Literal["use_menu"] = "use_menu"
    name: str = Field(..., min_length=1)
    context: Optional[dict[str, Value]] = None


class UseMenuPrototype(MenuPrototype):
    """Interprets a :class:`UseMenuNode`: every getter delegates to the target
    prototype (resolved lazily per call) with the merged context. The menu
    instance keeps the target's ``type_name``."""

    def __init__(self, node: UseMenuNode, runtime: SpecRuntime, window_name: str):
        self._node = node
        self._runtime = runtime
        self._window_name = window_name

    @property
    def name(self) -> str:
        return self._node.name

    def _target(self) -> MenuPrototype:
        return resolve_prototype(MenuPrototype, self._node.name)

    async def _context(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        scope = EvalScope(
            runtime=self._runtime,
            dialog=dialog,
            context=context or {},
            window_name=self._window_name,
        )
        return await _merge_context(self._node.context, scope)

    async def get_buttons(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> list[list[ButtonInstance]]:
        return await self._target().get_buttons(dialog, await self._context(dialog, context))

    async def get_data(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> dict:
        return await self._target().get_data(dialog, await self._context(dialog, context))

    async def get_additional_reply_parameters(
            self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]],
    ) -> Optional[AdditionalReplyMenuParameters]:
        return await self._target().get_additional_reply_parameters(dialog, await self._context(dialog, context))

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> MenuInstance:
        return await self._target().get_instance(dialog, await self._context(dialog, context))


@node_registry.register
class UseMessageContentSpec(BaseContentSpec):
    """Window content delegating to an existing registered message prototype.

    Resolved at compile time to the real registered prototype (the send/edit
    paths dispatch on its concrete class). Such a window cannot declare its
    own ``menu`` or ``data`` — the target prototype controls both.
    """

    type: Literal["use_message"] = "use_message"
    name: str = Field(..., min_length=1)

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> BaseMessagePrototype:
        return resolve_prototype(BaseMessagePrototype, self.name)
