"""
Anomaly Detector — Thin wrapper around the ensemble's Isolation Forest.

The Isolation Forest is now managed by the RiskScorer ensemble as Layer 2.
This module exists for backward compatibility with the approval engine
and provides the same detect() interface.
"""

import logging
from ml.risk_scorer import get_risk_scorer

logger = logging.getLogger("TempoExpenseAI.AnomalyDetector")


class AnomalyDetector:
    """
    Anomaly detection via the ensemble's Isolation Forest layer.

    The actual model lives inside RiskScorer (Layer 2).  This wrapper
    delegates to it so the approval engine API stays unchanged.
    """

    def __init__(self):
        self._scorer = None

    @property
    def scorer(self):
        if self._scorer is None:
            self._scorer = get_risk_scorer()
        return self._scorer

    def detect(self, expense_data: dict) -> dict:
        """
        Detect if an expense is anomalous.

        Returns:
            dict with anomaly_score (0-1), is_anomaly (bool), model_used
        """
        anomaly_score = self.scorer._isolation_score(expense_data)
        is_anomaly = anomaly_score > 0.5

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": is_anomaly,
            "model_used": (
                "isolation_forest" if self.scorer.iforest_loaded
                else "heuristic"
            ),
        }


# Singleton
_anomaly_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create the singleton anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector
