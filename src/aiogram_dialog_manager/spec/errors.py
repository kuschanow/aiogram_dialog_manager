"""Exceptions of the declarative dialog spec subsystem.

All errors raised by the spec core derive from :class:`SpecError`, so callers can
catch the whole family with a single except clause.
"""


class SpecError(Exception):
    """Base class for all spec-related errors."""


class SpecValidationError(SpecError):
    """Model-level validation failed (bad references, duplicate names, etc.)."""


class ExpressionEvaluationError(SpecError):
    """An expression raised during evaluation (type error, division by zero, ...).

    Missing data paths are *not* an error — they evaluate to ``None``.
    """


class UnknownNodeTypeError(SpecError):
    """A node dict references a ``type`` that is not registered."""


class UnknownFunctionError(SpecError):
    """A ``call`` node references a function that is not registered."""


class UnknownProviderError(SpecError):
    """A ``provider`` node references a provider that is not registered."""


class UnknownReferenceError(SpecError):
    """A ``ref`` node references a name that is not present in ``defs``."""


class UnknownPrototypeError(SpecError):
    """A ``use`` node references a prototype ``type_name`` that is not
    registered in the corresponding prototype registry."""
