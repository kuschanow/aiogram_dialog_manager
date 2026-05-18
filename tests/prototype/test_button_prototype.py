import pytest

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.prototype.button import ButtonPrototype
from tests.helpers import StubButton


class TestButtonPrototypeRegistry:
    def test_registration_sets_name_property(self, monkeypatch):
        monkeypatch.setattr(ButtonPrototype, "_registry", ButtonPrototype._registry.copy())

        class MyBtn(ButtonPrototype, name="unique_btn_xyz"):
            async def get_state(self, dialog, context):
                return "x"

        assert MyBtn()._prototype_name == "unique_btn_xyz"
        assert MyBtn().name == "unique_btn_xyz"
        assert "unique_btn_xyz" in ButtonPrototype._registry

    def test_duplicate_name_raises(self, monkeypatch):
        monkeypatch.setattr(ButtonPrototype, "_registry", ButtonPrototype._registry.copy())

        class First(ButtonPrototype, name="dup_btn_xyz"):
            async def get_state(self, dialog, context):
                return "x"

        with pytest.raises(ValueError, match="dup_btn_xyz"):
            class Second(ButtonPrototype, name="dup_btn_xyz"):
                async def get_state(self, dialog, context):
                    return "y"


class TestButtonPrototype:
    async def test_get_instance_returns_button_instance(self, operator):
        proto = StubButton(name="my_btn", state="Click me")
        instance = await proto.get_instance(operator, context=None)
        assert isinstance(instance, ButtonInstance)
        assert instance.text == "Click me"
        assert instance.type_name == "my_btn"

    async def test_get_instance_with_context(self, operator):
        proto = StubButton()
        instance = await proto.get_instance(operator, context={"x": 1})
        assert instance is not None

    async def test_get_data_default_empty(self, operator):
        proto = StubButton()
        data = await proto.get_data(operator, None)
        assert data == {}

    async def test_get_inline_additional_parameters_default_none(self, operator):
        proto = StubButton()
        result = await proto.get_inline_additional_parameters(operator, None)
        assert result is None

    async def test_get_common_additional_parameters_default_none(self, operator):
        proto = StubButton()
        result = await proto.get_common_additional_parameters(operator, None)
        assert result is None

    def test_str_representation(self):
        proto = StubButton(name="my_btn")
        assert "my_btn" in str(proto)
