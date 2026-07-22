"""The starter set of pure expression functions.

The registry is open: users register their own pure functions the same way
(the same principle as the provider registry).
"""
from typing import Any, Optional

from aiogram_dialog_manager.spec.registries import FunctionRegistry


def _join(items: list, sep: str = "") -> str:
    return sep.join(str(item) for item in items)


def _split(value: str, sep: Optional[str] = None) -> list[str]:
    return value.split(sep)


def _strip(value: str, chars: Optional[str] = None) -> str:
    return value.strip(chars)


def _format(template: str, *args: Any, **kwargs: Any) -> str:
    return template.format(*args, **kwargs)


def _default(value: Any, fallback: Any) -> Any:
    return fallback if value is None else value


def _range(*args: int) -> list[int]:
    return list(range(*args))


def _sorted(items: list, reverse: bool = False) -> list:
    return sorted(items, reverse=reverse)


def _keys(mapping: dict) -> list:
    return list(mapping.keys())


def _values(mapping: dict) -> list:
    return list(mapping.values())


_STARTER_FUNCTIONS = {
    "len": len,
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "round": round,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "join": _join,
    "split": _split,
    "upper": str.upper,
    "lower": str.lower,
    "strip": _strip,
    "format": _format,
    "default": _default,
    "range": _range,
    "sorted": _sorted,
    "keys": _keys,
    "values": _values,
}


def create_default_function_registry() -> FunctionRegistry:
    """A fresh registry preloaded with the starter set."""
    return FunctionRegistry(_STARTER_FUNCTIONS)
