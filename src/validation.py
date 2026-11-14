"""Reglas de validación de las muestras del reactor."""

import math
from enum import Enum


FIELD_RANGES = {"field2": (0.0, 100.0), "field3": (0.0, 100.0)}


class ValueErrorKind(Enum):
    REQUIRED = "required"
    NOT_NUMERIC = "not_numeric"
    NOT_FINITE = "not_finite"
    OUT_OF_RANGE = "out_of_range"


def parse_measurement(
    raw: object,
    min_value: float | None = None,
    max_value: float | None = None,
) -> tuple[float, None] | tuple[None, ValueErrorKind]:
    if isinstance(raw, str):
        raw = raw.strip().replace(",", ".")
        if not raw:
            return None, ValueErrorKind.REQUIRED
    if raw is None or isinstance(raw, bool):
        return None, ValueErrorKind.REQUIRED
    try:
        value = float(raw)
    except (TypeError, ValueError, OverflowError):
        return None, ValueErrorKind.NOT_NUMERIC
    if not math.isfinite(value):
        return None, ValueErrorKind.NOT_FINITE
    if (min_value is not None and value < min_value) or (max_value is not None and value > max_value):
        return None, ValueErrorKind.OUT_OF_RANGE
    return value, None
