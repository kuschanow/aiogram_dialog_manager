from typing import Dict, Any, Optional


class ButtonInstance:
    def __init__(self, button_id: str, type_name: str, state: str, data: Optional[Dict[str, Any]] = None):
        self.button_id = button_id
        self.type_name = type_name
        self.state = state
        self.data = data or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "button_id": self.button_id,
            "type_name": self.type_name,
            "state": self.state,
            "data": self.data
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ButtonInstance':
        return ButtonInstance(
            button_id=data["button_id"],
            type_name=data["type_name"],
            state=data["state"],
            data=data["data"]
        )
