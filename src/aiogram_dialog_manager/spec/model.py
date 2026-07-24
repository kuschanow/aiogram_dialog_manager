"""The core model: a whole named dialog as the unit of description.

The canonical form is a JSON-compatible dict — the single source of truth that
both the Python builder and the (phase 2) textual DSL compile into. The root
carries ``version`` from day one: the format will live in storages for years
and migrations are impossible without it.
"""
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from aiogram_dialog_manager.instance.dialog import DialogConfig
from aiogram_dialog_manager.spec.content import BaseContentSpec
from aiogram_dialog_manager.spec.node import SpecNode, Value, node_registry, resolve_value
from aiogram_dialog_manager.spec.nodes import IDENTIFIER_PATTERN
from aiogram_dialog_manager.spec.use import UseMenuNode

SPEC_VERSION = 1

Identifier = Annotated[str, Field(pattern=IDENTIFIER_PATTERN)]


def _check_content(value: Any) -> BaseContentSpec:
    if not isinstance(value, BaseContentSpec):
        raise ValueError(
            f"Window content must be a content node (text, photo, document, media_group, ...), got {type(value).__name__}"
        )
    return value


ContentValue = Annotated[Any, BeforeValidator(resolve_value), AfterValidator(_check_content)]


def _resolve_menu(value: Any) -> Any:
    if hasattr(value, "__spec_node__"):
        value = value.__spec_node__()
    if isinstance(value, dict) and "type" in value:
        value = node_registry.create(value)
    if isinstance(value, SpecNode) and not isinstance(value, UseMenuNode):
        raise ValueError(
            f"Window menu must be a menu spec or a 'use_menu' node, got node of type '{value.type}'"
        )
    return value


class MenuSpec(BaseModel):
    """The window's keyboard: a list of row-producing values.

    A plain list element is sugar for an explicit ``row`` node; ``foreach``,
    ``chunk`` and ``if`` at the row level are spliced/dropped accordingly.
    """

    model_config = ConfigDict(extra="forbid")

    rows: list[Value] = Field(..., min_length=1)
    keyboard_type: Literal["inline", "reply"] = "inline"
    reply_parameters: Optional[dict[str, Value]] = None

    @field_validator("rows", mode="before")
    @classmethod
    def _wrap_plain_rows(cls, rows: Any) -> Any:
        if not isinstance(rows, list):
            return rows
        return [
            {"type": "row", "items": list(row)} if isinstance(row, (list, tuple)) else row
            for row in rows
        ]


class WindowSpec(BaseModel):
    """A single window: what to show (content) and what to offer (menu).

    ``data`` holds the window's default message data (values are expressions);
    the render context is merged on top of it. ``menu`` is either an inline
    :class:`MenuSpec` or a ``use_menu`` node delegating to an existing
    registered menu prototype.
    """

    model_config = ConfigDict(extra="forbid")

    content: ContentValue
    menu: Annotated[Optional[Union[UseMenuNode, MenuSpec]], BeforeValidator(_resolve_menu)] = None
    data: Optional[dict[str, Value]] = None


class DialogSpec(BaseModel):
    """A named dialog: the unit of description, fully serializable.

    Windows are referenced by local names inside the dialog (no global window
    namespace); ``defs`` holds named reusable fragments targeted by ``ref``
    nodes. The reference graph is validated at compile time.
    """

    model_config = ConfigDict(extra="forbid")

    version: int = SPEC_VERSION
    name: Identifier
    windows: dict[Identifier, WindowSpec] = Field(..., min_length=1)
    defs: dict[Identifier, Value] = Field(default_factory=dict)
    #: When set, every spec window stamps its own name into the message data
    #: under this key — the "window name is the state" pattern of wizards
    #: (``MessageFilter`` state routing without repeating it in every send).
    window_name_key: Optional[str] = Field(default=None, min_length=1)
    #: The dialog's default initial data (values are expressions); the render
    #: context is merged on top, exactly like ``WindowSpec.data``.
    data: Optional[dict[str, Value]] = None
    #: The dialog's :class:`DialogConfig` fields (values are expressions);
    #: keys are validated against the config schema at model time.
    config: Optional[dict[str, Value]] = None

    @field_validator("version")
    @classmethod
    def _check_version(cls, version: int) -> int:
        if version != SPEC_VERSION:
            raise ValueError(f"Unsupported spec version {version}; supported version is {SPEC_VERSION}")
        return version

    @field_validator("config")
    @classmethod
    def _check_config_keys(cls, config: Optional[dict[str, Any]]) -> Optional[dict[str, Any]]:
        if config:
            unknown = set(config) - set(DialogConfig.model_fields)
            if unknown:
                raise ValueError(f"Unknown dialog config field(s): {', '.join(sorted(unknown))}")
        return config

    def to_dict(self) -> dict[str, Any]:
        """The canonical JSON-compatible form of the dialog."""
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DialogSpec":
        return cls.model_validate(payload)
