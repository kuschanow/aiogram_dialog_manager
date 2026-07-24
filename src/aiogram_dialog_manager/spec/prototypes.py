"""Interpreting prototypes for the four spec primitives.

A compiled model is interpreted by universal spec prototypes whose getters
evaluate the spec over ``(dialog, context)`` — the whole existing runtime
(instances, storage, history, filters, ``send_message``) works unchanged.

The four primitives — dialog, message, menu, button — are deliberately
symmetric: each is a ``SpecPrototypeMixin`` subclass defined here, and each is
constructed through :class:`SpecPrototypeFactory` rather than hardcoded at the
compile site. Override a factory hook (and pass the factory to
``compile_dialog``) to swap the interpreter of any primitive without touching
the compiler; message keeps a second, orthogonal extension axis — new content
kinds plug in via :class:`~aiogram_dialog_manager.spec.content.BaseContentSpec`.

These classes are instantiated per window with deterministic names
(``{dialog_name}:{window_name}:{...}``); they deliberately do not pass
``type_name`` to ``__init_subclass__`` — registration happens per instance
with replace semantics (see :mod:`aiogram_dialog_manager.spec.registration`).
"""
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING

from aiogram_dialog_manager.instance.button import (
    ButtonInstance,
    CommonButtonAdditionalParameters,
    InlineButtonAdditionalParameters,
)
from aiogram_dialog_manager.instance.dialog import DialogConfig
from aiogram_dialog_manager.instance.menu import AdditionalReplyMenuParameters, MenuInstance
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, TextContent
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.prototype.message.document import DocumentExtraParams, DocumentMessagePrototype
from aiogram_dialog_manager.prototype.message.media_group import MediaGroupItem, MediaGroupMessagePrototype
from aiogram_dialog_manager.prototype.message.photo import PhotoExtraParams, PhotoMessagePrototype
from aiogram_dialog_manager.prototype.message.text import TextMessagePrototype
from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError
from aiogram_dialog_manager.spec.node import Value, evaluate_value
from aiogram_dialog_manager.spec.nodes import ButtonSpec
from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator
    from aiogram_dialog_manager.spec.content import (
        BaseContentSpec,
        DocumentContentSpec,
        MediaGroupContentSpec,
        PhotoContentSpec,
        TextContentSpec,
    )
    from aiogram_dialog_manager.spec.model import MenuSpec


async def render_text(value: Value, scope: EvalScope) -> Optional[str]:
    """Render a text field: a single value or a list of fragments joined
    together (``None`` fragments become empty strings)."""
    rendered = await evaluate_value(value, scope)
    if rendered is None:
        return None
    if isinstance(rendered, list):
        return "".join("" if fragment is None else str(fragment) for fragment in rendered)
    return str(rendered)


class SpecPrototypeMixin:
    """Shared identity and scope construction for spec-driven prototypes."""

    def __init__(self, name: str, runtime: SpecRuntime, window_name: Optional[str] = None):
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


class SpecDialogPrototype(SpecPrototypeMixin, DialogPrototype):
    """Interprets the dialog-level defaults of a compiled model.

    Symmetric with the other three spec prototypes: it evaluates spec fields
    over the render scope instead of falling back to the base behaviour.
    ``data`` seeds the initial dialog data (context wins on top, as with window
    data); ``config`` evaluates into the immutable :class:`DialogConfig`.
    The dialog scope has no ``dialog``/``window`` — only ``ctx.*`` and locals.
    """

    def __init__(
            self, name: str, runtime: SpecRuntime,
            data: Optional[dict[str, Value]] = None,
            config: Optional[dict[str, Value]] = None,
    ):
        super().__init__(name, runtime)
        self._data = data
        self._config = config

    async def get_data(self, context: Optional[dict[str, Any]]) -> dict:
        data: dict[str, Any] = {}
        if self._data:
            scope = self._scope(None, context)
            data.update({key: await evaluate_value(value, scope) for key, value in self._data.items()})
        data.update(context or {})
        return data

    async def get_config(self, context: Optional[dict[str, Any]]) -> DialogConfig:
        if not self._config:
            return DialogConfig()
        scope = self._scope(None, context)
        rendered = {key: await evaluate_value(value, scope) for key, value in self._config.items()}
        return DialogConfig.model_validate(rendered)


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


class SpecMessagePrototypeMixin(SpecPrototypeMixin):
    """Shared wiring of spec message prototypes: content spec + window menu.

    Message data is assembled from three layers, later ones winning:
    the window name under ``runtime.window_name_key`` (if set), the window's
    default ``data`` (values are expressions), and the render context.

    Concrete message prototypes below combine this mixin with the matching
    library message base (text/photo/document/media group), so all sending and
    editing logic is reused as is.
    """

    def __init__(
            self, name: str, content: "BaseContentSpec",
            menu_prototype: Optional[MenuPrototype],
            runtime: SpecRuntime, window_name: str,
            window_data: Optional[dict[str, Value]] = None,
    ):
        super().__init__(name, runtime, window_name)
        self._content = content
        self._menu_prototype = menu_prototype
        self._window_data = window_data

    @property
    def content(self) -> "BaseContentSpec":
        return self._content

    @property
    def menu_prototype(self) -> Optional[MenuPrototype]:
        return self._menu_prototype

    async def get_menu(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]):
        if self._menu_prototype is None:
            return None
        return await self._menu_prototype.get_instance(dialog, context)

    async def get_data(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> dict:
        data: dict[str, Any] = {}
        if self._runtime.window_name_key is not None:
            data[self._runtime.window_name_key] = self._window_name
        if self._window_data:
            scope = self._scope(dialog, context)
            data.update({key: await evaluate_value(value, scope) for key, value in self._window_data.items()})
        data.update(context or {})
        return data


class SpecTextMessagePrototype(SpecMessagePrototypeMixin, TextMessagePrototype):
    _content: "TextContentSpec"

    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        text = await render_text(self._content.text, self._scope(dialog, context))
        if text is None:
            raise ExpressionEvaluationError(f"Text of window '{self._window_name}' evaluated to None")
        return TextContent(text=text)


class SpecPhotoMessagePrototype(SpecMessagePrototypeMixin, PhotoMessagePrototype):
    _content: "PhotoContentSpec"

    async def get_photo(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        return await evaluate_value(self._content.photo, self._scope(dialog, context))

    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        return TextContent(text=await render_text(self._content.caption, self._scope(dialog, context)))

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> PhotoExtraParams:
        scope = self._scope(dialog, context)
        return PhotoExtraParams(
            has_spoiler=await evaluate_value(self._content.has_spoiler, scope),
            show_caption_above_media=await evaluate_value(self._content.show_caption_above_media, scope),
        )


class SpecDocumentMessagePrototype(SpecMessagePrototypeMixin, DocumentMessagePrototype):
    _content: "DocumentContentSpec"

    async def get_document(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        return await evaluate_value(self._content.document, self._scope(dialog, context))

    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        return TextContent(text=await render_text(self._content.caption, self._scope(dialog, context)))

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> DocumentExtraParams:
        scope = self._scope(dialog, context)
        return DocumentExtraParams(
            disable_content_type_detection=await evaluate_value(self._content.disable_content_type_detection, scope),
        )


class SpecMediaGroupMessagePrototype(SpecMessagePrototypeMixin, MediaGroupMessagePrototype):
    _content: "MediaGroupContentSpec"

    async def get_media(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> list[MediaGroupItem]:
        return await evaluate_value(list(self._content.items), self._scope(dialog, context))


@dataclass(frozen=True)
class SpecPrototypeFactory:
    """Builds the four spec-driven interpreter prototypes.

    The single construction seam for a compiled dialog: subclass this, override
    the hook of a primitive to swap its interpreter across the whole dialog,
    and pass the instance to :func:`~aiogram_dialog_manager.spec.compile_dialog`.
    The default hooks build the standard ``Spec*Prototype`` classes above.

    ``create_message`` delegates to the content spec's ``create_prototype`` so
    the orthogonal content-kind seam (new media types via ``BaseContentSpec``)
    keeps working — including ``use_message``, which resolves to an existing
    registered prototype.
    """

    def create_dialog(
            self, name: str, runtime: SpecRuntime,
            data: Optional[dict[str, Value]] = None,
            config: Optional[dict[str, Value]] = None,
    ) -> DialogPrototype:
        return SpecDialogPrototype(name, runtime, data, config)

    def create_message(
            self, content: "BaseContentSpec", name: str,
            menu_prototype: Optional[MenuPrototype], runtime: SpecRuntime,
            window_name: str, window_data: Optional[dict[str, Value]] = None,
    ) -> BaseMessagePrototype:
        return content.create_prototype(name, menu_prototype, runtime, window_name, window_data)

    def create_menu(self, name: str, spec: "MenuSpec", runtime: SpecRuntime, window_name: str) -> MenuPrototype:
        return SpecMenuPrototype(name, spec, runtime, window_name)

    def create_button(self, name: str, spec: ButtonSpec, runtime: SpecRuntime, window_name: str) -> ButtonPrototype:
        return SpecButtonPrototype(name, spec, runtime, window_name)
