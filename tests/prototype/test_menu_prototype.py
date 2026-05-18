import pytest

from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from aiogram_dialog_manager.prototype.menu import MenuPrototype
from tests.helpers import StubMenu


class TestMenuPrototypeRegistry:
    def test_registration_sets_name_property(self, monkeypatch):
        monkeypatch.setattr(MenuPrototype, "_registry", MenuPrototype._registry.copy())

        class MyMenu(MenuPrototype, name="unique_menu_xyz"):
            async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
                return []

        assert MyMenu().name == "unique_menu_xyz"
        assert "unique_menu_xyz" in MenuPrototype._registry

    def test_duplicate_name_raises(self, monkeypatch):
        monkeypatch.setattr(MenuPrototype, "_registry", MenuPrototype._registry.copy())

        class First(MenuPrototype, name="dup_menu_xyz"):
            async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
                return []

        with pytest.raises(ValueError, match="dup_menu_xyz"):
            class Second(MenuPrototype, name="dup_menu_xyz"):
                async def get_buttons(self, dialog, context) -> list[list[ButtonInstance]]:
                    return []


class TestMenuPrototype:
    async def test_get_instance_returns_menu_instance(self, operator):
        proto = StubMenu(name="my_menu")
        instance = await proto.get_instance(operator, context=None)
        assert isinstance(instance, MenuInstance)
        assert instance.type_name == "my_menu"
        assert len(instance.buttons) == 1

    async def test_get_data_default_empty(self, operator):
        proto = StubMenu()
        data = await proto.get_data(operator, None)
        assert data == {}

    async def test_get_additional_reply_parameters_default_none(self, operator):
        proto = StubMenu()
        result = await proto.get_additional_reply_parameters(operator, None)
        assert result is None

    def test_str_representation(self):
        proto = StubMenu(name="test_menu")
        assert "test_menu" in str(proto)
