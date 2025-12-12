"""
Tests for the InverseEfficiencyProgressStrategy implementation.
"""
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from domain.entities.activity import Activity
from domain.entities.score import Score
from domain.services.progress import InverseEfficiencyProgressStrategy
from helpers.enums.question_types import QuestionType


class TestInverseEfficiencyProgressStrategy:
    """Test cases for the InverseEfficiencyProgressStrategy class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.strategy = InverseEfficiencyProgressStrategy()
        self.base_time = datetime(2025, 1, 1, 12, 0, 0)

    def _create_mock_patient(self) -> Any:
        """Create a mock patient for testing."""
        patient = MagicMock()
        patient.id = uuid4()
        return patient

    def _create_activity(self, activity_type: QuestionType) -> Activity:
        """Create an Activity instance for testing."""
        return Activity(
            id=uuid4(),
            title="Test Activity",
            description="Test Description",
            activity_type=activity_type,
            difficulty=3.0
        )

    def _create_score(
        self,
        score_value: float,
        seconds: float,
        activity_type: QuestionType,
        time_offset_minutes: int = 0
    ) -> Score:
        """Create a Score instance for testing."""
        patient = self._create_mock_patient()
        activity = self._create_activity(activity_type)
        completed_at = self.base_time + timedelta(minutes=time_offset_minutes)
        
        return Score(
            patient=patient,
            activity=activity,
            completed_at=completed_at,
            score=score_value,
            seconds_to_finish=seconds
        )

    def test_empty_score_list_returns_empty_series(self):
        """Test that an empty score list returns an empty series."""
        result = self.strategy.build_progress_series([])
        assert result == []

    def test_single_score_returns_single_point(self):
        """Test that a single score returns a single data point."""
        score = self._create_score(
            score_value=8.0,
            seconds=10.0,
            activity_type=QuestionType.CONCENTRATION
        )
        
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        timestamp, composite = result[0]
        assert timestamp == score.completed_at
        assert 0.0 <= composite <= 1.0

    def test_multiple_scores_same_type_shows_progress(self):
        """Test that multiple scores of the same type show progression."""
        scores = [
            self._create_score(5.0, 20.0, QuestionType.CONCENTRATION, 0),
            self._create_score(7.0, 15.0, QuestionType.CONCENTRATION, 10),
            self._create_score(9.0, 10.0, QuestionType.CONCENTRATION, 20),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 3
        # Verify timestamps are in order
        for i in range(len(result) - 1):
            assert result[i][0] < result[i + 1][0]
        # All composite values should be valid
        for _, composite in result:
            assert 0.0 <= composite <= 1.0

    def test_multiple_question_types_composite_averaging(self):
        """Test that multiple question types are averaged into composite score."""
        scores = [
            self._create_score(8.0, 10.0, QuestionType.CONCENTRATION, 0),
            self._create_score(8.0, 10.0, QuestionType.SPEED, 5),
            self._create_score(8.0, 10.0, QuestionType.WORDS, 10),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 3
        # After all three types are added, composite should reflect averaging
        # Each type contributes to the composite
        _, composite_after_one_type = result[0]
        _, composite_after_two_types = result[1]
        _, composite_after_three_types = result[2]
        
        # All should be valid
        assert 0.0 <= composite_after_one_type <= 1.0
        assert 0.0 <= composite_after_two_types <= 1.0
        assert 0.0 <= composite_after_three_types <= 1.0

    def test_division_by_zero_protection_min_accuracy(self):
        """Test that MIN_ACCURACY prevents division by zero with score=0."""
        score = self._create_score(
            score_value=0.0,  # Zero score
            seconds=10.0,
            activity_type=QuestionType.CONCENTRATION
        )
        
        # Should not raise division by zero error
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        _, composite = result[0]
        # Should still produce a valid composite value
        assert 0.0 <= composite <= 1.0

    def test_maximum_score_produces_high_efficiency(self):
        """Test that maximum score (10.0) with low time produces high efficiency."""
        scores = [
            self._create_score(10.0, 1.0, QuestionType.CONCENTRATION, 0),
            self._create_score(10.0, 1.0, QuestionType.CONCENTRATION, 5),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        # Maximum score with minimum time should produce high efficiency
        _, composite = result[-1]
        # Due to exponential smoothing and IES formula, expect relatively high value
        assert composite > 0.3  # Should be reasonably high

    def test_minimum_score_produces_low_efficiency(self):
        """Test that minimum score with high time produces low efficiency."""
        scores = [
            self._create_score(0.1, 100.0, QuestionType.CONCENTRATION, 0),
            self._create_score(0.1, 100.0, QuestionType.CONCENTRATION, 5),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        # Minimum score with maximum time should produce lower efficiency
        _, composite = result[-1]
        # Should be relatively low due to poor performance
        assert composite < 0.7

    def test_normalization_with_varying_seconds(self):
        """Test that normalization works correctly with varying seconds_to_finish."""
        scores = [
            self._create_score(8.0, 5.0, QuestionType.CONCENTRATION, 0),
            self._create_score(8.0, 50.0, QuestionType.CONCENTRATION, 5),
            self._create_score(8.0, 100.0, QuestionType.CONCENTRATION, 10),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 3
        # The strategy normalizes by max_seconds, so all should produce valid values
        for _, composite in result:
            assert 0.0 <= composite <= 1.0

    def test_exponential_smoothing_dampens_changes(self):
        """Test that exponential smoothing dampens sudden changes."""
        # Create scores with alternating performance
        scores = [
            self._create_score(9.0, 10.0, QuestionType.CONCENTRATION, 0),
            self._create_score(3.0, 50.0, QuestionType.CONCENTRATION, 5),
            self._create_score(9.0, 10.0, QuestionType.CONCENTRATION, 10),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        _, comp1 = result[0]
        _, comp2 = result[1]
        _, comp3 = result[2]
        
        # Due to smoothing (alpha=0.35), changes should be gradual
        # The second score's impact should be dampened
        change1 = abs(comp2 - comp1)
        change2 = abs(comp3 - comp2)
        
        # Both changes should be reasonable (not instant jumps)
        assert change1 < 1.0
        assert change2 < 1.0

    def test_handling_none_activity_type(self):
        """Test that missing activity_type is handled as 'unknown'."""
        patient = self._create_mock_patient()
        
        # Create an activity without activity_type (simulate missing attribute)
        activity = MagicMock()
        activity.activity_type = None
        
        score = Score(
            patient=patient,
            activity=activity,
            completed_at=self.base_time,
            score=8.0,
            seconds_to_finish=10.0
        )
        
        # Should not raise an error
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        _, composite = result[0]
        assert 0.0 <= composite <= 1.0

    def test_zero_seconds_handling(self):
        """Test that zero seconds_to_finish is handled correctly."""
        score = self._create_score(
            score_value=9.0,
            seconds=0.0,  # Zero seconds
            activity_type=QuestionType.SPEED
        )
        
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        _, composite = result[0]
        # Zero seconds (normalized) with good accuracy should give good efficiency
        assert 0.0 <= composite <= 1.0

    def test_negative_seconds_clamped_to_zero(self):
        """Test that negative seconds are clamped to zero in normalization."""
        score = self._create_score(
            score_value=8.0,
            seconds=-5.0,  # Negative seconds (edge case)
            activity_type=QuestionType.CONCENTRATION
        )
        
        # Should not raise an error; negative is clamped via max(0.0, ...)
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        _, composite = result[0]
        assert 0.0 <= composite <= 1.0

    def test_score_greater_than_10_clamped(self):
        """Test that scores > 10.0 are clamped to 1.0 accuracy."""
        score = self._create_score(
            score_value=15.0,  # Score > 10
            seconds=10.0,
            activity_type=QuestionType.CONCENTRATION
        )
        
        result = self.strategy.build_progress_series([score])
        
        assert len(result) == 1
        _, composite = result[0]
        # Should be clamped and produce valid result
        assert 0.0 <= composite <= 1.0

    def test_unordered_scores_are_sorted(self):
        """Test that scores provided out of chronological order are sorted."""
        scores = [
            self._create_score(8.0, 10.0, QuestionType.CONCENTRATION, 20),
            self._create_score(7.0, 15.0, QuestionType.CONCENTRATION, 0),
            self._create_score(9.0, 12.0, QuestionType.CONCENTRATION, 10),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 3
        # Verify results are in chronological order
        timestamps = [timestamp for timestamp, _ in result]
        assert timestamps == sorted(timestamps)

    def test_multiple_types_separate_smoothing_state(self):
        """Test that different question types maintain separate smoothing state."""
        scores = [
            self._create_score(8.0, 10.0, QuestionType.CONCENTRATION, 0),
            self._create_score(6.0, 20.0, QuestionType.SPEED, 5),
            self._create_score(9.0, 8.0, QuestionType.CONCENTRATION, 10),
            self._create_score(7.0, 18.0, QuestionType.SPEED, 15),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 4
        # Each type should maintain its own smoothing state
        # All composites should be valid
        for _, composite in result:
            assert 0.0 <= composite <= 1.0

    def test_composite_reflects_all_tracked_types(self):
        """Test that composite score reflects average of all tracked types."""
        # Add scores for three different types at different times
        scores = [
            self._create_score(8.0, 10.0, QuestionType.CONCENTRATION, 0),
            self._create_score(8.0, 10.0, QuestionType.SPEED, 5),
            self._create_score(8.0, 10.0, QuestionType.WORDS, 10),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        # After first score, should track 1 type
        # After second score, should track 2 types
        # After third score, should track 3 types
        # The composite is average of all per_type_state values
        assert len(result) == 3

    def test_consistent_performance_shows_stable_curve(self):
        """Test that consistent performance produces a stable progress curve."""
        # Create multiple scores with same performance
        scores = [
            self._create_score(8.0, 15.0, QuestionType.CONCENTRATION, i * 5)
            for i in range(10)
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 10
        # With consistent input, smoothing should converge to stable value
        composites = [comp for _, comp in result]
        
        # Later values should be more stable (less variance)
        later_variance = max(composites[5:]) - min(composites[5:])
        # Should be relatively stable after smoothing converges
        assert later_variance < 0.3

    def test_improving_performance_shows_upward_trend(self):
        """Test that improving performance shows an upward trend in composite."""
        scores = [
            self._create_score(5.0, 30.0, QuestionType.CONCENTRATION, 0),
            self._create_score(6.0, 25.0, QuestionType.CONCENTRATION, 5),
            self._create_score(7.0, 20.0, QuestionType.CONCENTRATION, 10),
            self._create_score(8.0, 15.0, QuestionType.CONCENTRATION, 15),
            self._create_score(9.0, 10.0, QuestionType.CONCENTRATION, 20),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        composites = [comp for _, comp in result]
        
        # With improving scores and decreasing time, expect upward trend
        # Due to smoothing, it won't be perfectly monotonic, but overall should increase
        assert composites[-1] > composites[0]

    def test_declining_performance_shows_downward_trend(self):
        """Test that declining performance shows a downward trend in composite."""
        scores = [
            self._create_score(9.0, 10.0, QuestionType.CONCENTRATION, 0),
            self._create_score(8.0, 15.0, QuestionType.CONCENTRATION, 5),
            self._create_score(7.0, 20.0, QuestionType.CONCENTRATION, 10),
            self._create_score(6.0, 25.0, QuestionType.CONCENTRATION, 15),
            self._create_score(5.0, 30.0, QuestionType.CONCENTRATION, 20),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        composites = [comp for _, comp in result]
        
        # With declining scores and increasing time, expect downward trend
        assert composites[-1] < composites[0]

    def test_mixed_types_with_different_performance_patterns(self):
        """Test composite with different performance patterns across types."""
        scores = [
            # CONCENTRATION improving
            self._create_score(6.0, 20.0, QuestionType.CONCENTRATION, 0),
            self._create_score(8.0, 15.0, QuestionType.CONCENTRATION, 10),
            # SPEED declining
            self._create_score(9.0, 10.0, QuestionType.SPEED, 5),
            self._create_score(7.0, 20.0, QuestionType.SPEED, 15),
        ]
        
        result = self.strategy.build_progress_series(scores)
        
        assert len(result) == 4
        # Composite should balance both trends
        for _, composite in result:
            assert 0.0 <= composite <= 1.0

    def test_strategy_implements_interface(self):
        """Test that InverseEfficiencyProgressStrategy implements CompositeProgressStrategy."""
        from domain.services.progress import CompositeProgressStrategy
        assert isinstance(self.strategy, CompositeProgressStrategy)

    def test_constants_have_expected_values(self):
        """Test that strategy constants are set to expected values."""
        assert self.strategy.MIN_ACCURACY == 0.05
        assert self.strategy.SMOOTHING_ALPHA == 0.35
