"""Normalization helpers for numeric and qualitative lab results."""

import math
import re
from typing import Optional, Union


TestValue = Union[float, str]


def normalize_test_value(value) -> Optional[TestValue]:
    """Return numeric values as floats and normalize common binary result labels."""
    if value is None or isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        number = float(value)
        return number if math.isfinite(number) else None

    text = str(value).strip()
    if not text:
        return None

    try:
        number = float(text)
        return number if math.isfinite(number) else None
    except ValueError:
        pass

    key = re.sub(r"[^a-z]", "", text.casefold())
    negative_values = {
        "negative", "neg", "nonreactive", "notdetected", "undetected",
        "absent", "notpresent",
    }
    positive_values = {
        "positive", "pos", "reactive", "detected", "present",
    }
    if key in negative_values:
        return "Negative"
    if key in positive_values:
        return "Positive"

    return text


def qualitative_polarity(value) -> Optional[str]:
    """Return Positive/Negative for recognized qualitative result values."""
    normalized = normalize_test_value(value)
    if not isinstance(normalized, str):
        return None

    key = re.sub(r"[^a-z]", "", normalized.casefold())
    if key in {
        "negative", "neg", "nonreactive", "notdetected", "undetected",
        "absent", "notpresent",
    }:
        return "Negative"
    if key in {"positive", "pos", "reactive", "detected", "present"}:
        return "Positive"
    return None


def classify_test_result(value, good_result=None, min_value=None, max_value=None) -> str:
    """Classify a result as good, bad, or unknown without guessing result polarity."""
    normalized = normalize_test_value(value)
    if isinstance(normalized, (int, float)):
        try:
            low, high = float(min_value), float(max_value)
        except (TypeError, ValueError):
            return "unknown"
        if not math.isfinite(low) or not math.isfinite(high) or low > high:
            return "unknown"
        return "good" if low <= normalized <= high else "bad"

    expected = qualitative_polarity(good_result)
    observed = qualitative_polarity(normalized)
    if expected and observed:
        return "good" if expected == observed else "bad"
    return "unknown"


def test_value_key(value):
    """Build a stable comparison key for duplicate detection."""
    normalized = normalize_test_value(value)
    if isinstance(normalized, (int, float)):
        return ("number", float(normalized))
    if isinstance(normalized, str):
        polarity = qualitative_polarity(normalized)
        return ("qualitative", polarity) if polarity else ("text", normalized.casefold())
    return ("empty", None)
