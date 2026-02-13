"""
XGBoost-based expense risk scoring model.
Predicts the probability that an expense is fraudulent or anomalous.
"""

import numpy as np
import xgboost as xgb
import joblib
import os
import logging

logger = logging.getLogger("TempoExpenseAI.RiskScorer")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "risk_model.json")
SCALER_PATH = os.path.join(MODEL_DIR, "risk_scaler.pkl")

# Feature columns used by the model (order matters!)
FEATURE_COLUMNS = [
    "amount",
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "days_since_last_expense",
    "monthly_expense_count",
    "monthly_total_amount",
    "amount_vs_avg_ratio",
    "category_frequency",
    "merchant_frequency",
    "is_round_number",
    "receipt_attached",
    "description_length",
]


class RiskScorer:
    """XGBoost-based expense risk scoring engine."""

    def __init__(self):
        self.model = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        """Load trained model from disk if available."""
        if os.path.exists(MODEL_PATH):
            try:
                self.model = xgb.XGBClassifier()
                self.model.load_model(MODEL_PATH)
                self.is_trained = True
                logger.info("✅ Risk scoring model loaded from disk")
            except Exception as e:
                logger.warning(f"⚠️ Could not load risk model: {e}")
                self.model = None
                self.is_trained = False
        else:
            logger.info("ℹ️ No trained risk model found — will use heuristic scoring")

    def extract_features(self, expense_data: dict) -> np.ndarray:
        """Extract feature vector from expense data."""
        features = []
        for col in FEATURE_COLUMNS:
            val = expense_data.get(col, 0)
            # Convert booleans to int
            if isinstance(val, bool):
                val = int(val)
            features.append(float(val))
        return np.array(features).reshape(1, -1)

    def _heuristic_score(self, expense_data: dict) -> float:
        """Fallback heuristic scoring when model isn't trained."""
        score = 0.1  # base score

        amount = expense_data.get("amount", 0)
        hour = expense_data.get("hour_of_day", 12)
        is_weekend = expense_data.get("is_weekend", 0)
        receipt = expense_data.get("receipt_attached", True)
        ratio = expense_data.get("amount_vs_avg_ratio", 1.0)
        is_round = expense_data.get("is_round_number", 0)

        # High amount
        if amount > 1000:
            score += 0.2
        elif amount > 500:
            score += 0.1

        # Unusual hours
        if hour < 6 or hour > 22:
            score += 0.15

        # Weekend
        if is_weekend:
            score += 0.1

        # No receipt on high amount
        if not receipt and amount > 50:
            score += 0.2

        # Amount much higher than average
        if ratio > 3:
            score += 0.2
        elif ratio > 2:
            score += 0.1

        # Round number pattern
        if is_round and amount > 100:
            score += 0.1

        return min(score, 1.0)

    def predict_risk(self, expense_data: dict) -> dict:
        """
        Predict risk score for an expense.

        Returns:
            dict with risk_score (0-1), risk_level, and risk_factors
        """
        risk_factors = []

        if self.is_trained and self.model is not None:
            features = self.extract_features(expense_data)
            try:
                risk_score = float(self.model.predict_proba(features)[0][1])
            except Exception as e:
                logger.warning(f"Model prediction failed, using heuristic: {e}")
                risk_score = self._heuristic_score(expense_data)
        else:
            risk_score = self._heuristic_score(expense_data)

        # Identify risk factors
        amount = expense_data.get("amount", 0)
        hour = expense_data.get("hour_of_day", 12)
        is_weekend = expense_data.get("is_weekend", 0)
        receipt = expense_data.get("receipt_attached", True)
        ratio = expense_data.get("amount_vs_avg_ratio", 1.0)

        if amount > 1000:
            risk_factors.append(f"High amount: ${amount:.2f}")
        if hour < 6 or hour > 22:
            risk_factors.append(f"Unusual submission time: {hour}:00")
        if is_weekend:
            risk_factors.append("Weekend submission")
        if not receipt and amount > 50:
            risk_factors.append(f"No receipt for ${amount:.2f} expense")
        if ratio > 2:
            risk_factors.append(f"Amount {ratio:.1f}x above employee average")

        # Determine risk level
        if risk_score < 0.3:
            risk_level = "low"
        elif risk_score < 0.7:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "risk_score": round(risk_score, 4),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "model_used": "xgboost" if self.is_trained else "heuristic",
        }


# Singleton instance
_risk_scorer = None


def get_risk_scorer() -> RiskScorer:
    """Get or create the singleton risk scorer instance."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer

