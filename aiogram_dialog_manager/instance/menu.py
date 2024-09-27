from typing import List, Dict, Any

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from .button import ButtonInstance


class MenuInstance:
    def __init__(self, buttons: List[List[ButtonInstance]]):
        self.buttons = buttons

    def get_button_by_id(self, button_id: str) -> ButtonInstance | None:
        for row in self.buttons:
            for button in row:
                if button.button_id == button_id:
                    return button

        return None

    def get_button_position(self, button_id: str) -> (int, int):
        for row in range(len(self.buttons)):
            for button in range(len(self.buttons[row])):
                if self.buttons[row][button].button_id == button_id:
                    return row, button

        return None, None

    def get_inline_keyboard(self) -> InlineKeyboardMarkup:
        buttons = [[
            InlineKeyboardButton(
                text=button.state,
                callback_data=f"b:{button.button_id}")
            for button in row]
            for row in self.buttons]

        return InlineKeyboardMarkup(inline_keyboard=buttons)

    def to_dict(self) -> Dict[str, Any]:
        return {"buttons": [[button.to_dict() for button in row] for row in self.buttons]}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MenuInstance':
        return MenuInstance([[ButtonInstance.from_dict(button) for button in row] for row in data["buttons"]])
