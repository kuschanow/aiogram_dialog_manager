import inspect
from collections import ChainMap
from typing import Dict, Any, Optional, Callable, TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from aiogram_dialog_manager.instance import ButtonInstance
    from aiogram_dialog_manager import Dialog


class ButtonPrototype:
    def __init__(self, name: str, states: Dict[str, str], state_selector: Optional[Callable] = None):
        self.name = name
        self.states = states
        self.state_selector = state_selector or (lambda: next(iter(self.states.items()))[0])

    def _get_relevant_kwargs(self, **kwargs) -> Dict[str, Any]:
        func_args = inspect.signature(self.state_selector).parameters
        relevant_kwargs = {k: v for k, v in kwargs.items() if k in func_args}
        return relevant_kwargs

    def _build_button_instance(self, selected_state_key: str, dialog: Optional['Dialog'] = None, data: Optional[Dict[str, Any]] = None) -> 'ButtonInstance':
        from aiogram_dialog_manager.instance import ButtonInstance

        state = (
                self.states[selected_state_key] %
                ChainMap(self.states, data or {}, dialog.values if dialog else {}) %
                ChainMap(data or {}, dialog.values if dialog else {}) %
                (dialog.values if dialog else {})
        )
        return ButtonInstance(
            button_id=str(uuid4()),
            type_name=self.name,
            state=state,
            data=data
        )

    def get_instance(self, data: Optional[Dict[str, Any]] = None, dialog: Optional['Dialog'] = None, **kwargs) -> 'ButtonInstance':
        relevant_kwargs = self._get_relevant_kwargs(prototype=self, dialog=dialog, data=data, **kwargs)
        selected_state_key = self.state_selector(**relevant_kwargs)
        return self._build_button_instance(selected_state_key, dialog, data)
