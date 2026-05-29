from aiogram.client.default import Default
from pydantic import BaseModel


def _strip_defaults(obj):
    if isinstance(obj, dict):
        return {k: _strip_defaults(v) for k, v in obj.items() if not isinstance(v, Default)}
    if isinstance(obj, list):
        return [_strip_defaults(v) for v in obj]
    return obj


class BaseDialogModel(BaseModel):
    """Base model that strips aiogram Default sentinels when serializing to JSON.

    Default objects represent bot-level configuration values (e.g. parse_mode)
    and cannot be JSON-serialized. Excluding them is safe because pydantic restores
    them from field defaults during model_validate.
    """

    def model_dump(self, *, mode="python", **kwargs):
        if mode == "json":
            return _strip_defaults(super().model_dump(mode="python", **kwargs))
        return super().model_dump(mode=mode, **kwargs)
