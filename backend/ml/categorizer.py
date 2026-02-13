"""
ML-based expense categorization.
Predicts the category of an expense based on its features.
"""

import numpy as np
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
import logging

logger = logging.getLogger("TempoExpenseAI.Categorizer")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
CATEGORIZER_PATH = os.path.join(MODEL_DIR, "categorizer_model.pkl")
ENCODER_PATH = os.path.join(MODEL_DIR, "category_encoder.pkl")

CATEGORIES = [
    "meals", "travel", "accommodation", "office_supplies",
    "software", "equipment", "training", "client_entertainment",
    "transportation", "miscellaneous"
]

# Amount-based heuristic ranges for fallback
CATEGORY_AMOUNT_HINTS = {
    (0, 80): ["meals", "transportation"],
    (80, 200): ["office_supplies", "meals", "miscellaneous"],
    (150, 500): ["software", "training", "accommodation"],
    (200, 900): ["travel", "accommodation", "equipment"],
    (500, 5000): ["equipment", "travel"],
}


class ExpenseCategorizer:
    """ML-based expense category prediction."""

    def __init__(self):
        self.model = None
        self.encoder = None
        self.is_trained = False
        self._load_model()

    def _load_model(self):
        if os.path.exists(CATEGORIZER_PATH) and os.path.exists(ENCODER_PATH):
            try:
                self.model = joblib.load(CATEGORIZER_PATH)
                self.encoder = joblib.load(ENCODER_PATH)
                self.is_trained = True
                logger.info("✅ Categorizer model loaded from disk")
            except Exception as e:
                logger.warning(f"⚠️ Could not load categorizer: {e}")

    def predict_category(self, expense_data: dict) -> dict:
        """Predict the most likely category for an expense."""
        if self.is_trained and self.model is not None:
            features = np.array([
                expense_data.get("amount", 0),
                expense_data.get("hour_of_day", 12),
                expense_data.get("day_of_week", 1),
                expense_data.get("is_weekend", 0),
                expense_data.get("description_length", 20),
            ]).reshape(1, -1)

            try:
                pred_idx = self.model.predict(features)[0]
                predicted = self.encoder.inverse_transform([pred_idx])[0]
                probas = self.model.predict_proba(features)[0]
                confidence = float(max(probas))

                return {
                    "predicted_category": predicted,
                    "confidence": round(confidence, 3),
                    "model_used": "random_forest",
                }
            except Exception as e:
                logger.warning(f"Categorization failed: {e}")

        # Heuristic fallback
        return self._heuristic_categorize(expense_data)

    def _heuristic_categorize(self, expense_data: dict) -> dict:
        """Simple heuristic categorization based on amount and description."""
        amount = expense_data.get("amount", 0)
        description = expense_data.get("description", "").lower()

        # Keyword matching
        keyword_map = {
            "meals": ["lunch", "dinner", "breakfast", "food", "restaurant", "coffee", "chipotle", "starbucks"],
            "travel": ["flight", "airline", "plane", "travel", "delta", "united", "southwest"],
            "accommodation": ["hotel", "marriott", "hilton", "airbnb", "lodging", "inn"],
            "transportation": ["uber", "lyft", "taxi", "cab", "parking", "gas", "fuel"],
            "office_supplies": ["staples", "office", "paper", "pen", "supplies"],
            "software": ["adobe", "slack", "zoom", "subscription", "saas", "cloud", "aws"],
            "equipment": ["laptop", "monitor", "keyboard", "mouse", "computer", "apple", "dell"],
            "training": ["course", "training", "conference", "workshop", "udemy", "coursera"],
            "client_entertainment": ["client", "entertainment", "event", "dinner meeting"],
        }

        for cat, keywords in keyword_map.items():
            if any(kw in description for kw in keywords):
                return {
                    "predicted_category": cat,
                    "confidence": 0.7,
                    "model_used": "heuristic_keyword",
                }

        # Amount-based fallback
        for (low, high), cats in CATEGORY_AMOUNT_HINTS.items():
            if low <= amount <= high:
                return {
                    "predicted_category": cats[0],
                    "confidence": 0.4,
                    "model_used": "heuristic_amount",
                }

        return {
            "predicted_category": "miscellaneous",
            "confidence": 0.2,
            "model_used": "heuristic_default",
        }


# Singleton
_categorizer = None


def get_categorizer() -> ExpenseCategorizer:
    global _categorizer
    if _categorizer is None:
        _categorizer = ExpenseCategorizer()
    return _categorizer

