"""Node infrastructure of the spec core.

The canonical form of a dialog description is a JSON-compatible dict. Any dict
containing a ``"type"`` key is resolved into a :class:`SpecNode` subclass via
the global :data:`node_registry`; everything else is a literal. The universal
principle of the model: *any leaf field is either a literal or an expression
node* — expressed by the :data:`Value` annotated type.
"""
from typing import Annotated, Any, TYPE_CHECKING

from pydantic import BaseModel, BeforeValidator, ConfigDict

from aiogram_dialog_manager.spec.errors import ExpressionEvaluationError
from aiogram_dialog_manager.spec.registries import NodeRegistry

if TYPE_CHECKING:
    from aiogram_dialog_manager.spec.scope import EvalScope

#: The global open registry of node kinds. Standard nodes are registered here
#: with the library; users add their own kinds through the same mechanism.
node_registry = NodeRegistry()


class _Omitted:
    """Sentinel returned by conditional nodes whose condition failed and no
    ``else`` branch exists. Dropped in list contexts, ``None`` in value contexts."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "OMIT"


OMIT = _Omitted()


class Spliced:
    """Wrapper marking a node result that must be spliced into the enclosing
    list instead of being appended as a single element (``foreach``, ``chunk``)."""

    def __init__(self, items: list):
        self.items = items


class SpecNode(BaseModel):
    """Base class of every node kind.

    Subclasses declare ``type: Literal["..."] = "..."`` and register themselves
    in a :class:`~aiogram_dialog_manager.spec.registries.NodeRegistry`.
    """

    model_config = ConfigDict(extra="forbid")

    type: str


class EvaluableNode(SpecNode):
    """A node that can be evaluated in an expression context."""

    async def evaluate(self, scope: "EvalScope") -> Any:
        raise NotImplementedError  # pragma: no cover - abstract


def resolve_value(value: Any) -> Any:
    """Recursively resolve node dicts inside a raw value.

    Builder expression wrappers expose ``__spec_node__()`` and are unwrapped
    here, so builder objects can be used anywhere a :data:`Value` is expected.
    """
    if hasattr(value, "__spec_node__"):
        value = value.__spec_node__()
    if isinstance(value, SpecNode):
        return value
    if isinstance(value, dict):
        if "type" in value:
            return node_registry.create(value)
        return {key: resolve_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [resolve_value(item) for item in value]
    return value


#: Any leaf field of the spec: a literal or an expression node.
Value = Annotated[Any, BeforeValidator(resolve_value)]


async def evaluate_value(value: Any, scope: "EvalScope") -> Any:
    """Evaluate a :data:`Value` in a *value* context.

    Lists are rendered with splice semantics: ``OMIT`` results are dropped and
    :class:`Spliced` results are inlined — this single rule powers conditional
    buttons, rows and text fragments alike.
    """
    if isinstance(value, EvaluableNode):
        result = await value.evaluate(scope)
        if result is OMIT:
            return None
        if isinstance(result, Spliced):
            return result.items
        return result
    if isinstance(value, SpecNode):
        raise ExpressionEvaluationError(
            f"Node of type '{value.type}' is not evaluable in an expression context"
        )
    if isinstance(value, dict):
        return {key: await evaluate_value(item, scope) for key, item in value.items()}
    if isinstance(value, list):
        rendered: list = []
        for item in value:
            await render_into(rendered, item, scope)
        return rendered
    return value


async def render_into(out: list, value: Any, scope: "EvalScope") -> None:
    """Evaluate a single value with splice semantics, appending into ``out``.

    ``OMIT`` results are dropped, :class:`Spliced` results are inlined; anything
    else is appended as one element.
    """
    if isinstance(value, EvaluableNode):
        result = await value.evaluate(scope)
        if result is OMIT:
            return
        if isinstance(result, Spliced):
            out.extend(result.items)
            return
        out.append(result)
        return
    out.append(await evaluate_value(value, scope))
