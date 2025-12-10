"""
Strategy interface for normalising metrics dictionaries.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IMetricsNormaliserStrategy(ABC):
    """
    Interface for strategies that normalise metrics dictionaries.
    
    Implementors of this interface provide different strategies for
    normalising raw metrics data into a consistent format with string
    keys and float values.
    """

    @abstractmethod
    def normalise(self, raw_metrics: Optional[Dict[Any, Any]]) -> Dict[str, float]:
        """
        Normalise a dictionary of metrics by ensuring all keys are strings
        and all values are floats. Invalid entries are skipped.

        Args:
            raw_metrics: Dictionary with metric names as keys and values.
                         Can be None or contain None keys/invalid values.

        Returns:
            A cleaned dictionary with string keys and float values.
            None keys and values that cannot be converted to float are excluded.
        """
        raise NotImplementedError()
