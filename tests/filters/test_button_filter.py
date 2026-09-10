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

    async def test_passes_with_unhashable_button_data(self):
        # Regression: button.data may hold dict/list values. A set-based subset
        # check raised "TypeError: unhashable type: 'dict'"; matching by key must
        # tolerate unhashable values it does not filter on.
        btn = self._make_button("ok_btn", data={"x": "1", "payload": {"a": [1, 2]}})
        f = ButtonFilter("ok_btn", x="1")
        assert await f(MagicMock(), button=btn) is True

    async def test_name_only_match_ignores_unhashable_button_data(self):
        btn = self._make_button("ok_btn", data={"payload": {"a": [1, 2]}, "items": [1, 2]})
        f = ButtonFilter("ok_btn")
        assert await f(MagicMock(), button=btn) is True

    async def test_matches_unhashable_data_value_by_equality(self):
        btn = self._make_button("ok_btn", data={"payload": {"a": [1, 2]}})
        f = ButtonFilter("ok_btn", payload={"a": [1, 2]})
        assert await f(MagicMock(), button=btn) is True

    async def test_matches_nested_path_with_separator(self):
        btn = self._make_button("ok_btn", data={"payload": {"action": "confirm"}})
        f = ButtonFilter("ok_btn", payload__action="confirm")
        assert await f(MagicMock(), button=btn) is True

    async def test_fails_nested_path_wrong_value(self):
        btn = self._make_button("ok_btn", data={"payload": {"action": "cancel"}})
        f = ButtonFilter("ok_btn", payload__action="confirm")
        assert not await f(MagicMock(), button=btn)

    async def test_fails_nested_path_missing_key(self):
        btn = self._make_button("ok_btn", data={"payload": {}})
        f = ButtonFilter("ok_btn", payload__action="confirm")
        assert not await f(MagicMock(), button=btn)

    async def test_literal_key_with_separator_still_matches(self):
        # Backward compatible: an exact top-level key wins over path-splitting.
        btn = self._make_button("ok_btn", data={"a__b": "1"})
        f = ButtonFilter("ok_btn", a__b="1")
        assert await f(MagicMock(), button=btn) is True
