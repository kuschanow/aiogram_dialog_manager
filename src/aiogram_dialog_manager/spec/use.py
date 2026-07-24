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
from aiogram_dialog_manager.spec.node import EvaluableNode, SpecNode, Value, evaluate_value, node_registry
from aiogram_dialog_manager.spec.scope import EvalScope, SpecResolver, SpecRuntime

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator

_DEFAULT_RESOLVER = SpecResolver()


def resolve_prototype(base_cls: type, name: str) -> Any:
    """Resolve a prototype from ``base_cls._registry`` by ``type_name`` using
    the default (non-gating) resolver — the standalone convenience form of
    :meth:`~aiogram_dialog_manager.spec.scope.SpecResolver.resolve`.
    """
    return _DEFAULT_RESOLVER.resolve(base_cls, name, None)


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
        prototype = scope.runtime.resolver.resolve(ButtonPrototype, self.name, scope)
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

    def _scope(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> EvalScope:
        return EvalScope(
            runtime=self._runtime,
            dialog=dialog,
            context=context or {},
            window_name=self._window_name,
        )

    def _target(self, scope: EvalScope) -> MenuPrototype:
        return self._runtime.resolver.resolve(MenuPrototype, self._node.name, scope)

    async def get_buttons(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> list[list[ButtonInstance]]:
        scope = self._scope(dialog, context)
        return await self._target(scope).get_buttons(dialog, await _merge_context(self._node.context, scope))

    async def get_data(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> dict:
        scope = self._scope(dialog, context)
        return await self._target(scope).get_data(dialog, await _merge_context(self._node.context, scope))

    async def get_additional_reply_parameters(
            self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]],
    ) -> Optional[AdditionalReplyMenuParameters]:
        scope = self._scope(dialog, context)
        return await self._target(scope).get_additional_reply_parameters(dialog, await _merge_context(self._node.context, scope))

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> MenuInstance:
        scope = self._scope(dialog, context)
        return await self._target(scope).get_instance(dialog, await _merge_context(self._node.context, scope))


@node_registry.register
class UseMessageContentSpec(BaseContentSpec):
    """Window content delegating to an existing registered message prototype.

    Resolved **lazily at render time** through ``runtime.resolver`` (via
    :class:`UseMessagePrototype`), so a compiled dialog resolves nothing and
    access policies apply per execution — symmetric with ``use_button`` and
    ``use_menu``. Such a window cannot declare its own ``menu`` or ``data`` —
    the target prototype controls both.
    """

    type: Literal["use_message"] = "use_message"
    name: str = Field(..., min_length=1)

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> "UseMessagePrototype":
        return UseMessagePrototype(self, runtime, window_name)


class UseMessagePrototype(BaseMessagePrototype):
    """Interprets a :class:`UseMessageContentSpec`: resolves the target message
    prototype lazily per call through ``runtime.resolver`` and delegates to it —
    the message analog of :class:`UseMenuPrototype`. The instance keeps the
    target's own ``type_name``.

    ``get_instance``/``_do_send``/``_do_edit`` are delegated explicitly (their
    first argument is ``bot`` or they are abstract); the kind-specific getters
    (``get_input_media``, ``get_latitude``, ...) share the ``(dialog, context,
    *rest)`` shape and are forwarded via :meth:`__getattr__`.
    """

    def __init__(self, node: UseMessageContentSpec, runtime: SpecRuntime, window_name: str):
        self._node = node
        self._runtime = runtime
        self._window_name = window_name

    @property
    def name(self) -> str:
        return self._node.name

    def _target(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> BaseMessagePrototype:
        scope = EvalScope(
            runtime=self._runtime,
            dialog=dialog,
            context=context or {},
            window_name=self._window_name,
        )
        return self._runtime.resolver.resolve(BaseMessagePrototype, self._node.name, scope)

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]):
        return await self._target(dialog, context).get_instance(dialog, context)

    async def _do_send(self, bot, dialog, context, target, instance, effective_params, reply_markup):
        return await self._target(dialog, context)._do_send(
            bot, dialog, context, target, instance, effective_params, reply_markup,
        )

    async def _do_edit(self, bot, dialog, context, tg, instance, inline_markup, effective_params):
        return await self._target(dialog, context)._do_edit(
            bot, dialog, context, tg, instance, inline_markup, effective_params,
        )

    def __getattr__(self, item: str):
        # Forward kind-specific getters (all shaped (dialog, context, *rest)) to
        # the resolved target; internal/dunder lookups are not proxied.
        if item.startswith("_"):
            raise AttributeError(item)

        async def forward(dialog, context, *args, **kwargs):
            target = self._target(dialog, context)
            return await getattr(target, item)(dialog, context, *args, **kwargs)

        return forward
