"""
Tests for SQLAlchemy repository utility functions.
"""
import pytest
from infrastructure.sqlalchemy.utils import normalise_metrics


class TestNormaliseMetrics:
    """Test cases for the normalise_metrics utility function."""

    def test_normalise_metrics_with_valid_data(self):
        """Test that valid metrics are normalized correctly."""
        raw_metrics = {"accuracy": 0.95, "speed": 100.5, "count": 42}
        result = normalise_metrics(raw_metrics)
        
        assert result == {"accuracy": 0.95, "speed": 100.5, "count": 42.0}
        assert all(isinstance(k, str) for k in result.keys())
        assert all(isinstance(v, float) for v in result.values())

    def test_normalise_metrics_with_none_keys(self):
        """Test that None keys are skipped."""
        raw_metrics = {"valid": 1.0, None: 2.0, "another": 3.0}
        result = normalise_metrics(raw_metrics)
        
        assert result == {"valid": 1.0, "another": 3.0}
        assert None not in result

    def test_normalise_metrics_with_invalid_values(self):
        """Test that invalid values are skipped."""
        raw_metrics = {
            "valid": 1.0,
            "invalid_str": "not a number",
            "invalid_none": None,
            "valid_int": 42,
        }
        result = normalise_metrics(raw_metrics)
        
        assert result == {"valid": 1.0, "valid_int": 42.0}
        assert "invalid_str" not in result
        assert "invalid_none" not in result

    def test_normalise_metrics_with_numeric_keys(self):
        """Test that numeric keys are converted to strings."""
        raw_metrics = {1: 10.0, 2: 20.0, "three": 30.0}
        result = normalise_metrics(raw_metrics)
        
        assert result == {"1": 10.0, "2": 20.0, "three": 30.0}
        assert all(isinstance(k, str) for k in result.keys())

    def test_normalise_metrics_with_empty_dict(self):
        """Test that an empty dictionary returns an empty dictionary."""
        result = normalise_metrics({})
        assert result == {}

    def test_normalise_metrics_with_none_input(self):
        """Test that None input returns an empty dictionary."""
        result = normalise_metrics(None)
        assert result == {}

    def test_normalise_metrics_with_string_numbers(self):
        """Test that string representations of numbers are converted."""
        raw_metrics = {"metric1": "10.5", "metric2": "20", "metric3": 30}
        result = normalise_metrics(raw_metrics)
        
        assert result == {"metric1": 10.5, "metric2": 20.0, "metric3": 30.0}
        assert all(isinstance(v, float) for v in result.values())

    def test_normalise_metrics_with_all_invalid_data(self):
        """Test that all invalid data results in an empty dictionary."""
        raw_metrics = {
            None: 1.0,
            "invalid1": "not a number",
            "invalid2": None,
            "invalid3": object(),
        }
        result = normalise_metrics(raw_metrics)
        assert result == {}

    def test_normalise_metrics_preserves_float_precision(self):
        """Test that float precision is preserved."""
        raw_metrics = {"precise": 0.123456789, "scientific": 1.23e-5}
        result = normalise_metrics(raw_metrics)
        
        assert result["precise"] == 0.123456789
        assert result["scientific"] == 1.23e-5
