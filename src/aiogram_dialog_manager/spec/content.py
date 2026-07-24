"""Window content kinds — the data nodes and the content-kind extension seam.

The content of a window is an open discriminated union by ``type``: the first
iteration ships ``text``, ``photo``, ``document`` and ``media_group`` (the
common dialog types); the rest of the existing message prototypes can be added
mechanically. A user-defined content kind is a registered node subclassing
:class:`BaseContentSpec` — it plugs into windows exactly like the standard ones.

Each content spec knows how to create its interpreting message prototype (the
``Spec*MessagePrototype`` classes live in
:mod:`aiogram_dialog_manager.spec.prototypes` alongside the other three spec
primitives). This ``create_prototype`` dispatch is the *content-kind* seam
(adding media types); swapping the interpreter of an existing primitive is the
orthogonal job of
:class:`~aiogram_dialog_manager.spec.prototypes.SpecPrototypeFactory`.
"""
from typing import Literal, Optional

from aiogram_dialog_manager.prototype.base import BaseMessagePrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.spec.node import SpecNode, Value, node_registry
from aiogram_dialog_manager.spec.prototypes import (
    SpecDocumentMessagePrototype,
    SpecMediaGroupMessagePrototype,
    SpecPhotoMessagePrototype,
    SpecTextMessagePrototype,
)
from aiogram_dialog_manager.spec.scope import SpecRuntime


class BaseContentSpec(SpecNode):
    """Base class of window content kinds.

    Not evaluable as an expression — instead it creates the message prototype
    that interprets it. The extension seam for new content *kinds*: a
    user-defined kind subclasses this (or :class:`SentContentSpec` to also gain
    send params) and registers itself.
    """

    def create_prototype(
            self, name: str, menu_prototype: Optional[MenuPrototype],
            runtime: SpecRuntime, window_name: str,
            window_data: Optional[dict[str, Value]] = None,
    ) -> BaseMessagePrototype:
        raise NotImplementedError  # pragma: no cover - abstract


class SentContentSpec(BaseContentSpec):
    """Content the library itself renders and sends — as opposed to a delegated
    ``use_message``, whose target prototype owns its send behaviour.

    ``send_params`` carries the message *send* options (``parse_mode``,
    ``link_preview_options``, ``disable_notification``, ...) as evaluable
    :data:`Value` fields — so formatting/notification behaviour is part of the
    serialized dialog and reachable by runtime/user-authored dialogs, not only
    by a Python send-site. Evaluated into a
    :class:`~aiogram_dialog_manager.instance.message.SendParams` and surfaced
    through the message prototype's ``get_send_params``. Keys are validated
    against ``SendParams`` at render time (unknown keys are ignored, mirroring
    the other ``*_parameters`` fields).
    """

    send_params: Optional[dict[str, Value]] = None


@node_registry.register
class TextContentSpec(SentContentSpec):
    """A plain text message; ``text`` is a value or a list of fragments."""

    type: Literal["text"] = "text"
    text: Value

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> SpecTextMessagePrototype:
        return SpecTextMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


@node_registry.register
class PhotoContentSpec(SentContentSpec):
    type: Literal["photo"] = "photo"
    photo: Value
    caption: Value = None
    has_spoiler: Value = None
    show_caption_above_media: Value = None

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> SpecPhotoMessagePrototype:
        return SpecPhotoMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


@node_registry.register
class DocumentContentSpec(SentContentSpec):
    type: Literal["document"] = "document"
    document: Value
    caption: Value = None
    disable_content_type_detection: Value = None

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> SpecDocumentMessagePrototype:
        return SpecDocumentMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)


@node_registry.register
class MediaGroupContentSpec(SentContentSpec):
    """A media group; ``items`` render with splice semantics, so ``foreach``
    over ``data`` naturally produces a dynamic album."""

    type: Literal["media_group"] = "media_group"
    items: list[Value]

    def create_prototype(self, name, menu_prototype, runtime, window_name, window_data=None) -> SpecMediaGroupMessagePrototype:
        return SpecMediaGroupMessagePrototype(name, self, menu_prototype, runtime, window_name, window_data)
