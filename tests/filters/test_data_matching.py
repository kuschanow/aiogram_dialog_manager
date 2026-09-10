from aiogram_dialog_manager.filter._matching import data_matches


class TestDataMatches:
    def test_empty_criteria_matches_anything(self):
        assert data_matches({"a": 1}, {}) is True

    def test_top_level_equality(self):
        assert data_matches({"a": 1, "b": 2}, {"a": 1}) is True
        assert data_matches({"a": 1}, {"a": 2}) is False

    def test_missing_key_fails(self):
        assert data_matches({"a": 1}, {"b": 1}) is False

    def test_unhashable_value_is_ignored_when_not_filtered(self):
        assert data_matches({"a": 1, "payload": {"x": [1, 2]}}, {"a": 1}) is True

    def test_unhashable_value_compared_by_equality(self):
        assert data_matches({"payload": {"x": [1, 2]}}, {"payload": {"x": [1, 2]}}) is True

    def test_nested_path(self):
        data = {"payload": {"action": "confirm", "meta": {"n": 1}}}
        assert data_matches(data, {"payload__action": "confirm"}) is True
        assert data_matches(data, {"payload__meta__n": 1}) is True
        assert data_matches(data, {"payload__action": "cancel"}) is False

    def test_nested_path_missing_intermediate(self):
        assert data_matches({"payload": {}}, {"payload__action": "x"}) is False
        assert data_matches({}, {"payload__action": "x"}) is False

    def test_literal_key_with_separator_wins(self):
        assert data_matches({"a__b": 1}, {"a__b": 1}) is True

    def test_non_mapping_data_never_matches_criteria(self):
        # Guards against a non-dict payload (e.g. None) — treated as empty.
        assert data_matches(None, {"a": 1}) is False
        assert data_matches("not a dict", {"a": 1}) is False
        # ...but empty criteria still matches.
        assert data_matches(None, {}) is True
