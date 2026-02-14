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
        """
        Predict the most likely category for an expense.

        Strategy: Keywords in the description are the strongest signal
        (e.g. "flight" → travel, "lunch" → meals).  If keyword matching
        succeeds with high confidence, use it directly.  Otherwise, blend
        with the RF model's numeric-feature prediction.
        """
        # Step 1: Always try keyword matching first — descriptions are
        # the most informative signal for category.
        keyword_result = self._keyword_categorize(expense_data)

        # Step 2: If we have a trained RF model, get its prediction too.
        rf_result = None
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
                rf_result = {
                    "predicted_category": predicted,
                    "confidence": round(confidence, 3),
                    "model_used": "random_forest",
                }
            except Exception as e:
                logger.warning(f"Categorization failed: {e}")

        # Step 3: Decide which result to use.
        # Keywords win if they matched anything, because the RF model
        # has no access to the text and often miscategorizes.
        if keyword_result is not None:
            return keyword_result

        # RF model as fallback when no keywords matched
        if rf_result is not None:
            return rf_result

        # Last resort: amount-based heuristic
        return self._amount_heuristic(expense_data)

    # Keyword map — order matters (more specific first)
    KEYWORD_MAP = {
        "accommodation": ["hotel", "marriott", "hilton", "airbnb", "lodging", "inn", "motel", "resort"],
        "travel": ["flight", "airline", "plane", "travel", "delta", "united", "southwest", "jetblue", "american airlines"],
        "transportation": ["uber", "lyft", "taxi", "cab", "parking", "gas", "fuel", "metro", "subway", "train", "bus", "toll"],
        "meals": ["lunch", "dinner", "breakfast", "food", "restaurant", "coffee", "chipotle", "starbucks", "meal", "cafeteria", "catering"],
        "software": ["adobe", "slack", "zoom", "subscription", "saas", "cloud", "aws", "azure", "github", "jira", "license", "hosting"],
        "equipment": ["laptop", "monitor", "keyboard", "mouse", "computer", "apple", "dell", "server", "printer", "hardware", "macbook"],
        "training": ["course", "training", "conference", "workshop", "udemy", "coursera", "seminar", "certification", "registration"],
        "office_supplies": ["staples", "office", "paper", "pen", "supplies", "toner", "ink", "binder", "notepad"],
        "client_entertainment": ["client dinner", "client meeting", "client entertainment", "client event", "business dinner", "networking"],
    }

    def _keyword_categorize(self, expense_data: dict) -> dict | None:
        """
        Categorize based on keywords in the description.
        Returns None if no keywords match.
        """
        description = (expense_data.get("description", "") or "").lower()
        if not description.strip():
            return None

        for cat, keywords in self.KEYWORD_MAP.items():
            if any(kw in description for kw in keywords):
                return {
                    "predicted_category": cat,
                    "confidence": 0.85,
                    "model_used": "keyword_match",
                }
        return None

    def _amount_heuristic(self, expense_data: dict) -> dict:
        """Amount-based fallback when no keywords and no trained model."""
        amount = expense_data.get("amount", 0)
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

    def _heuristic_categorize(self, expense_data: dict) -> dict:
        """Legacy fallback: keyword first, then amount."""
        result = self._keyword_categorize(expense_data)
        if result is not None:
            return result
        return self._amount_heuristic(expense_data)


# Singleton
_categorizer = None


def get_categorizer() -> ExpenseCategorizer:
    global _categorizer
    if _categorizer is None:
        _categorizer = ExpenseCategorizer()
    return _categorizer

