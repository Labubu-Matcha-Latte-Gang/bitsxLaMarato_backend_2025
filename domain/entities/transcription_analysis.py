from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class TranscriptionAnalysis:
    """
    Domain representation of a cognitive analysis session derived from voice
    transcriptions. Each instance captures aggregated metrics from a
    transcription session linked to a patient. Metrics may include
    processing speed (e.g., ``raw_latency``), lexical access (e.g.,
    ``idea_density``), phonation ratios and other cognitive proxies.

    Attributes:
        patient_email (str): Unique identifier of the patient associated
            with this analysis.
        metrics (Dict[str, float]): Dictionary of analysis metrics keyed by
            metric name. Values are floats and should be normalised or
            comparable across sessions.
        created_at (datetime): When the analysis was recorded. Should be
            timezone aware.
    """

    patient_email: str
    metrics: Dict[str, float]
    created_at: datetime

    def to_dict(self) -> dict:
        """
        Serialize the analysis for API responses or logging. The returned
        dictionary contains the patient identifier, a shallow copy of the
        metrics and an ISO8601 timestamp.
        """
        return {
            "patient_email": self.patient_email,
            "metrics": dict(self.metrics),
            "created_at": self.created_at.isoformat(),
        }
