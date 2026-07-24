"""Tests for ``use`` nodes: plugging existing prototypes into spec dialogs."""
import pytest

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import AdditionalReplyMenuParameters
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype, TextContent
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.prototype.message.text import TextMessagePrototype
from aiogram_dialog_manager.spec import (
    DialogSpec,
    SpecResolver,
    SpecValidationError,
    UnknownPrototypeError,
    UseButtonNode,
    UseMenuNode,
    UseMenuPrototype,
    UseMessageContentSpec,
    UseMessagePrototype,
    compile_dialog,
    resolve_prototype,
)
from aiogram_dialog_manager.spec import registration
from aiogram_dialog_manager.spec.prototypes import SpecMenuPrototype


@pytest.fixture
def clean_registries(monkeypatch):
    for base in (BaseMessagePrototype, ButtonPrototype, MenuPrototype, DialogPrototype):
        monkeypatch.setattr(base, "_registry", base._registry.copy())
    monkeypatch.setattr(registration, "_spec_registered_names", {})


@pytest.fixture
def cancel_button(clean_registries):
    class CancelButton(ButtonPrototype, type_name="cancel_btn"):
        async def get_state(self, dialog, context):
            return "Cancel"

        async def get_data(self, dialog, context):
            return dict(context or {})

    return CancelButton


@pytest.fixture
def shared_menu(clean_registries, cancel_button):
    class SharedMenu(MenuPrototype, type_name="shared_menu"):
        async def get_buttons(self, dialog, context):
            return [[await cancel_button().get_instance(dialog, context)]]

        async def get_additional_reply_parameters(self, dialog, context):
            if (context or {}).get("resize"):
                return AdditionalReplyMenuParameters(resize_keyboard=True)
            return None

    return SharedMenu


@pytest.fixture
def error_message(clean_registries):
    class ErrorMessage(TextMessagePrototype, type_name="error_msg"):
        async def get_text_content(self, dialog, context):
            return TextContent(text=f"Error: {(context or {}).get('reason')}")

    return ErrorMessage


@pytest.fixture
def sink_message(clean_registries):
    class SinkMessage(TextMessagePrototype, type_name="sink_msg"):
        async def get_text_content(self, dialog, context):
            return TextContent(text="sink")

        async def _do_send(self, bot, dialog, context, target, instance, effective_params, reply_markup):
            return "sent"

        async def _do_edit(self, bot, dialog, context, tg, instance, inline_markup, effective_params):
            return "edited"

    return SinkMessage


class TestResolvePrototype:
    def test_class_entry_is_instantiated(self, cancel_button):
        prototype = resolve_prototype(ButtonPrototype, "cancel_btn")
        assert isinstance(prototype, cancel_button)

    def test_instance_entry_returned_as_is(self, clean_registries):
        compiled = compile_dialog(
            {"name": "dlg", "windows": {"main": {"content": {"type": "text", "text": "hi"}}}},
            register=True,
        )
        assert resolve_prototype(BaseMessagePrototype, "dlg:main") is compiled.windows.main.message

    def test_unknown_name_raises(self, clean_registries):
        with pytest.raises(UnknownPrototypeError, match="'missing' is not registered"):
            resolve_prototype(ButtonPrototype, "missing")


class TestUseButtonNode:
    async def test_renders_target_with_original_type_name(self, cancel_button, make_scope):
        scope = make_scope(context={"game_id": 7})
        instance = await UseButtonNode(name="cancel_btn").evaluate(scope)
        assert isinstance(instance, ButtonInstance)
        assert instance.type_name == "cancel_btn"
        assert instance.text == "Cancel"
        assert instance.data == {"game_id": 7}

    async def test_context_expressions_merged_over_render_context(self, cancel_button, make_scope):
        scope = make_scope(data={"page": 3}, context={"game_id": 7, "page": 0})
        node = UseButtonNode(name="cancel_btn", context={"page": {"type": "path", "path": "data.page"}})
        instance = await node.evaluate(scope)
        assert instance.data == {"game_id": 7, "page": 3}

    async def test_foreach_parameterizes_used_button(self, cancel_button, make_scope):
        from aiogram_dialog_manager.spec import ForeachNode, PathNode, evaluate_value

        scope = make_scope(data={"ids": [1, 2]})
        node = ForeachNode(
            over=PathNode(path="data.ids"),
            body=UseButtonNode(name="cancel_btn", context={"id": PathNode(path="item")}),
        )
        buttons = await evaluate_value([node], scope)
        assert [b.data["id"] for b in buttons] == [1, 2]

    async def test_unknown_target_raises_at_render(self, clean_registries, scope):
        with pytest.raises(UnknownPrototypeError):
            await UseButtonNode(name="missing").evaluate(scope)

    def test_serialization_roundtrip(self):
        node = UseButtonNode(name="cancel_btn", context={"x": 1})
        dumped = node.model_dump()
        assert dumped == {"type": "use_button", "name": "cancel_btn", "context": {"x": 1}}
        assert UseButtonNode.model_validate(dumped) == node


def make_use_menu_spec(**menu_extra) -> DialogSpec:
    return DialogSpec.from_dict({
        "name": "dlg",
        "windows": {
            "main": {
                "content": {"type": "text", "text": "hi"},
                "menu": {"type": "use_menu", "name": "shared_menu", **menu_extra},
            },
        },
    })


class TestUseMenu:
    async def test_window_menu_delegates_to_target(self, shared_menu):
        compiled = compile_dialog(make_use_menu_spec())
        menu = compiled.windows.main.menu
        assert isinstance(menu, UseMenuPrototype)
        assert menu.name == "shared_menu"
        instance = await menu.get_instance(None, {"game_id": 7})
        assert instance.type_name == "shared_menu"
        assert instance.buttons[0][0].type_name == "cancel_btn"
        assert instance.data == {"game_id": 7}

    async def test_context_override_and_delegated_getters(self, shared_menu):
        compiled = compile_dialog(make_use_menu_spec(context={"resize": True}))
        menu = compiled.windows.main.menu
        buttons = await menu.get_buttons(None, {})
        assert buttons[0][0].text == "Cancel"
        assert await menu.get_data(None, {"a": 1}) == {"a": 1, "resize": True}
        params = await menu.get_additional_reply_parameters(None, {})
        assert params.resize_keyboard is True

    async def test_message_get_menu_goes_through_use(self, shared_menu):
        compiled = compile_dialog(make_use_menu_spec())
        instance = await compiled.windows.main.message.get_menu(None, {})
        assert instance.type_name == "shared_menu"

    async def test_target_may_be_registered_after_compile(self, clean_registries):
        compiled = compile_dialog(make_use_menu_spec())

        with pytest.raises(UnknownPrototypeError):
            await compiled.windows.main.menu.get_instance(None, {})

        class LateMenu(MenuPrototype, type_name="shared_menu"):
            async def get_buttons(self, dialog, context):
                return [[ButtonInstance(text="x", type_name="late_btn", data={})]]

        instance = await compiled.windows.main.menu.get_instance(None, {})
        assert instance.type_name == "shared_menu"

    def test_use_menu_not_registered_under_spec_name(self, shared_menu):
        compiled = compile_dialog(make_use_menu_spec(), register=True)
        assert "dlg:main:menu" not in MenuPrototype._registry
        assert compiled.windows.main.menu.name == "shared_menu"

    def test_menu_rejects_other_node_kinds(self):
        with pytest.raises(ValueError, match="menu spec or a 'use_menu' node"):
            DialogSpec.from_dict({
                "name": "dlg",
                "windows": {
                    "main": {
                        "content": {"type": "text", "text": "hi"},
                        "menu": {"type": "row", "items": []},
                    },
                },
            })

    def test_serialization_roundtrip(self, shared_menu):
        spec = make_use_menu_spec(context={"resize": True})
        dumped = spec.to_dict()
        menu = dumped["windows"]["main"]["menu"]
        assert menu == {"type": "use_menu", "name": "shared_menu", "context": {"resize": True}}
        assert DialogSpec.from_dict(dumped).to_dict() == dumped


def make_use_message_spec(window_extra=None) -> dict:
    return {
        "name": "dlg",
        "windows": {
            "err": {
                "content": {"type": "use_message", "name": "error_msg"},
                **(window_extra or {}),
            },
        },
    }


class TestUseMessage:
    async def test_resolves_lazily_at_render(self, error_message):
        compiled = compile_dialog(make_use_message_spec())
        message = compiled.windows.err.message
        # A lazy proxy, not the resolved prototype — symmetric with use_menu.
        assert isinstance(message, UseMessagePrototype)
        assert message.name == "error_msg"
        # get_instance is delegated explicitly...
        instance = await message.get_instance(None, {"reason": "oops"})
        assert instance.type_name == "error_msg"
        assert instance.text == "Error: oops"
        # ...kind-specific getters through __getattr__ forwarding.
        content = await message.get_text_content(None, {"reason": "bad"})
        assert content.text == "Error: bad"

    async def test_proxy_delegates_send_and_edit(self, sink_message):
        compiled = compile_dialog({
            "name": "dlg",
            "windows": {"err": {"content": {"type": "use_message", "name": "sink_msg"}}},
        })
        proto = compiled.windows.err.message
        assert await proto._do_send("bot", None, {}, "tgt", "inst", "params", "markup") == "sent"
        assert await proto._do_edit("bot", None, {}, "tg", "inst", "markup", "params") == "edited"

    def test_proxy_does_not_proxy_private_attributes(self, error_message):
        proto = compile_dialog(make_use_message_spec()).windows.err.message
        with pytest.raises(AttributeError):
            proto._nonexistent

    async def test_reused_target_resolved_per_call(self, error_message, clean_registries):
        inner = compile_dialog(
            {"name": "inner", "windows": {"main": {"content": {"type": "text", "text": "hi"}}}},
            register=True,
        )
        compiled = compile_dialog({
            "name": "outer",
            "windows": {"main": {"content": {"type": "use_message", "name": "inner:main"}}},
        })
        message = compiled.windows.main.message
        assert isinstance(message, UseMessagePrototype)
        instance = await message.get_instance(None, None)
        assert instance.type_name == inner.windows.main.message.name == "inner:main"

    async def test_unknown_target_fails_at_render(self, clean_registries):
        compiled = compile_dialog({
            "name": "dlg",
            "windows": {"main": {"content": {"type": "use_message", "name": "missing"}}},
        })
        with pytest.raises(UnknownPrototypeError):
            await compiled.windows.main.message.get_instance(None, None)

    def test_window_menu_conflict_rejected(self, error_message):
        with pytest.raises(SpecValidationError, match="controls its own menu"):
            compile_dialog(make_use_message_spec({"menu": {"rows": [[{"type": "button", "name": "b", "text": "x"}]]}}))

    def test_window_data_conflict_rejected(self, error_message):
        with pytest.raises(SpecValidationError, match="controls its own data"):
            compile_dialog(make_use_message_spec({"data": {"state": "err"}}))

    def test_not_registered_under_spec_name(self, error_message):
        compile_dialog(make_use_message_spec(), register=True)
        assert "dlg:err" not in BaseMessagePrototype._registry
        assert BaseMessagePrototype._registry["error_msg"] is error_message

    def test_serialization_roundtrip(self, error_message):
        spec = DialogSpec.from_dict(make_use_message_spec())
        dumped = spec.to_dict()
        assert dumped["windows"]["err"]["content"] == {"type": "use_message", "name": "error_msg"}
        assert DialogSpec.from_dict(dumped).to_dict() == dumped


class _GateResolver(SpecResolver):
    """Denies any name starting with ``secret``; delegates the rest."""

    def resolve(self, base_cls, name, scope):
        if name.startswith("secret"):
            raise PermissionError(f"denied {name}")
        return super().resolve(base_cls, name, scope)


class TestCustomResolver:
    async def test_allows_and_routes_button_through_resolver(self, cancel_button):
        spec = {
            "name": "d",
            "windows": {"main": {
                "content": {"type": "text", "text": "x"},
                "menu": {"rows": [[{"type": "use_button", "name": "cancel_btn"}]]},
            }},
        }
        compiled = compile_dialog(spec, resolver=_GateResolver())
        rows = await compiled.windows.main.menu.get_buttons(None, None)
        assert rows[0][0].type_name == "cancel_btn"

    async def test_denies_message_reference_at_render(self, clean_registries):
        class SecretMessage(TextMessagePrototype, type_name="secret_msg"):
            async def get_text_content(self, dialog, context):
                return TextContent(text="secret")

        compiled = compile_dialog(
            {"name": "d", "windows": {"main": {"content": {"type": "use_message", "name": "secret_msg"}}}},
            resolver=_GateResolver(),
        )
        with pytest.raises(PermissionError, match="denied secret_msg"):
            await compiled.windows.main.message.get_instance(None, None)
