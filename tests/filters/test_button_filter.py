from unittest.mock import MagicMock

from aiogram_dialog_manager.filter.button import ButtonFilter
from aiogram_dialog_manager.instance.button import ButtonInstance
from tests.helpers import StubButton


class TestButtonFilter:
    def _make_button(self, type_name="ok_btn", data=None) -> ButtonInstance:
        return ButtonInstance(text="OK", type_name=type_name, data=data or {})

    async def test_passes_with_prototype(self):
        proto = StubButton(name="ok_btn")
        btn = self._make_button("ok_btn")
        f = ButtonFilter(proto)
        assert await f(MagicMock(), button=btn) is True

    async def test_passes_with_string_name(self):
        btn = self._make_button("ok_btn")
        f = ButtonFilter("ok_btn")
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_when_button_is_none(self):
        proto = StubButton(name="ok_btn")
        f = ButtonFilter(proto)
        assert not await f(MagicMock(), button=None)

    async def test_fails_when_name_does_not_match(self):
        btn = self._make_button("other_btn")
        f = ButtonFilter("ok_btn")
        assert not await f(MagicMock(), button=btn)

    async def test_passes_with_matching_data(self):
        btn = self._make_button("ok_btn", data={"x": "1"})
        f = ButtonFilter("ok_btn", x="1")
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_with_non_matching_data(self):
        btn = self._make_button("ok_btn", data={"x": "1"})
        f = ButtonFilter("ok_btn", x="2")
        assert not await f(MagicMock(), button=btn)

    async def test_passes_when_no_names_specified(self):
        btn = self._make_button("any_btn")
        f = ButtonFilter()
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_when_no_names_and_button_is_none(self):
        f = ButtonFilter()
        assert not await f(MagicMock(), button=None)

    async def test_passes_with_multiple_string_names_first_matches(self):
        btn = self._make_button("ok_btn")
        f = ButtonFilter("ok_btn", "cancel_btn")
        assert await f(MagicMock(), button=btn) is True

    async def test_passes_with_multiple_string_names_second_matches(self):
        btn = self._make_button("cancel_btn")
        f = ButtonFilter("ok_btn", "cancel_btn")
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_with_multiple_string_names_none_matches(self):
        btn = self._make_button("other_btn")
        f = ButtonFilter("ok_btn", "cancel_btn")
        assert not await f(MagicMock(), button=btn)

    async def test_passes_with_multiple_prototypes(self):
        proto1 = StubButton(name="ok_btn")
        proto2 = StubButton(name="cancel_btn")
        btn = self._make_button("cancel_btn")
        f = ButtonFilter(proto1, proto2)
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_with_multiple_prototypes_none_matches(self):
        proto1 = StubButton(name="ok_btn")
        proto2 = StubButton(name="cancel_btn")
        btn = self._make_button("other_btn")
        f = ButtonFilter(proto1, proto2)
        assert not await f(MagicMock(), button=btn)

    async def test_passes_with_multiple_names_and_matching_data(self):
        btn = self._make_button("cancel_btn", data={"confirmed": "yes"})
        f = ButtonFilter("ok_btn", "cancel_btn", confirmed="yes")
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_with_multiple_names_matching_type_but_wrong_data(self):
        btn = self._make_button("cancel_btn", data={"confirmed": "no"})
        f = ButtonFilter("ok_btn", "cancel_btn", confirmed="yes")
        assert not await f(MagicMock(), button=btn)
