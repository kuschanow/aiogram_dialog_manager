"""Shared data-matching for filters.

Filters accept ``**data`` criteria and match them against an instance's ``data``
dict (a button/menu/message/dialog payload). Matching here:

* Never hashes the instance's values, so ``data`` may hold unhashable values
  (dict/list). A previous ``set(data.items())`` check raised
  ``TypeError: unhashable type: 'dict'`` on such payloads.
* Supports nested access via the ``__`` separator, e.g. ``payload__action="ok"``
  matches ``data["payload"]["action"] == "ok"``. An exact top-level key is tried
  first, so a literal key that itself contains ``__`` keeps matching as before.
"""

from typing import Any, Mapping

_MISSING = object()


def _resolve(data: Mapping[str, Any], path: str) -> Any:
    """Look up ``path`` in ``data``; return ``_MISSING`` if absent.

    An exact top-level key wins over path-splitting (backward compatible), then
    ``__`` walks nested mappings.
    """
    if path in data:
        return data[path]
    current: Any = data
    for part in path.split("__"):
        if isinstance(current, Mapping) and part in current:
            current = current[part]
        else:
            return _MISSING
    return current


def data_matches(data: Any, criteria: Mapping[str, Any]) -> bool:
    """True if every criterion matches ``data`` (nested paths via ``__``).

    Empty ``criteria`` matches anything. Values are compared by equality, never
    hashed, so ``data`` may contain dict/list values.
    """
    if not isinstance(data, Mapping):
        data = {}
    return all(_resolve(data, key) == value for key, value in criteria.items())
