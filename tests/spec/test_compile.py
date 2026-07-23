"""Tests for compilation, registration and the interpreting prototypes."""
import pytest

from aiogram_dialog_manager.filter import ButtonFilter
from aiogram_dialog_manager.instance.dialog import DialogInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.instance.message import MessageTarget
from aiogram_dialog_manager.prototype.base import BaseMessagePrototype
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from aiogram_dialog_manager.prototype.dialog import DialogPrototype
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from aiogram_dialog_manager.spec import (
    ButtonSpec,
    CompiledDialog,
    DialogSpec,
    ExpressionEvaluationError,
    Namespace,
    PathNode,
    RefNode,
    SpecValidationError,
    compile_dialog,
    is_spec_registered,
    iter_spec_nodes,
    register_spec_prototype,
)
from aiogram_dialog_manager.spec import registration
from aiogram_dialog_manager.spec.content import (
    SpecDocumentMessagePrototype,
    SpecMediaGroupMessagePrototype,
    SpecPhotoMessagePrototype,
)
from aiogram_dialog_manager.spec.registries import ProviderRegistry
from tests.spec.conftest import FakeDialog


@pytest.fixture
def clean_registries(monkeypatch):
    for base in (BaseMessagePrototype, ButtonPrototype, MenuPrototype, DialogPrototype):
        monkeypatch.setattr(base, "_registry", base._registry.copy())
    monkeypatch.setattr(registration, "_spec_registered_names", {})


def make_spec(**overrides) -> DialogSpec:
    payload = {
        "name": "settings",
        "windows": {
            "main": {
                "content": {"type": "text", "text": ["Hello, ", {"type": "path", "path": "data.name"}]},
                "menu": {
                    "rows": [
                        [{"type": "button", "name": "save", "text": "Save", "data": {"page": {"type": "path", "path": "data.page"}}}],
                        {"type": "if", "when": {"type": "path", "path": "data.is_admin"},
                         "then": {"type": "row", "items": [{"type": "button", "name": "admin", "text": "Admin"}]}},
                        {"type": "row", "items": [{"type": "ref", "name": "back"}]},
                    ],
                },
            },
            "notify": {"content": {"type": "text", "text": {"type": "t", "key": "notify_text"}}},
        },
        "defs": {"back": {"type": "button", "name": "back", "text": "Back"}},
    }
    payload.update(overrides)
    return DialogSpec.from_dict(payload)


class TestNamespace:
    def test_attribute_and_item_access(self):
        ns = Namespace({"a": 1})
        assert ns.a == 1
        assert ns["a"] == 1
        assert "a" in ns
        assert list(ns) == ["a"]
        assert len(ns) == 1

    def test_unknown_attribute_lists_available(self):
        with pytest.raises(AttributeError, match="available: a"):
            Namespace({"a": 1}).b

    def test_empty_namespace_message(self):
        with pytest.raises(AttributeError, match=r"available: \(none\)"):
            Namespace({}).anything


class TestIterSpecNodes:
    def test_walks_models_dicts_lists_and_tuples(self):
        spec = make_spec()
        names = {node.name for node in iter_spec_nodes(spec) if isinstance(node, ButtonSpec)}
        assert names == {"save", "admin", "back"}
        assert any(isinstance(node, RefNode) for node in iter_spec_nodes(spec))
        assert list(iter_spec_nodes(("x", [PathNode(path="data.a")]))) == [PathNode(path="data.a")]


class TestValidation:
    def test_unknown_ref_in_windows_rejected(self):
        spec = make_spec(defs={})
        with pytest.raises(SpecValidationError, match="Reference 'back' \\(used in windows\\)"):
            compile_dialog(spec)

    def test_unknown_ref_in_defs_rejected(self):
        spec = make_spec(defs={
            "back": {"type": "button", "name": "back", "text": "Back"},
            "broken": {"type": "ref", "name": "ghost"},
        })
        with pytest.raises(SpecValidationError, match="Reference 'ghost' \\(used in defs\\)"):
            compile_dialog(spec)

    def test_cyclic_defs_rejected(self):
        spec = make_spec(defs={
            "back": {"type": "button", "name": "back", "text": "Back"},
            "a": {"type": "ref", "name": "b"},
            "b": {"type": "ref", "name": "a"},
        })
        with pytest.raises(SpecValidationError, match="Cyclic reference in defs"):
            compile_dialog(spec)

    def test_self_cycle_rejected(self):
        spec = make_spec(defs={
            "back": {"type": "button", "name": "back", "text": "Back"},
            "loop": {"type": "ref", "name": "loop"},
        })
        with pytest.raises(SpecValidationError, match="loop -> loop"):
            compile_dialog(spec)

    def test_acyclic_shared_defs_allowed(self):
        spec = make_spec(defs={
            "back": {"type": "button", "name": "back", "text": "Back"},
            "footer": {"type": "row", "items": [{"type": "ref", "name": "back"}]},
        })
        compile_dialog(spec)

    def test_duplicate_button_names_rejected(self):
        spec = make_spec()
        spec.windows["main"].menu.rows.append(
            ButtonSpec(name="save", text="Another save")
        )
        with pytest.raises(SpecValidationError, match="Duplicate button name 'save'"):
            compile_dialog(spec)


class TestCompiledDialog:
    def test_deterministic_prototype_names(self):
        compiled = compile_dialog(make_spec())
        assert compiled.dialog_prototype.name == "settings"
        assert compiled.windows.main.message.name == "settings:main"
        assert compiled.windows.main.menu.name == "settings:main:menu"
        assert compiled.windows.main.buttons.save.name == "settings:main:save"
        assert compiled.windows.main.buttons.back.name == "settings:main:back"

    def test_window_without_menu(self):
        compiled = compile_dialog(make_spec())
        assert compiled.windows.notify.menu is None
        assert len(compiled.windows.notify.buttons) == 0

    def test_accepts_canonical_dict(self):
        compiled = compile_dialog(make_spec().to_dict())
        assert isinstance(compiled, CompiledDialog)
        assert compiled.spec.name == "settings"

    def test_exposes_spec_and_runtime(self):
        spec = make_spec()
        compiled = compile_dialog(spec, translator=lambda msgid, locale: msgid)
        assert compiled.spec is spec
        assert compiled.runtime.dialog_name == "settings"
        assert compiled.windows.main.menu.spec is spec.windows["main"].menu
        assert compiled.windows.main.buttons.save.spec.name == "save"

    def test_custom_registries_are_used(self):
        providers = ProviderRegistry({"p": lambda dialog, context: 1})
        compiled = compile_dialog(make_spec(), providers=providers)
        assert compiled.runtime.providers is providers

    async def test_dialog_prototype_creates_instance(self):
        compiled = compile_dialog(make_spec())
        instance = await compiled.dialog_prototype.get_instance(user_id=1, chat_id=2)
        assert instance.type_name == "settings"


class TestRegistration:
    def test_register_all_prototypes(self, clean_registries):
        compiled = compile_dialog(make_spec(), register=True)
        assert DialogPrototype._registry["settings"] is compiled.dialog_prototype
        assert BaseMessagePrototype._registry["settings:main"] is compiled.windows.main.message
        assert MenuPrototype._registry["settings:main:menu"] is compiled.windows.main.menu
        assert ButtonPrototype._registry["settings:main:save"] is compiled.windows.main.buttons.save
        assert is_spec_registered(ButtonPrototype, "settings:main:save")
        assert not is_spec_registered(ButtonPrototype, "unknown")

    def test_reregistration_replaces_spec_entries(self, clean_registries):
        compile_dialog(make_spec(), register=True)
        recompiled = compile_dialog(make_spec()).register()
        assert ButtonPrototype._registry["settings:main:save"] is recompiled.windows.main.buttons.save

    def test_collision_with_python_class_rejected(self, clean_registries):
        class LegacyButton(ButtonPrototype, type_name="settings:main:save"):
            async def get_state(self, dialog, context) -> str:
                return "legacy"

        with pytest.raises(SpecValidationError, match="replace semantics apply only to spec-registered entries"):
            compile_dialog(make_spec(), register=True)

    def test_python_classes_still_fail_on_duplicate(self, clean_registries):
        register_spec_prototype(ButtonPrototype, "taken", object())

        with pytest.raises(ValueError, match="already registered"):
            class Duplicate(ButtonPrototype, type_name="taken"):
                async def get_state(self, dialog, context) -> str:
                    return "x"


class TestMessagePrototypes:
    async def test_text_window_renders(self):
        compiled = compile_dialog(make_spec())
        content = await compiled.windows.main.message.get_text_content(FakeDialog({"name": "Roman"}), None)
        assert content.text == "Hello, Roman"

    async def test_text_none_raises(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {"content": {"type": "text", "text": {"type": "path", "path": "data.missing"}}}},
        })
        compiled = compile_dialog(spec)
        with pytest.raises(ExpressionEvaluationError, match="Text of window 'w'"):
            await compiled.windows.w.message.get_text_content(FakeDialog(), None)

    async def test_translation_uses_translator(self):
        compiled = compile_dialog(make_spec(), translator=lambda msgid, locale: f"{msgid}@{locale}")
        content = await compiled.windows.notify.message.get_text_content(FakeDialog(), {"locale": "ru"})
        assert content.text == "notify_text@ru"

    async def test_photo_window(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {"content": {
                "type": "photo",
                "photo": {"type": "path", "path": "data.file"},
                "caption": ["Album ", {"type": "path", "path": "data.title"}],
                "has_spoiler": True,
            }}},
        })
        prototype = compile_dialog(spec).windows.w.message
        assert isinstance(prototype, SpecPhotoMessagePrototype)
        dialog = FakeDialog({"file": "fid", "title": "T"})
        assert await prototype.get_photo(dialog, None) == "fid"
        assert (await prototype.get_text_content(dialog, None)).text == "Album T"
        extra = await prototype.get_extra_params(dialog, None)
        assert extra.has_spoiler is True
        assert extra.show_caption_above_media is None
        assert prototype.content is spec.windows["w"].content
        assert prototype.menu_prototype is None

    async def test_document_window(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {"content": {
                "type": "document",
                "document": "doc_id",
                "disable_content_type_detection": True,
            }}},
        })
        prototype = compile_dialog(spec).windows.w.message
        assert isinstance(prototype, SpecDocumentMessagePrototype)
        assert await prototype.get_document(FakeDialog(), None) == "doc_id"
        assert (await prototype.get_text_content(FakeDialog(), None)).text is None
        extra = await prototype.get_extra_params(FakeDialog(), None)
        assert extra.disable_content_type_detection is True

    async def test_media_group_window(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {"content": {
                "type": "media_group",
                "items": [{
                    "type": "foreach",
                    "over": {"type": "path", "path": "data.photos"},
                    "body": {"type": "media_item", "media_type": "photo",
                             "media": {"type": "path", "path": "item.file"},
                             "caption": {"type": "path", "path": "item.title"}},
                }],
            }}},
        })
        prototype = compile_dialog(spec).windows.w.message
        assert isinstance(prototype, SpecMediaGroupMessagePrototype)
        dialog = FakeDialog({"photos": [{"file": "f1", "title": "a"}, {"file": "f2", "title": "b"}]})
        media = await prototype.get_media(dialog, None)
        assert [m.media for m in media] == ["f1", "f2"]

    async def test_get_menu_returns_instance(self):
        compiled = compile_dialog(make_spec())
        menu = await compiled.windows.main.message.get_menu(FakeDialog({"is_admin": True}), None)
        assert isinstance(menu, MenuInstance)
        assert menu.type_name == "settings:main:menu"

    async def test_get_menu_none_without_menu(self):
        compiled = compile_dialog(make_spec())
        assert await compiled.windows.notify.message.get_menu(FakeDialog(), None) is None


class TestMenuPrototype:
    async def test_conditional_rows(self):
        compiled = compile_dialog(make_spec())
        menu_prototype = compiled.windows.main.menu

        rows = await menu_prototype.get_buttons(FakeDialog({"is_admin": True}), None)
        assert [[button.type_name for button in row] for row in rows] == [
            ["settings:main:save"], ["settings:main:admin"], ["settings:main:back"],
        ]

        rows = await menu_prototype.get_buttons(FakeDialog({"is_admin": False}), None)
        assert [[button.type_name for button in row] for row in rows] == [
            ["settings:main:save"], ["settings:main:back"],
        ]

    async def test_non_list_row_raises(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {
                "content": {"type": "text", "text": "x"},
                "menu": {"rows": [{"type": "path", "path": "data.x"}]},
            }},
        })
        compiled = compile_dialog(spec)
        with pytest.raises(ExpressionEvaluationError, match="Menu row must evaluate to a list"):
            await compiled.windows.w.menu.get_buttons(FakeDialog({"x": 5}), None)

    async def test_all_rows_empty_yields_no_instance(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {
                "content": {"type": "text", "text": "x"},
                "menu": {"rows": [{"type": "row", "items": [
                    {"type": "if", "when": {"type": "path", "path": "data.show"},
                     "then": {"type": "button", "name": "b", "text": "B"}},
                ]}]},
            }},
        })
        compiled = compile_dialog(spec)
        assert await compiled.windows.w.menu.get_instance(FakeDialog({"show": False}), None) is None
        instance = await compiled.windows.w.menu.get_instance(FakeDialog({"show": True}), None)
        assert instance.buttons[0][0].text == "B"

    async def test_reply_keyboard_with_parameters(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {
                "content": {"type": "text", "text": "x"},
                "menu": {
                    "rows": [[{"type": "button", "name": "b", "text": "B"}]],
                    "keyboard_type": "reply",
                    "reply_parameters": {"input_field_placeholder": {"type": "path", "path": "data.ph"}},
                },
            }},
        })
        compiled = compile_dialog(spec)
        instance = await compiled.windows.w.menu.get_instance(FakeDialog({"ph": "Type here"}), None)
        assert instance.keyboard_type == "reply"
        assert instance.additional_reply_parameters.input_field_placeholder == "Type here"


class TestButtonPrototype:
    async def test_getters(self):
        compiled = compile_dialog(make_spec())
        button = compiled.windows.main.buttons.save
        dialog = FakeDialog({"page": 4})
        assert await button.get_state(dialog, None) == "Save"
        assert await button.get_data(dialog, None) == {"page": 4}
        assert await button.get_inline_additional_parameters(dialog, None) is None
        assert await button.get_common_additional_parameters(dialog, None) is None

    async def test_get_instance_matches_menu_rendering(self):
        compiled = compile_dialog(make_spec())
        instance = await compiled.windows.main.buttons.save.get_instance(FakeDialog({"page": 1}), None)
        assert instance.type_name == "settings:main:save"
        assert instance.data == {"page": 1}

    async def test_additional_parameters_evaluated(self):
        spec = DialogSpec.from_dict({
            "name": "d",
            "windows": {"w": {
                "content": {"type": "text", "text": "x"},
                "menu": {"rows": [[{
                    "type": "button", "name": "site", "text": "Site",
                    "inline": {"url": "https://example.com"},
                    "common": {"request_contact": True},
                }]]},
            }},
        })
        button = compile_dialog(spec).windows.w.buttons.site
        inline = await button.get_inline_additional_parameters(FakeDialog(), None)
        common = await button.get_common_additional_parameters(FakeDialog(), None)
        assert inline.url == "https://example.com"
        assert common.request_contact is True


class TestRuntimeCompatibility:
    async def test_button_filter_accepts_handle_and_string(self):
        compiled = compile_dialog(make_spec())
        button_instance = await compiled.windows.main.buttons.save.get_instance(FakeDialog({"page": 0}), None)

        assert await ButtonFilter(compiled.windows.main.buttons.save)(None, button_instance)
        assert await ButtonFilter("settings:main:save")(None, button_instance)
        assert not await ButtonFilter("settings:main:other")(None, button_instance)
        assert await ButtonFilter(compiled.windows.main.buttons.save, page=0)(None, button_instance)
        assert not await ButtonFilter(compiled.windows.main.buttons.save, page=9)(None, button_instance)

    async def test_send_through_dialog_operator(self, operator, mock_bot):
        compiled = compile_dialog(make_spec())
        operator.data["name"] = "Roman"
        operator.data["is_admin"] = True

        record = await operator.send_message(compiled.windows.main.message, MessageTarget(chat_id=100))

        assert record.type_name == "settings:main"
        sent = mock_bot.send_message.call_args.kwargs
        assert sent["text"] == "Hello, Roman"
        callback_buttons = sent["reply_markup"].inline_keyboard
        assert [len(row) for row in callback_buttons] == [1, 1, 1]

    async def test_instances_survive_storage(self, memory_storage):
        compiled = compile_dialog(make_spec())
        instance = await compiled.dialog_prototype.get_instance(user_id=1, chat_id=2)
        await memory_storage.set(f"dialog:{instance.id}", instance.model_dump(mode="json"))
        loaded = DialogInstance.model_validate(await memory_storage.get_dict(f"dialog:{instance.id}"))
        assert loaded.type_name == "settings"


class TestWindowData:
    def make_compiled(self, *, window_extra=None, dialog_extra=None):
        payload = {
            "name": "wizard",
            "windows": {
                "step_one": {
                    "content": {"type": "text", "text": "hi"},
                    **(window_extra or {}),
                },
            },
            **(dialog_extra or {}),
        }
        return compile_dialog(DialogSpec.from_dict(payload))

    async def test_default_data_is_context_only(self):
        compiled = self.make_compiled()
        assert await compiled.windows.step_one.message.get_data(None, {"a": 1}) == {"a": 1}

    async def test_window_data_evaluated_and_merged_under_context(self):
        compiled = self.make_compiled(window_extra={
            "data": {"state": "step_one", "page": {"type": "path", "path": "data.page"}},
        })
        data = await compiled.windows.step_one.message.get_data(FakeDialog({"page": 3}), {"page": 0, "extra": True})
        # context wins over window defaults
        assert data == {"state": "step_one", "page": 0, "extra": True}

    async def test_window_name_key_stamps_window_name(self):
        compiled = self.make_compiled(dialog_extra={"window_name_key": "state"})
        data = await compiled.windows.step_one.message.get_data(None, {"a": 1})
        assert data == {"state": "step_one", "a": 1}

    async def test_merge_order_name_key_then_data_then_context(self):
        compiled = self.make_compiled(
            window_extra={"data": {"state": "from_data", "step": 1}},
            dialog_extra={"window_name_key": "state"},
        )
        assert await compiled.windows.step_one.message.get_data(None, None) == {"state": "from_data", "step": 1}
        assert await compiled.windows.step_one.message.get_data(None, {"state": "override"}) == {
            "state": "override", "step": 1,
        }

    async def test_window_data_lands_in_message_instance(self):
        compiled = self.make_compiled(dialog_extra={"window_name_key": "state"})
        instance = await compiled.windows.step_one.message.get_instance(FakeDialog(), None)
        assert instance.data == {"state": "step_one"}
