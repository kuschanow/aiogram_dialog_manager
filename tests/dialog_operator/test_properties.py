class TestDialogOperatorProperties:
    def test_name(self, operator, dialog_instance):
        assert operator.name == dialog_instance.type_name

    def test_user_id(self, operator, dialog_instance):
        assert operator.user_id == dialog_instance.user_id

    def test_chat_id(self, operator, dialog_instance):
        assert operator.chat_id == dialog_instance.chat_id

    def test_data(self, operator, dialog_instance):
        assert operator.data is dialog_instance.data

    def test_dialog(self, operator, dialog_instance):
        assert operator.dialog is dialog_instance

    def test_temp_is_dict(self, operator):
        assert isinstance(operator.temp, dict)
