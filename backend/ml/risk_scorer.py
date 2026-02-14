"""
Three-Layer Ensemble Risk Scorer
=================================

Combines three independent scoring layers into a single calibrated
fraud probability:

  Layer 1 — Distilled XGBoost (0.15 weight)
    Trained on 284,807 real credit card transactions via knowledge
    distillation.  17 features derived from Amount + Time.  Low weight
    because the Kaggle fraud signals live in PCA features, not
    amount/time — this layer is a minor supplementary signal.

  Layer 2 — Isolation Forest (0.35 weight)
    Unsupervised anomaly detector.  Trained on Kaggle legit
    transactions; re-trains on real expenses as they accumulate.
    Primary ML signal for spending-pattern anomalies.

  Layer 3 — Policy Engine (0.50 weight)
    Transparent, rule-based domain scorer.  Category norms, receipt
    logic, budget utilization.  No ML — 100% explainable.
    Highest weight because domain rules are the most reliable signal
    for real-world expense fraud detection.

Final score = w1·distilled + w2·isolation + w3·policy
"""

import os
import math
import logging
import numpy as np
import xgboost as xgb
from sklearn.ensemble import IsolationForest
import joblib

from ml.feature_engineering import (
    engineer_kaggle_features_single,
    compute_policy_features,
    set_amount_stats,
    KAGGLE_FEATURE_NAMES,
    CATEGORY_AMOUNT_NORMS,
    HIGH_RISK_CATEGORIES,
)

logger = logging.getLogger("TempoExpenseAI.RiskScorer")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
STUDENT_PATH = os.path.join(MODEL_DIR, "student_risk_model.json")
IFOREST_PATH = os.path.join(MODEL_DIR, "isolation_forest.pkl")
STATS_PATH = os.path.join(MODEL_DIR, "amount_stats.pkl")

# Ensemble weights
# NOTE: The distilled XGBoost was trained on Kaggle PCA features (V1-V28) via
# knowledge distillation to 17 amount/time features.  Since fraud signals in
# that dataset live almost entirely in the PCA space, the student produces
# near-zero scores for all inputs.  We keep it as a minor signal but rely
# primarily on the Isolation Forest (learned spending patterns) and the
# Policy Engine (transparent domain rules) for real expense risk.
W_DISTILLED = 0.15
W_ISOLATION = 0.35
W_POLICY = 0.50


class RiskScorer:
    """
    Three-layer ensemble risk scorer.

    Each layer produces a score in [0, 1].  The final risk score is the
    weighted average, clipped to [0, 1].
    """

    def __init__(self):
        self.student_model = None
        self.iforest_model = None
        self.student_loaded = False
        self.iforest_loaded = False
        self._iforest_offset = 0.0
        self._iforest_scale = 1.0
        self._load_models()

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_models(self):
        """Load distilled student and Isolation Forest from disk."""
        # Amount stats (needed for feature engineering)
        if os.path.exists(STATS_PATH):
            stats = joblib.load(STATS_PATH)
            set_amount_stats(stats["mean"], stats["std"])

        # Student (distilled XGBoost regressor — load as raw Booster)
        if os.path.exists(STUDENT_PATH):
            try:
                self.student_model = xgb.Booster()
                self.student_model.load_model(STUDENT_PATH)
                self.student_loaded = True
                logger.info(
                    "✅ Distilled student model loaded "
                    "(trained on 284K real transactions)"
                )
            except Exception as e:
                logger.warning(f"⚠️ Could not load student model: {e}")
        else:
            logger.info("ℹ️ No student model — will use heuristic scoring")

        # Isolation Forest
        if os.path.exists(IFOREST_PATH):
            try:
                self.iforest_model = joblib.load(IFOREST_PATH)
                self.iforest_loaded = True
                # Calibrate IF normalization using the model's offset
                self._calibrate_iforest()
                logger.info("✅ Isolation Forest loaded")
            except Exception as e:
                logger.warning(f"⚠️ Could not load Isolation Forest: {e}")
        else:
            logger.info("ℹ️ No Isolation Forest model found")

    def _calibrate_iforest(self):
        """
        Calibrate IF normalization using the model's offset_ attribute.
        The offset_ is the threshold that separates inliers from outliers.
        We use it to center our normalization so normal data → score ≈ 0.
        """
        if self.iforest_model is not None and hasattr(self.iforest_model, 'offset_'):
            self._iforest_offset = self.iforest_model.offset_
            # Scale factor: we want the typical inlier range [-0.1, 0.2]
            # to map to [0, ~0.15] and outliers (< -0.2) to map to >0.5
            self._iforest_scale = 5.0  # Tuned for our data
            logger.info(f"   IF calibrated: offset={self._iforest_offset:.4f}")

    # ------------------------------------------------------------------
    # Layer 1: Distilled XGBoost
    # ------------------------------------------------------------------

    def _distilled_score(self, expense_data: dict) -> float:
        """
        Predict fraud probability using the distilled student model.

        The student was trained on teacher soft labels from 284,807 real
        transactions.  It uses 17 features derivable from amount + time.
        """
        if not self.student_loaded or self.student_model is None:
            return self._heuristic_amount_score(expense_data)

        try:
            features = engineer_kaggle_features_single(expense_data)
            dmatrix = xgb.DMatrix(features, feature_names=KAGGLE_FEATURE_NAMES)
            raw = float(self.student_model.predict(dmatrix)[0])
            return max(0.0, min(1.0, raw))
        except Exception as e:
            logger.warning(f"Student prediction failed: {e}")
            return self._heuristic_amount_score(expense_data)

    def _heuristic_amount_score(self, expense_data: dict) -> float:
        """Fallback heuristic when student model isn't available."""
        score = 0.02
        amount = expense_data.get("amount", 0)
        hour = expense_data.get("hour_of_day", 12)
        is_wknd = expense_data.get("is_weekend", 0)

        if amount > 5000:
            score += 0.25
        elif amount > 2000:
            score += 0.15
        elif amount > 1000:
            score += 0.08
        if hour < 5 or hour >= 22:
            score += 0.12
        if is_wknd:
            score += 0.05
        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Layer 2: Isolation Forest
    # ------------------------------------------------------------------

    def _isolation_score(self, expense_data: dict) -> float:
        """
        Anomaly score from Isolation Forest.

        Higher = more anomalous.  Uses the 8-feature subset that the
        forest was trained on.
        """
        if not self.iforest_loaded or self.iforest_model is None:
            return self._heuristic_anomaly_score(expense_data)

        try:
            amount = float(expense_data.get("amount", 0))
            hour = float(expense_data.get("hour_of_day", 12))
            features = np.array([
                amount,
                math.log1p(amount),
                (amount - 88.35) / 250.12,  # z-score (default stats)
                math.floor(math.log10(max(amount, 0.01))),
                hour,
                math.sin(2 * math.pi * hour / 24),
                math.cos(2 * math.pi * hour / 24),
                int(hour < 5 or hour >= 22),
            ]).reshape(1, -1)

            raw = self.iforest_model.decision_function(features)[0]

            # Better normalization using sigmoid-like mapping:
            # raw > 0 means "more normal" → low anomaly score
            # raw < 0 means "more anomalous" → higher anomaly score
            # We use a sigmoid centered around 0 with a gentle slope
            # so that normal data (raw ~ 0.05-0.15) → score ~ 0.10-0.20
            # and truly anomalous data (raw < -0.1) → score > 0.50
            score = 1.0 / (1.0 + math.exp(self._iforest_scale * raw))
            return max(0.0, min(1.0, score))
        except Exception as e:
            logger.warning(f"Isolation Forest failed: {e}")
            return self._heuristic_anomaly_score(expense_data)

    def _heuristic_anomaly_score(self, expense_data: dict) -> float:
        """Fallback anomaly heuristic."""
        score = 0.0
        amount = expense_data.get("amount", 0)
        ratio = expense_data.get("amount_vs_avg_ratio", 1.0)
        hour = expense_data.get("hour_of_day", 12)

        if ratio > 5:
            score += 0.35
        elif ratio > 3:
            score += 0.15
        if amount > 5000:
            score += 0.25
        elif amount > 2000:
            score += 0.10
        if hour < 5 or hour > 23:
            score += 0.15
        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Layer 3: Policy Engine (rule-based)
    # ------------------------------------------------------------------

    def _policy_score(self, expense_data: dict) -> tuple:
        """
        Domain-specific risk scoring via transparent business rules.

        Returns (score, risk_factors) where risk_factors is a list of
        human-readable strings explaining why the score is elevated.
        """
        score = 0.0
        factors = []

        pf = compute_policy_features(expense_data)
        amount = float(expense_data.get("amount", 0))
        category = expense_data.get("category", "miscellaneous")
        receipt = bool(expense_data.get("receipt_attached", True))
        hour = float(expense_data.get("hour_of_day", 12))
        ratio = float(expense_data.get("amount_vs_avg_ratio", 1.0))

        # Category-amount deviation (only flag extreme deviations)
        if pf["category_amount_deviation"] > 3.0:
            score += 0.15
            low, high = CATEGORY_AMOUNT_NORMS.get(category, (5, 500))
            factors.append(
                f"Amount ${amount:.2f} is far above typical "
                f"${low}–${high} for {category}"
            )
        elif pf["category_amount_deviation"] > 2.0:
            score += 0.06

        # High-risk category (minor signal)
        if pf["is_high_risk_category"]:
            score += 0.04
            factors.append(f"Category '{category}' is higher-risk")

        # Receipt policy (only flag, no double-blocking)
        if pf["receipt_risk"] and amount > 200:
            score += 0.10
            factors.append(f"No receipt for ${amount:.2f} expense")

        # Budget utilization
        if pf["budget_utilization"] > 0.95:
            score += 0.12
            factors.append(
                f"Budget {pf['budget_utilization']*100:.0f}% utilized"
            )
        elif pf["budget_utilization"] > 0.8:
            score += 0.04

        # Unusual hours (minor signal)
        if hour < 5 or hour > 23:
            score += 0.06
            factors.append(f"Unusual submission time: {int(hour)}:00")

        # Amount vs personal average (only extreme cases)
        if ratio > 5:
            score += 0.12
            factors.append(f"Amount is {ratio:.1f}× above your average")
        elif ratio > 3:
            score += 0.05

        # Description quality
        if pf["description_quality"] > 0.8 and amount > 200:
            score += 0.04
            factors.append("Short/vague description for high amount")

        # ─── OCR Verification Signals ───
        if expense_data.get("ocr_success"):
            # Amount mismatch (strongest OCR fraud signal)
            amt_mismatch = float(expense_data.get("amount_mismatch", 0))
            if amt_mismatch > 0.50:
                score += 0.25
                ocr_amt = expense_data.get("ocr_amount", "?")
                factors.append(
                    f"Receipt amount (${ocr_amt}) differs from submitted "
                    f"amount (${amount:.2f}) by {amt_mismatch:.0%}"
                )
            elif amt_mismatch > 0.15:
                score += 0.12
                ocr_amt = expense_data.get("ocr_amount", "?")
                factors.append(
                    f"Receipt amount (${ocr_amt}) differs from submitted "
                    f"amount (${amount:.2f}) by {amt_mismatch:.0%}"
                )

            # Merchant mismatch
            if expense_data.get("merchant_mismatch"):
                score += 0.10
                ocr_merch = expense_data.get("ocr_merchant", "?")
                factors.append(
                    f"Receipt merchant '{ocr_merch}' doesn't match "
                    f"submitted merchant"
                )

            # Stale/reused receipt (date too far from submission)
            date_gap = int(expense_data.get("date_gap_days", 0))
            if date_gap > 90:
                score += 0.15
                factors.append(
                    f"Receipt is {date_gap} days old — possible reused receipt"
                )
            elif date_gap > 30:
                score += 0.06
                factors.append(f"Receipt date is {date_gap} days ago")

            # Low OCR confidence (blurry/edited image)
            ocr_conf = float(expense_data.get("ocr_confidence", 1.0))
            if ocr_conf < 0.3 and amount > 200:
                score += 0.06
                factors.append(
                    f"Low receipt quality (OCR confidence: {ocr_conf:.0%})"
                )

        return min(score, 1.0), factors

    # ------------------------------------------------------------------
    # Ensemble
    # ------------------------------------------------------------------

    def predict_risk(self, expense_data: dict) -> dict:
        """
        Predict risk score using the three-layer ensemble.

        Returns dict with:
          - risk_score: 0–1 (weighted ensemble)
          - risk_level: 'low' / 'medium' / 'high'
          - risk_factors: list of human-readable explanations
          - layer_scores: breakdown of each layer's contribution
          - model_used: description of which models contributed
        """
        # Layer 1: Distilled XGBoost
        distilled = self._distilled_score(expense_data)

        # Layer 2: Isolation Forest
        isolation = self._isolation_score(expense_data)

        # Layer 3: Policy rules
        policy, risk_factors = self._policy_score(expense_data)

        # Weighted ensemble
        risk_score = (
            W_DISTILLED * distilled
            + W_ISOLATION * isolation
            + W_POLICY * policy
        )
        risk_score = round(max(0.0, min(1.0, risk_score)), 4)

        # Risk level
        if risk_score < 0.3:
            risk_level = "low"
        elif risk_score < 0.7:
            risk_level = "medium"
        else:
            risk_level = "high"

        # Model description
        models = []
        if self.student_loaded:
            models.append("distilled_xgboost(284K_real_tx)")
        else:
            models.append("heuristic_amount")
        if self.iforest_loaded:
            models.append("isolation_forest")
        else:
            models.append("heuristic_anomaly")
        models.append("policy_engine")

        return {
            "risk_score": risk_score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "model_used": " + ".join(models),
            "layer_scores": {
                "distilled_xgboost": round(distilled, 4),
                "isolation_forest": round(isolation, 4),
                "policy_engine": round(policy, 4),
            },
            "ensemble_weights": {
                "distilled": W_DISTILLED,
                "isolation": W_ISOLATION,
                "policy": W_POLICY,
            },
        }


# Singleton
_risk_scorer = None


def get_risk_scorer() -> RiskScorer:
    """Get or create the singleton risk scorer instance."""
    global _risk_scorer
    if _risk_scorer is None:
        _risk_scorer = RiskScorer()
    return _risk_scorer
