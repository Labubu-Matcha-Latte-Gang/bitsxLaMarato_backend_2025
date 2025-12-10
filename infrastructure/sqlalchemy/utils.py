"""
Shared utilities for SQLAlchemy repositories.
"""
from typing import Any, Dict, Optional


def normalise_metrics(raw_metrics: Optional[Dict[Any, Any]]) -> Dict[str, float]:
    """
    Normalize a dictionary of metrics by ensuring all keys are strings
    and all values are floats. Invalid entries are skipped.

    Args:
        raw_metrics: Dictionary with metric names as keys and values as floats.
                     Can be None or contain None keys/invalid values.

    Returns:
        A cleaned dictionary with string keys and float values.
        None keys and values that cannot be converted to float are excluded.
    """
    if raw_metrics is None:
        return {}
    
    normalised: Dict[str, float] = {}
    for key, value in raw_metrics.items():
        if key is None:
            continue
        try:
            normalised[str(key)] = float(value)
        except (TypeError, ValueError):
            continue
    return normalised
