from datetime import datetime
from typing import Dict, Any, Optional

from .menu import MenuInstance


class MessageInstance:
    def __init__(self,
                 date: datetime,
                 message_id: int,
                 user_id: int,
                 text: str,
                 menu: Optional[MenuInstance] = None,
                 marks: Optional[Dict[str, Any]] = None):
        self.date = date
        self.message_id = message_id
        self.user_id = user_id
        self.text = text
        self.menu = menu
        self.marks = marks or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S.%f"),
            "message_id": self.message_id,
            "user_id": self.user_id,
            "text": self.text,
            "menu": self.menu.to_dict(),
            "marks": self.marks
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'MessageInstance':
        return MessageInstance(
            date=datetime.strptime(data["date"], "%Y-%m-%d %H:%M:%S.%f"),
            message_id=data["message_id"],
            user_id=data["user_id"],
            text=data["text"],
            menu=MenuInstance.from_dict(data["menu"]),
            marks=data["marks"]
        )