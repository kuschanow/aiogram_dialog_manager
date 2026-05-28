from unittest.mock import MagicMock

from aiogram_dialog_manager.filter.menu import MenuFilter
from aiogram_dialog_manager.instance.button import ButtonInstance
from aiogram_dialog_manager.instance.menu import MenuInstance
from tests.helpers import StubMenu


class TestMenuFilter:
    def _make_menu_instance(self, type_name="my_menu", data=None) -> MenuInstance:
        btn = ButtonInstance(text="OK", type_name="ok")
        return MenuInstance(type_name=type_name, buttons=[[btn]], data=data or {})

    async def test_passes_with_prototype(self):
        proto = StubMenu(name="my_menu")
        menu = self._make_menu_instance("my_menu")
        f = MenuFilter(proto)
        assert await f(MagicMock(), menu=menu) is True

    async def test_passes_with_string_name(self):
        menu = self._make_menu_instance("my_menu")
        f = MenuFilter("my_menu")
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_when_menu_is_none(self):
        proto = StubMenu(name="my_menu")
        f = MenuFilter(proto)
        assert not await f(MagicMock(), menu=None)

    async def test_fails_when_name_does_not_match(self):
        menu = self._make_menu_instance("other_menu")
        f = MenuFilter("my_menu")
        assert not await f(MagicMock(), menu=menu)

    async def test_passes_with_matching_data(self):
        menu = self._make_menu_instance("my_menu", data={"page": "1"})
        f = MenuFilter("my_menu", page="1")
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_with_non_matching_data(self):
        menu = self._make_menu_instance("my_menu", data={"page": "1"})
        f = MenuFilter("my_menu", page="2")
        assert not await f(MagicMock(), menu=menu)

    async def test_passes_when_no_names_specified(self):
        menu = self._make_menu_instance("any_menu")
        f = MenuFilter()
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_when_no_names_and_menu_is_none(self):
        f = MenuFilter()
        assert not await f(MagicMock(), menu=None)

    async def test_passes_with_multiple_string_names_first_matches(self):
        menu = self._make_menu_instance("my_menu")
        f = MenuFilter("my_menu", "other_menu")
        assert await f(MagicMock(), menu=menu) is True

    async def test_passes_with_multiple_string_names_second_matches(self):
        menu = self._make_menu_instance("other_menu")
        f = MenuFilter("my_menu", "other_menu")
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_with_multiple_string_names_none_matches(self):
        menu = self._make_menu_instance("third_menu")
        f = MenuFilter("my_menu", "other_menu")
        assert not await f(MagicMock(), menu=menu)

    async def test_passes_with_multiple_prototypes(self):
        proto1 = StubMenu(name="my_menu")
        proto2 = StubMenu(name="other_menu")
        menu = self._make_menu_instance("other_menu")
        f = MenuFilter(proto1, proto2)
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_with_multiple_prototypes_none_matches(self):
        proto1 = StubMenu(name="my_menu")
        proto2 = StubMenu(name="other_menu")
        menu = self._make_menu_instance("third_menu")
        f = MenuFilter(proto1, proto2)
        assert not await f(MagicMock(), menu=menu)

    async def test_passes_with_multiple_names_and_matching_data(self):
        menu = self._make_menu_instance("other_menu", data={"page": "2"})
        f = MenuFilter("my_menu", "other_menu", page="2")
        assert await f(MagicMock(), menu=menu) is True

    async def test_fails_with_multiple_names_matching_type_but_wrong_data(self):
        menu = self._make_menu_instance("other_menu", data={"page": "1"})
        f = MenuFilter("my_menu", "other_menu", page="2")
        assert not await f(MagicMock(), menu=menu)
