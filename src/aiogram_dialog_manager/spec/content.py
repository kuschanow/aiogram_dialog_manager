"""Window content kinds and their interpreting message prototypes.

The content of a window is an open discriminated union by ``type``: the first
iteration ships ``text``, ``photo``, ``document`` and ``media_group`` (the
common dialog types); the rest of the existing message prototypes can be added
mechanically. A user-defined content kind is a registered node subclassing
:class:`BaseContentSpec` — it plugs into windows exactly like the standard ones.

Each content spec knows how to create its interpreting prototype; the
prototypes subclass the existing message prototype bases, so all sending and
editing logic is reused as is.
"""
from typing import Any, Literal, Optional, TYPE_CHECKING

from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, TextContent
from aiogram_dialog_manager.prototype.message.document import DocumentExtraParams, DocumentMessagePrototype
from aiogram_dialog_manager.prototype.message.media_group import MediaGroupItem, MediaGroupMessagePrototype
from aiogram_dialog_manager.prototype.message.photo import PhotoExtraParams, PhotoMessagePrototype
from aiogram_dialog_manager.prototype.message.text import TextMessagePrototype
from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError
from aiogram_dialog_manager.spec.node import SpecNode, Value, evaluate_value, node_registry
from aiogram_dialog_manager.spec.prototypes import SpecMenuPrototype, SpecPrototypeMixin
from aiogram_dialog_manager.spec.scope import EvalScope, SpecRuntime

if TYPE_CHECKING:
    from aiogram_dialog_manager.dialog_operator import DialogOperator


async def render_text(value: Value, scope: EvalScope) -> Optional[str]:
    """Render a text field: a single value or a list of fragments joined
    together (``None`` fragments become empty strings)."""
    rendered = await evaluate_value(value, scope)
    if rendered is None:
        return None
    if isinstance(rendered, list):
        return "".join("" if fragment is None else str(fragment) for fragment in rendered)
    return str(rendered)


class BaseContentSpec(SpecNode):
    """Base class of window content kinds.

    Not evaluable as an expression — instead it creates the message prototype
    that interprets it.
    """

    def create_prototype(
            self, name: str, menu_prototype: Optional[SpecMenuPrototype],
            runtime: SpecRuntime, window_name: str,
            window_data: Optional[dict[str, Value]] = None,
    ) -> BaseMessagePrototype:
        raise NotImplementedError  # pragma: no cover - abstract


class SpecMessagePrototypeMixin(SpecPrototypeMixin):
    """Shared wiring of spec message prototypes: content spec + window menu.

    Message data is assembled from three layers, later ones winning:
    the window name under ``runtime.window_name_key`` (if set), the window's
    default ``data`` (values are expressions), and the render context.
    """

    def __init__(
            self, name: str, content: BaseContentSpec,
            menu_prototype: Optional[SpecMenuPrototype],
            runtime: SpecRuntime, window_name: str,
            window_data: Optional[dict[str, Value]] = None,
    ):
        super().__init__(name, runtime, window_name)
        self._content = content
        self._menu_prototype = menu_prototype
        self._window_data = window_data

    @property
    def content(self) -> BaseContentSpec:
        return self._content

    @property
    def menu_prototype(self) -> Optional[SpecMenuPrototype]:
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


@node_registry.register
class TextContentSpec(BaseContentSpec):
    """A plain text message; ``text`` is a value or a list of fragments."""

    type: Literal["text"] = "text"
    text: Value

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> "SpecTextMessagePrototype":
        return SpecTextMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


class SpecTextMessagePrototype(SpecMessagePrototypeMixin, TextMessagePrototype):
    _content: TextContentSpec

    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        text = await render_text(self._content.text, self._scope(dialog, context))
        if text is None:
            raise ExpressionEvaluationError(f"Text of window '{self._window_name}' evaluated to None")
        return TextContent(text=text)


@node_registry.register
class PhotoContentSpec(BaseContentSpec):
    type: Literal["photo"] = "photo"
    photo: Value
    caption: Value = None
    has_spoiler: Value = None
    show_caption_above_media: Value = None

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> "SpecPhotoMessagePrototype":
        return SpecPhotoMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


class SpecPhotoMessagePrototype(SpecMessagePrototypeMixin, PhotoMessagePrototype):
    _content: PhotoContentSpec

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


@node_registry.register
class DocumentContentSpec(BaseContentSpec):
    type: Literal["document"] = "document"
    document: Value
    caption: Value = None
    disable_content_type_detection: Value = None

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> "SpecDocumentMessagePrototype":
        return SpecDocumentMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


class SpecDocumentMessagePrototype(SpecMessagePrototypeMixin, DocumentMessagePrototype):
    _content: DocumentContentSpec

    async def get_document(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> str:
        return await evaluate_value(self._content.document, self._scope(dialog, context))

    async def get_text_content(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> TextContent:
        return TextContent(text=await render_text(self._content.caption, self._scope(dialog, context)))

    async def get_extra_params(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> DocumentExtraParams:
        scope = self._scope(dialog, context)
        return DocumentExtraParams(
            disable_content_type_detection=await evaluate_value(self._content.disable_content_type_detection, scope),
        )


@node_registry.register
class MediaGroupContentSpec(BaseContentSpec):
    """A media group; ``items`` render with splice semantics, so ``foreach``
    over ``data`` naturally produces a dynamic album."""

    type: Literal["media_group"] = "media_group"
    items: list[Value]

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> "SpecMediaGroupMessagePrototype":
        return SpecMediaGroupMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


class SpecMediaGroupMessagePrototype(SpecMessagePrototypeMixin, MediaGroupMessagePrototype):
    _content: MediaGroupContentSpec

    async def get_media(self, dialog: "DialogOperator", context: Optional[dict[str, Any]]) -> list[MediaGroupItem]:
        return await evaluate_value(list(self._content.items), self._scope(dialog, context))
