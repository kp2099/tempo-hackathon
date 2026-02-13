"""
Isolation Forest-based anomaly detection for expenses.
Complements the XGBoost risk scorer by detecting statistical outliers.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
import joblib
import os
import logging

logger = logging.getLogger("TempoExpenseAI.AnomalyDetector")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
ANOMALY_MODEL_PATH = os.path.join(MODEL_DIR, "anomaly_model.pkl")

ANOMALY_FEATURES = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "monthly_expense_count",
    "monthly_total_amount",
    "amount_vs_avg_ratio",
    "is_round_number",
]


class AnomalyDetector:
    """Isolation Forest-based anomaly detector for expense data."""

    def __init__(self):
        self.model = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        """Load trained model from disk if available."""
        if os.path.exists(ANOMALY_MODEL_PATH):
            try:
                self.model = joblib.load(ANOMALY_MODEL_PATH)
                self.is_trained = True
                logger.info("✅ Anomaly detection model loaded from disk")
            except Exception as e:
                logger.warning(f"⚠️ Could not load anomaly model: {e}")
                self.is_trained = False

    def extract_features(self, expense_data: dict) -> np.ndarray:
        """Extract feature vector for anomaly detection."""
        features = []
        for col in ANOMALY_FEATURES:
            val = expense_data.get(col, 0)
            if isinstance(val, bool):
                val = int(val)
            features.append(float(val))
        return np.array(features).reshape(1, -1)

    def _heuristic_anomaly_score(self, expense_data: dict) -> float:
        """Fallback heuristic for anomaly scoring."""
        score = 0.0
        amount = expense_data.get("amount", 0)
        ratio = expense_data.get("amount_vs_avg_ratio", 1.0)
        hour = expense_data.get("hour_of_day", 12)

        # Statistical outlier signals
        if ratio > 4:
            score += 0.4
        elif ratio > 2.5:
            score += 0.2

        if amount > 2000:
            score += 0.3
        elif amount > 1000:
            score += 0.15

        if hour < 5 or hour > 23:
            score += 0.2

        return min(score, 1.0)

    def detect(self, expense_data: dict) -> dict:
        """
        Detect if an expense is anomalous.

        Returns:
            dict with anomaly_score (0-1), is_anomaly (bool), and details
        """
        if self.is_trained and self.model is not None:
            features = self.extract_features(expense_data)
            try:
                # Isolation Forest: -1 = anomaly, 1 = normal
                prediction = self.model.predict(features)[0]
                # decision_function: lower = more anomalous
                raw_score = self.model.decision_function(features)[0]
                # Normalize to 0-1 where 1 = most anomalous
                anomaly_score = max(0, min(1, 0.5 - raw_score))
                is_anomaly = prediction == -1
            except Exception as e:
                logger.warning(f"Anomaly detection failed, using heuristic: {e}")
                anomaly_score = self._heuristic_anomaly_score(expense_data)
                is_anomaly = anomaly_score > 0.5
        else:
            anomaly_score = self._heuristic_anomaly_score(expense_data)
            is_anomaly = anomaly_score > 0.5

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": is_anomaly,
            "model_used": "isolation_forest" if self.is_trained else "heuristic",
        }


# Singleton
_anomaly_detector = None


def get_anomaly_detector() -> AnomalyDetector:
    """Get or create the singleton anomaly detector instance."""
    global _anomaly_detector
    if _anomaly_detector is None:
        _anomaly_detector = AnomalyDetector()
    return _anomaly_detector

