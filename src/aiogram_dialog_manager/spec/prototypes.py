"""Interpreting prototypes for buttons and menus.

A compiled model is interpreted by universal spec prototypes whose getters
evaluate the spec over ``(dialog, context)`` — the whole existing runtime
(instances, storage, history, filters, ``send_message``) works unchanged.

These classes are instantiated per window with deterministic names
(``{dialog_name}:{window_name}:{...}``); they deliberately do not pass
``type_name`` to ``__init_subclass__`` — registration happens per instance
with replace semantics (see :mod:`aiogram_dialog_manager.spec.registration`).
"""
from typing import Any, Optional, TYPE_CHECKING

from aiogram_dialog_manager.instance.button import (
    ButtonInstance,
    CommonButtonAdditionalParameters,
    InlineButtonAdditionalParameters,
)
from aiogram_dialog_manager.instance.menu import AdditionalReplyMenuParameters, MenuInstance
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError
from aiogram_dialog_manager.spec.node import evaluate_value
from aiogram_dialog_manager.spec.nodes import ButtonSpec
from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator
    from aiogram_dialog_manager.spec.model import MenuSpec


class SpecPrototypeMixin:
    """Shared identity and scope construction for spec-driven prototypes."""

    def __init__(self, name: str, runtime: SpecRuntime, window_name: str):
        self._name = name
        self._runtime = runtime
        self._window_name = window_name

    @property
    def name(self) -> str:
        return self._name

    def _scope(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> EvalScope:
        return EvalScope(
            runtime=self._runtime,
            dialog=dialog,
            context=context or {},
            window_name=self._window_name,
        )


class SpecButtonPrototype(SpecPrototypeMixin, ButtonPrototype):
    """Interprets a :class:`ButtonSpec`.

    Doubles as the typed handle of the compiled model
    (``model.windows.main.buttons.save``): ``ButtonFilter`` accepts it
    directly, and a typo fails at compile time instead of at runtime.
    """

    def __init__(self, name: str, spec: ButtonSpec, runtime: SpecRuntime, window_name: str):
        super().__init__(name, runtime, window_name)
        self._spec = spec

    @property
    def spec(self) -> ButtonSpec:
        return self._spec

    async def get_state(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> str:
        return await self._spec.evaluate_text(self._scope(dialog, context))

    async def get_data(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> dict:
        return await self._spec.evaluate_data(self._scope(dialog, context))

    async def get_inline_additional_parameters(
            self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]],
    ) -> Optional[InlineButtonAdditionalParameters]:
        return await self._spec.evaluate_inline_parameters(self._scope(dialog, context))

    async def get_common_additional_parameters(
            self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]],
    ) -> Optional[CommonButtonAdditionalParameters]:
        return await self._spec.evaluate_common_parameters(self._scope(dialog, context))


class SpecMenuPrototype(SpecPrototypeMixin, MenuPrototype):
    """Interprets a :class:`~aiogram_dialog_manager.spec.model.MenuSpec`.

    Rows that render empty (all buttons conditioned away) are dropped; a menu
    with no remaining rows yields no instance at all, so windows can have
    fully conditional keyboards.
    """

    def __init__(self, name: str, spec: "MenuSpec", runtime: SpecRuntime, window_name: str):
        super().__init__(name, runtime, window_name)
        self._spec = spec

    @property
    def spec(self) -> "MenuSpec":
        return self._spec

    async def get_buttons(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> list[list[ButtonInstance]]:
        scope = self._scope(dialog, context)
        rows = await evaluate_value(list(self._spec.rows), scope)
        for row in rows:
            if not isinstance(row, list):
                raise ExpressionEvaluationError(
                    f"Menu row must evaluate to a list of buttons, got {type(row).__name__}"
                )
        return [row for row in rows if row]

    async def get_additional_reply_parameters(
            self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]],
    ) -> Optional[AdditionalReplyMenuParameters]:
        if self._spec.reply_parameters is None:
            return None
        rendered = await evaluate_value(self._spec.reply_parameters, self._scope(dialog, context))
        return AdditionalReplyMenuParameters.model_validate(rendered)

    async def get_instance(self, dialog: "Optional[DialogOperator]", context: Optional[dict[str, Any]]) -> Optional[MenuInstance]:
        buttons = await self.get_buttons(dialog, context)
        if not buttons:
            return None
        return MenuInstance(
            type_name=self.name,
            buttons=buttons,
            keyboard_type=self._spec.keyboard_type,
            data=await self.get_data(dialog, context),
            additional_reply_parameters=await self.get_additional_reply_parameters(dialog, context),
        )
