"""Compilation of a :class:`DialogSpec` into interpreting prototypes.

Compilation happens once at load time: the reference graph is validated,
buttons are collected per window, and the model is turned into a tree of spec
prototypes with deterministic names:

- message:  ``{dialog_name}:{window_name}``
- menu:     ``{dialog_name}:{window_name}:menu``
- button:   ``{dialog_name}:{window_name}:{button_name}``

The result also exposes typed handles (``compiled.windows.main.buttons.save``)
accepted by ``ButtonFilter`` — a typo fails at startup, not at runtime.
"""
from dataclasses import dataclass
from typing import Any, Iterator, Optional, Union

from pydantic import BaseModel

from aiogram_dialog_manager.prototype.base import BaseMessagePrototype
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.spec.errors import SpecValidationError
from aiogram_dialog_manager.spec.functions import create_default_function_registry
from aiogram_dialog_manager.spec.model import DialogSpec, WindowSpec
from aiogram_dialog_manager.spec.node import SpecNode
from aiogram_dialog_manager.spec.nodes import ButtonSpec, RefNode
from aiogram_dialog_manager.spec.prototypes import SpecPrototypeFactory
from aiogram_dialog_manager.spec.registration import register_spec_prototype
from aiogram_dialog_manager.spec.registries import FunctionRegistry, ProviderRegistry
from aiogram_dialog_manager.spec.scope import SpecResolver, SpecRuntime, Translator
from aiogram_dialog_manager.spec.use import UseMenuNode, UseMenuPrototype, UseMessageContentSpec


class Namespace:
    """Attribute/key access over compiled objects: ``windows.main``, ``buttons.save``."""

    def __init__(self, items: dict[str, Any]):
        self._items = dict(items)

    def __getattr__(self, name: str) -> Any:
        try:
            return self._items[name]
        except KeyError:
            raise AttributeError(f"Unknown name '{name}'; available: {', '.join(self._items) or '(none)'}") from None

    def __getitem__(self, name: str) -> Any:
        return self._items[name]

    def __contains__(self, name: str) -> bool:
        return name in self._items

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


@dataclass(frozen=True)
class CompiledWindow:
    name: str
    message: BaseMessagePrototype
    menu: Optional[MenuPrototype]
    buttons: Namespace


def iter_spec_nodes(value: Any) -> Iterator[SpecNode]:
    """Yield every :class:`SpecNode` reachable inside ``value`` (depth-first)."""
    if isinstance(value, SpecNode):
        yield value
    if isinstance(value, BaseModel):
        for field_name in type(value).model_fields:
            yield from iter_spec_nodes(getattr(value, field_name))
    elif isinstance(value, dict):
        for item in value.values():
            yield from iter_spec_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from iter_spec_nodes(item)


def _validate_references(spec: DialogSpec) -> None:
    for scope_name, root in (("windows", spec.windows), ("defs", spec.defs)):
        for node in iter_spec_nodes(root):
            if isinstance(node, RefNode) and node.name not in spec.defs:
                raise SpecValidationError(
                    f"Reference '{node.name}' (used in {scope_name}) is not present in defs"
                )


def _validate_def_cycles(spec: DialogSpec) -> None:
    edges = {
        name: {node.name for node in iter_spec_nodes(body) if isinstance(node, RefNode)}
        for name, body in spec.defs.items()
    }

    visiting: set[str] = set()
    verified: set[str] = set()

    def visit(name: str, path: list[str]) -> None:
        if name in verified:
            return
        if name in visiting:
            cycle = " -> ".join(path + [name])
            raise SpecValidationError(f"Cyclic reference in defs: {cycle}")
        visiting.add(name)
        for target in edges[name]:
            visit(target, path + [name])
        visiting.discard(name)
        verified.add(name)

    for name in edges:
        visit(name, [])


def _collect_window_buttons(window: WindowSpec, spec: DialogSpec, window_name: str) -> dict[str, ButtonSpec]:
    found: dict[str, ButtonSpec] = {}
    visited_refs: set[str] = set()

    def visit(value: Any) -> None:
        for node in iter_spec_nodes(value):
            if isinstance(node, ButtonSpec):
                existing = found.setdefault(node.name, node)
                if existing is not node:
                    raise SpecValidationError(
                        f"Duplicate button name '{node.name}' in window '{window_name}'; "
                        f"reuse a single definition via defs/ref instead"
                    )
            elif isinstance(node, RefNode) and node.name not in visited_refs:
                visited_refs.add(node.name)
                visit(spec.defs[node.name])

    visit(window)
    return found


class CompiledDialog:
    """The result of compilation: prototypes + typed handles + registration."""

    def __init__(self, spec: DialogSpec, runtime: SpecRuntime, factory: SpecPrototypeFactory):
        self._spec = spec
        self._runtime = runtime
        self._factory = factory
        self._dialog_prototype = factory.create_dialog(spec.name, runtime, spec.data, spec.config)
        self._windows = Namespace({
            window_name: self._compile_window(window_name, window)
            for window_name, window in spec.windows.items()
        })

    def _compile_window(self, window_name: str, window: WindowSpec) -> CompiledWindow:
        message_name = f"{self._spec.name}:{window_name}"
        if isinstance(window.content, UseMessageContentSpec):
            # The used prototype controls its own menu and data — a window
            # declaring either alongside would silently lose them.
            for conflicting, present in (("menu", window.menu is not None), ("data", window.data is not None)):
                if present:
                    raise SpecValidationError(
                        f"Window '{window_name}' uses message prototype '{window.content.name}', "
                        f"which controls its own {conflicting}; remove the window {conflicting}"
                    )
        menu_prototype: Optional[MenuPrototype] = None
        if isinstance(window.menu, UseMenuNode):
            menu_prototype = UseMenuPrototype(window.menu, self._runtime, window_name)
        elif window.menu is not None:
            menu_prototype = self._factory.create_menu(f"{message_name}:menu", window.menu, self._runtime, window_name)
        message_prototype = self._factory.create_message(
            window.content, message_name, menu_prototype, self._runtime, window_name, window.data,
        )
        buttons = Namespace({
            button_name: self._factory.create_button(
                f"{message_name}:{button_name}", button_spec, self._runtime, window_name,
            )
            for button_name, button_spec in _collect_window_buttons(window, self._spec, window_name).items()
        })
        return CompiledWindow(name=window_name, message=message_prototype, menu=menu_prototype, buttons=buttons)

    @property
    def spec(self) -> DialogSpec:
        return self._spec

    @property
    def runtime(self) -> SpecRuntime:
        return self._runtime

    @property
    def dialog_prototype(self) -> DialogPrototype:
        return self._dialog_prototype

    @property
    def windows(self) -> Namespace:
        return self._windows

    def register(self) -> "CompiledDialog":
        """Register every prototype in the shared registries (replace semantics
        for spec entries only). ``use``'d prototypes are already registered
        under their own names and are skipped — decided by the spec kind, not
        the prototype class, so custom factories register correctly too."""
        register_spec_prototype(DialogPrototype, self._dialog_prototype.name, self._dialog_prototype)
        for window_name in self._windows:
            window: CompiledWindow = self._windows[window_name]
            window_spec = self._spec.windows[window_name]
            if not isinstance(window_spec.content, UseMessageContentSpec):
                register_spec_prototype(BaseMessagePrototype, window.message.name, window.message)
            if window.menu is not None and not isinstance(window_spec.menu, UseMenuNode):
                register_spec_prototype(MenuPrototype, window.menu.name, window.menu)
            for button_name in window.buttons:
                button = window.buttons[button_name]
                register_spec_prototype(ButtonPrototype, button.name, button)
        return self


def compile_dialog(
        spec: Union[DialogSpec, dict[str, Any]],
        *,
        functions: Optional[FunctionRegistry] = None,
        providers: Optional[ProviderRegistry] = None,
        translator: Optional[Translator] = None,
        prototypes: Optional[SpecPrototypeFactory] = None,
        resolver: Optional[SpecResolver] = None,
        register: bool = False,
) -> CompiledDialog:
    """Compile a dialog model (or its canonical dict form) into prototypes.

    Pass ``prototypes`` (a :class:`SpecPrototypeFactory` subclass) to swap the
    interpreter of any of the four spec primitives; the default factory builds
    the standard ``Spec*Prototype`` classes. Pass ``resolver`` (a
    :class:`~aiogram_dialog_manager.spec.scope.SpecResolver` subclass) to gate
    or customise how ``use`` references (``button``/``menu``/``message``)
    resolve registered prototypes at render time.
    """
    if not isinstance(spec, DialogSpec):
        spec = DialogSpec.model_validate(spec)
    _validate_references(spec)
    _validate_def_cycles(spec)
    runtime = SpecRuntime(
        dialog_name=spec.name,
        defs=spec.defs,
        functions=functions if functions is not None else create_default_function_registry(),
        providers=providers if providers is not None else ProviderRegistry(),
        translator=translator,
        window_name_key=spec.window_name_key,
        resolver=resolver if resolver is not None else SpecResolver(),
    )
    compiled = CompiledDialog(spec, runtime, prototypes if prototypes is not None else SpecPrototypeFactory())
    if register:
        compiled.register()
    return compiled
