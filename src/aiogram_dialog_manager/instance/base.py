import json

import pydantic_core
from aiogram.client.default import Default
from pydantic import BaseModel

_DEFAULT_MARKER = "##__aiogram_default__##"


def _default_fallback(v):
    if isinstance(v, Default):
        return _DEFAULT_MARKER
    raise TypeError(f"Object of type {type(v).__name__} is not JSON serializable")


def _strip_markers(obj):
    if isinstance(obj, dict):
        return {k: _strip_markers(v) for k, v in obj.items() if v != _DEFAULT_MARKER}
    if isinstance(obj, list):
        return [_strip_markers(v) for v in obj if v != _DEFAULT_MARKER]
    return obj


class BaseDialogModel(BaseModel):
    """Base model that produces a JSON-safe dict when model_dump(mode='json') is called.

    Uses pydantic_core.to_json for correct serialisation of all standard types
    (datetime, UUID, Enum, etc.) and strips aiogram Default sentinels via a fallback.
    Stripped fields are restored from field defaults on model_validate.
    """

    def model_dump(self, *, mode="python", **kwargs):
        if mode == "json":
            return _strip_markers(
                json.loads(pydantic_core.to_json(self, fallback=_default_fallback))
            )
        return super().model_dump(mode=mode, **kwargs)
