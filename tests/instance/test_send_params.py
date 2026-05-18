from aiogram.client.default import Default

from aiogram_dialog_manager.instance.message import SendParams


class TestSendParams:
    def test_round_trip_json_with_defaults(self):
        params = SendParams(disable_notification=True)
        dumped = params.model_dump(mode="json")
        restored = SendParams.model_validate(dumped)
        assert restored.disable_notification is True

    def test_restore_defaults_validator_non_dict_path(self):
        existing = SendParams()
        result = SendParams._restore_defaults(existing)
        assert result is existing

    def test_serialize_preserves_default_objects(self):
        params = SendParams()
        dumped = params.model_dump(mode="json")
        assert dumped["parse_mode"] == {"__default__": "parse_mode"}
        restored = SendParams.model_validate(dumped)
        assert isinstance(restored.parse_mode, Default)
