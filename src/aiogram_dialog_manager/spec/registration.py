"""Registration of spec prototypes in the shared prototype registries.

Spec prototypes live in the *same* registries as Python prototype classes,
under deterministic names derived from the model — ``type_name`` is stored in
the storage inside instances, so a restart with the same script must restore
the same names.

Re-registration (model reload, hot-reload, loading from a DB) replaces the
entry — but only for names previously registered through this module. Python
classes still fail on duplicates: there it is a real error.
"""
from typing import Any

from aiogram_dialog_manager.spec.errors import SpecValidationError

_spec_registered_names: dict[type, set[str]] = {}


def register_spec_prototype(base_cls: type, name: str, prototype: Any) -> None:
    """Register ``prototype`` under ``name`` in ``base_cls._registry``.

    Replace semantics apply only to names previously registered as spec
    entries; colliding with a Python prototype class raises.
    """
    registry: dict[str, Any] = base_cls._registry
    spec_names = _spec_registered_names.setdefault(base_cls, set())
    if name in registry and name not in spec_names:
        existing = registry[name]
        existing_name = getattr(existing, "__qualname__", type(existing).__qualname__)
        raise SpecValidationError(
            f"{base_cls.__name__} name '{name}' is already registered by {existing_name}; "
            f"replace semantics apply only to spec-registered entries"
        )
    registry[name] = prototype
    spec_names.add(name)


def is_spec_registered(base_cls: type, name: str) -> bool:
    return name in _spec_registered_names.get(base_cls, set())
