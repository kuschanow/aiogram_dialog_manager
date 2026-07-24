"""Declarative dialog descriptions: the JSON-serializable core model,
the expression language, interpreting prototypes and the Python builder.

See ``docs/dialog_spec_design.md`` for the design and
``aiogram_dialog_manager.spec.builder`` for the ergonomic construction API.
"""
from aiogram_dialog_manager.spec.compile import (
    CompiledDialog,
    CompiledWindow,
    Namespace,
    compile_dialog,
    iter_spec_nodes,
)
from aiogram_dialog_manager.spec.content import (
    BaseContentSpec,
    DocumentContentSpec,
    MediaGroupContentSpec,
    PhotoContentSpec,
    TextContentSpec,
)
from aiogram_dialog_manager.spec.babel import extract_spec, iter_translation_keys
from aiogram_dialog_manager.spec.errors import (
    ExpressionEvaluationError,
    SpecError,
    SpecValidationError,
    UnknownFunctionError,
    UnknownNodeTypeError,
    UnknownPrototypeError,
    UnknownProviderError,
    UnknownReferenceError,
)
from aiogram_dialog_manager.spec.functions import create_default_function_registry
from aiogram_dialog_manager.spec.model import SPEC_VERSION, DialogSpec, MenuSpec, WindowSpec
from aiogram_dialog_manager.spec.node import (
    OMIT,
    EvaluableNode,
    SpecNode,
    Spliced,
    Value,
    evaluate_value,
    node_registry,
    resolve_value,
)
from aiogram_dialog_manager.spec.nodes import (
    ButtonSpec,
    CallNode,
    ChunkNode,
    EscapeNode,
    ForeachNode,
    IfNode,
    LiteralNode,
    MediaItemNode,
    OpNode,
    PathNode,
    ProviderNode,
    RefNode,
    RowNode,
    SliceNode,
    TranslateNode,
)
from aiogram_dialog_manager.spec.prototypes import (
    SpecButtonPrototype,
    SpecDialogPrototype,
    SpecDocumentMessagePrototype,
    SpecMediaGroupMessagePrototype,
    SpecMenuPrototype,
    SpecMessagePrototypeMixin,
    SpecPhotoMessagePrototype,
    SpecPrototypeFactory,
    SpecPrototypeMixin,
    SpecTextMessagePrototype,
    render_text,
)
from aiogram_dialog_manager.spec.registration import is_spec_registered, register_spec_prototype
from aiogram_dialog_manager.spec.registries import FunctionRegistry, NodeRegistry, ProviderRegistry
from aiogram_dialog_manager.spec.scope import EvalScope, SpecResolver, SpecRuntime, Translator
from aiogram_dialog_manager.spec.use import (
    UseButtonNode,
    UseMenuNode,
    UseMenuPrototype,
    UseMessageContentSpec,
    UseMessagePrototype,
    resolve_prototype,
)
