"""
Feature Engineering for the Knowledge-Distillation ML Pipeline.

Two feature sets:

1. KAGGLE-MAPPABLE FEATURES (17)
   Derived from Amount + Time only — computable from BOTH the Kaggle
   dataset AND live expense data.  Used by the distilled student model.

2. DOMAIN FEATURES (additional)
   Expense-specific features (category, merchant, receipt, etc.) that
   only exist for real expenses.  Used by the policy engine and the
   adaptive Isolation Forest.
"""

import math
import numpy as np
import pandas as pd
import logging

logger = logging.getLogger("TempoExpenseAI.FeatureEngineering")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Global amount statistics (computed once from Kaggle during training,
# then reused at inference).  Updated by set_amount_stats().
_AMOUNT_MEAN: float = 88.35  # Kaggle dataset mean (default)
_AMOUNT_STD: float = 250.12  # Kaggle dataset std  (default)

# Category-typical amount ranges (domain knowledge)
CATEGORY_AMOUNT_NORMS = {
    "meals": (8, 75),
    "travel": (150, 800),
    "accommodation": (80, 350),
    "office_supplies": (10, 200),
    "software": (10, 500),
    "equipment": (50, 2000),
    "training": (30, 500),
    "client_entertainment": (50, 500),
    "transportation": (5, 80),
    "miscellaneous": (5, 150),
}

HIGH_RISK_CATEGORIES = {"client_entertainment", "equipment", "miscellaneous"}

# ---------------------------------------------------------------------------
# 17 Kaggle-mappable feature names (ORDER MATTERS — matches model input)
# ---------------------------------------------------------------------------

KAGGLE_FEATURE_NAMES = [
    "amount",               # 1  raw amount
    "amount_log",           # 2  log1p(amount)
    "amount_sqrt",          # 3  sqrt(amount)
    "amount_zscore",        # 4  z-score vs global mean
    "amount_percentile",    # 5  percentile rank 0-1
    "amount_decimal_part",  # 6  fractional part (fraud uses round #s)
    "is_round_10",          # 7  divisible by 10
    "is_round_100",         # 8  divisible by 100
    "amount_bin",           # 9  binned into ranges
    "amount_magnitude",     # 10 order of magnitude
    "hour_of_day",          # 11 0-23
    "hour_sin",             # 12 sin cyclical encoding
    "hour_cos",             # 13 cos cyclical encoding
    "is_night",             # 14 hour 0-5 or 22-23
    "is_business_hours",    # 15 hour 9-17
    "is_weekend",           # 16 Sat/Sun
    "amount_x_is_night",   # 17 interaction: amount * is_night
]

# Isolation Forest features (behavioral — learned from real expenses)
ISOLATION_FEATURES = [
    "amount",
    "amount_log",
    "hour_of_day",
    "day_of_week",
    "expense_velocity_7d",
    "amount_vs_personal_mean",
    "amount_vs_dept_mean",
    "category_encoded",
    "time_since_last",
]

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def set_amount_stats(mean: float, std: float):
    """Set global amount statistics (called once during training)."""
    global _AMOUNT_MEAN, _AMOUNT_STD
    _AMOUNT_MEAN = mean
    _AMOUNT_STD = max(std, 1e-6)  # prevent division by zero
    logger.info(f"   Amount stats set: mean={mean:.2f}, std={std:.2f}")


def engineer_kaggle_features_batch(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineer the 17 Kaggle-mappable features from a DataFrame that has
    at least 'Amount' and 'Time' columns (the Kaggle dataset format).

    Returns a new DataFrame with exactly the 17 feature columns.
    """
    out = pd.DataFrame(index=df.index)

    amount = df["Amount"].astype(float)

    # --- Amount features ---
    out["amount"] = amount
    out["amount_log"] = np.log1p(amount)
    out["amount_sqrt"] = np.sqrt(amount)
    out["amount_zscore"] = (amount - _AMOUNT_MEAN) / _AMOUNT_STD
    out["amount_percentile"] = amount.rank(pct=True)
    out["amount_decimal_part"] = amount - np.floor(amount)
    out["is_round_10"] = (amount % 10 == 0).astype(int)
    out["is_round_100"] = (amount % 100 == 0).astype(int)
    out["amount_bin"] = pd.cut(
        amount,
        bins=[0, 25, 50, 100, 250, 500, 1000, float("inf")],
        labels=[0, 1, 2, 3, 4, 5, 6],
        include_lowest=True,
    ).astype(float)
    out["amount_magnitude"] = np.where(
        amount > 0, np.floor(np.log10(amount.clip(lower=0.01))), 0
    )

    # --- Time features ---
    # Kaggle 'Time' = seconds elapsed from first transaction (~2 days)
    time_sec = df["Time"].astype(float)
    hour_of_day = (time_sec % 86400) / 3600  # 0-23.999
    day_in_period = time_sec / 86400          # 0-~2

    out["hour_of_day"] = hour_of_day
    out["hour_sin"] = np.sin(2 * np.pi * hour_of_day / 24)
    out["hour_cos"] = np.cos(2 * np.pi * hour_of_day / 24)
    out["is_night"] = ((hour_of_day < 5) | (hour_of_day >= 22)).astype(int)
    out["is_business_hours"] = (
        (hour_of_day >= 9) & (hour_of_day < 17)
    ).astype(int)
    # Kaggle spans ~2 days; approximate weekday/weekend heuristically
    out["is_weekend"] = (day_in_period > 1.4).astype(int)  # second day as weekend proxy

    # --- Interaction ---
    out["amount_x_is_night"] = out["amount"] * out["is_night"]

    return out[KAGGLE_FEATURE_NAMES]


def engineer_kaggle_features_single(expense_data: dict) -> np.ndarray:
    """
    Compute the 17 Kaggle-mappable features from a live expense submission.

    Parameters
    ----------
    expense_data : dict with keys like 'amount', 'hour_of_day', 'is_weekend', etc.

    Returns
    -------
    np.ndarray of shape (1, 17)
    """
    amount = float(expense_data.get("amount", 0))
    hour = float(expense_data.get("hour_of_day", 12))
    is_wknd = int(expense_data.get("is_weekend", 0))

    features = [
        amount,                                           # 1 amount
        math.log1p(amount),                               # 2 amount_log
        math.sqrt(max(amount, 0)),                        # 3 amount_sqrt
        (amount - _AMOUNT_MEAN) / _AMOUNT_STD,            # 4 amount_zscore
        _amount_to_percentile(amount),                    # 5 amount_percentile
        amount - math.floor(amount),                      # 6 amount_decimal_part
        int(amount % 10 == 0),                            # 7 is_round_10
        int(amount % 100 == 0),                           # 8 is_round_100
        _amount_to_bin(amount),                           # 9 amount_bin
        math.floor(math.log10(max(amount, 0.01))),        # 10 amount_magnitude
        hour,                                             # 11 hour_of_day
        math.sin(2 * math.pi * hour / 24),                # 12 hour_sin
        math.cos(2 * math.pi * hour / 24),                # 13 hour_cos
        int(hour < 5 or hour >= 22),                      # 14 is_night
        int(9 <= hour < 17),                              # 15 is_business_hours
        is_wknd,                                          # 16 is_weekend
        amount * int(hour < 5 or hour >= 22),             # 17 amount_x_is_night
    ]

    return np.array(features, dtype=float).reshape(1, -1)


def engineer_isolation_features(expense_data: dict) -> np.ndarray:
    """
    Compute the 9 Isolation Forest features from a live expense.
    """
    amount = float(expense_data.get("amount", 0))
    features = [
        amount,
        math.log1p(amount),
        float(expense_data.get("hour_of_day", 12)),
        float(expense_data.get("day_of_week", 1)),
        float(expense_data.get("expense_velocity_7d", 1)),
        float(expense_data.get("amount_vs_personal_mean", 1.0)),
        float(expense_data.get("amount_vs_dept_mean", 1.0)),
        float(expense_data.get("category_encoded", 0)),
        float(expense_data.get("time_since_last", 7)),
    ]
    return np.array(features, dtype=float).reshape(1, -1)


def compute_policy_features(expense_data: dict) -> dict:
    """
    Compute domain-specific features used by the policy engine.
    These are NOT fed into any ML model — they power transparent rules.
    """
    amount = float(expense_data.get("amount", 0))
    category = expense_data.get("category", "miscellaneous")
    receipt = bool(expense_data.get("receipt_attached", False))

    # Category-amount deviation
    low, high = CATEGORY_AMOUNT_NORMS.get(category, (5, 500))
    cat_mid = (low + high) / 2
    category_amount_deviation = (amount - cat_mid) / max(cat_mid, 1)

    return {
        "category_amount_deviation": round(category_amount_deviation, 3),
        "is_high_risk_category": int(category in HIGH_RISK_CATEGORIES),
        "receipt_risk": int(not receipt and amount > 75),
        "amount_to_limit_ratio": round(
            amount / max(float(expense_data.get("monthly_limit", 5000)), 1), 3
        ),
        "budget_utilization": round(
            float(expense_data.get("monthly_spent", 0))
            / max(float(expense_data.get("monthly_limit", 5000)), 1),
            3,
        ),
        "description_quality": max(0, 1 - expense_data.get("description_length", 20) / 50),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Approximate CDF lookup for amount percentile (built from Kaggle stats)
_AMOUNT_PERCENTILE_THRESHOLDS = [
    (1, 0.05), (5, 0.20), (10, 0.30), (20, 0.40),
    (50, 0.55), (80, 0.65), (100, 0.70), (150, 0.77),
    (250, 0.85), (500, 0.92), (1000, 0.97), (5000, 0.99),
]


def _amount_to_percentile(amount: float) -> float:
    """Approximate percentile rank for an amount using Kaggle CDF."""
    for threshold, pct in _AMOUNT_PERCENTILE_THRESHOLDS:
        if amount <= threshold:
            return pct
    return 0.999


_BIN_EDGES = [0, 25, 50, 100, 250, 500, 1000]


def _amount_to_bin(amount: float) -> float:
    """Bin an amount into a category (0-6)."""
    for i, edge in enumerate(_BIN_EDGES):
        if amount <= edge:
            return float(max(i - 1, 0))
    return 6.0

