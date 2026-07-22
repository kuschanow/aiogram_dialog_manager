"""The core model: a whole named dialog as the unit of description.

The canonical form is a JSON-compatible dict — the single source of truth that
both the Python builder and the (phase 2) textual DSL compile into. The root
carries ``version`` from day one: the format will live in storages for years
and migrations are impossible without it.
"""
from typing import Annotated, Any, Literal, Optional

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field, field_validator

from aiogram_dialog_manager.spec.content import BaseContentSpec
from aiogram_dialog_manager.spec.node import Value, resolve_value
from aiogram_dialog_manager.spec.nodes import IDENTIFIER_PATTERN

SPEC_VERSION = 1

Identifier = Annotated[str, Field(pattern=IDENTIFIER_PATTERN)]


def _check_content(value: Any) -> BaseContentSpec:
    if not isinstance(value, BaseContentSpec):
        raise ValueError(
            f"Window content must be a content node (text, photo, document, media_group, ...), got {type(value).__name__}"
        )
    return value


ContentValue = Annotated[Any, BeforeValidator(resolve_value), AfterValidator(_check_content)]


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
    """A single window: what to show (content) and what to offer (menu)."""

    model_config = ConfigDict(extra="forbid")

    content: ContentValue
    menu: Optional[MenuSpec] = None


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

    @field_validator("version")
    @classmethod
    def _check_version(cls, version: int) -> int:
        if version != SPEC_VERSION:
            raise ValueError(f"Unsupported spec version {version}; supported version is {SPEC_VERSION}")
        return version

    def to_dict(self) -> dict[str, Any]:
        """The canonical JSON-compatible form of the dialog."""
        return self.model_dump(mode="json", by_alias=True)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DialogSpec":
        return cls.model_validate(payload)
