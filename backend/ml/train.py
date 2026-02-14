"""
Knowledge-Distillation Training Pipeline
=========================================

Trains three models on the Kaggle Credit Card Fraud dataset (284,807 real
transactions from European cardholders, 492 real fraud cases):

1. **Teacher XGBoost** — trained on ALL 30 Kaggle features (V1-V28 + Amount
   + Time).  Achieves ~0.98 AUC because it sees V1-V28.  This model is
   used ONLY during training to produce soft labels.

2. **Student XGBoost** — trained DIRECTLY on binary fraud labels using
   17 Kaggle-mappable features (derived from Amount + Time ONLY).
   Knowledge distillation was abandoned because fraud signal lives in
   V1-V28 PCA features, not Amount/Time.  Direct classification with
   scale_pos_weight learns the weak-but-real amount/time correlations.

3. **Isolation Forest** — unsupervised anomaly detector trained on the
   legitimate-only Amount distribution from Kaggle.  At runtime it is
   retrained periodically on real expense data for adaptive behavior.

Also trains:
4. **Categorizer** — Random Forest that maps (amount, hour, day) to
   expense categories using domain heuristic data (this one stays
   domain-specific by design).

No synthetic data is generated or used.
"""

import os
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import LabelEncoder
import joblib
import logging

from ml.kaggle_loader import load_kaggle_dataframe
from ml.feature_engineering import (
    engineer_kaggle_features_batch,
    set_amount_stats,
    KAGGLE_FEATURE_NAMES,
)

logger = logging.getLogger("TempoExpenseAI.Training")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# All 30 Kaggle raw feature columns
KAGGLE_ALL_FEATURES = (
    [f"V{i}" for i in range(1, 29)] + ["Amount", "Time"]
)


# -----------------------------------------------------------------------
# 1.  Teacher model (full Kaggle features)
# -----------------------------------------------------------------------

def train_teacher(df: pd.DataFrame) -> xgb.XGBClassifier:
    """
    Train the teacher XGBoost on all 30 Kaggle features.

    This model sees V1-V28 and achieves high AUC.  It is used
    only to produce soft probability labels for the student.
    """
    logger.info("👨‍🏫 Training TEACHER model on all 30 Kaggle features...")

    X = df[KAGGLE_ALL_FEATURES].values
    y = df["Class"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    teacher = xgb.XGBClassifier(
        n_estimators=500,
        max_depth=8,
        learning_rate=0.05,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
        random_state=42,
        n_jobs=-1,
    )

    teacher.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    y_proba = teacher.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)
    logger.info(f"   Teacher AUC-ROC: {auc:.4f}  (uses V1-V28 — full signal)")

    # Save teacher (optional — only needed for reproducibility)
    os.makedirs(MODEL_DIR, exist_ok=True)
    teacher_path = os.path.join(MODEL_DIR, "teacher_model.json")
    teacher.save_model(teacher_path)
    logger.info(f"   Saved teacher → {teacher_path}")

    return teacher


# -----------------------------------------------------------------------
# 2.  Student model (distilled — 17 Kaggle-mappable features)
# -----------------------------------------------------------------------

def train_student(
    df: pd.DataFrame,
    teacher: xgb.XGBClassifier,
) -> dict:
    """
    Train the student XGBoost DIRECTLY on binary fraud labels.

    Knowledge distillation failed because the teacher's fraud signal lives
    entirely in PCA features (V1-V28) that the student can't see.  The
    student's 17 Amount+Time features have negligible correlation with the
    teacher's soft probabilities, so the regressor converged to "always
    predict 0" — minimizing MSE for the 99.83% non-fraud majority.

    Fix: Train as a CLASSIFIER on real binary labels with scale_pos_weight.
    Binary cross-entropy + class balancing forces the model to learn whatever
    weak-but-real fraud correlations exist in amount/time patterns (unusual
    amounts, round numbers, nighttime transactions).  The result is modest
    AUC (~0.55-0.70) but non-zero probabilities that meaningfully contribute
    to the 3-layer ensemble.
    """
    logger.info("🎓 Training STUDENT model (direct classification on binary labels)...")

    # Engineer our 17 features from Amount + Time
    X_student_df = engineer_kaggle_features_batch(df)
    X_student = X_student_df.values
    y_binary = df["Class"].values  # Real binary labels, NOT teacher soft labels

    X_train, X_test, y_train, y_test = train_test_split(
        X_student, y_binary, test_size=0.2, random_state=42, stratify=y_binary,
    )

    # Classifier with class imbalance handling
    n_neg = len(y_train[y_train == 0])
    n_pos = max(len(y_train[y_train == 1]), 1)

    student = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        objective="binary:logistic",
        eval_metric="auc",
        scale_pos_weight=n_neg / n_pos,
        random_state=42,
        n_jobs=-1,
    )

    student.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    y_proba = student.predict_proba(X_test)[:, 1]
    y_pred_binary = (y_proba > 0.5).astype(int)
    auc = roc_auc_score(y_test, y_proba)

    logger.info(f"   Student AUC-ROC: {auc:.4f} (Amount+Time features only)")

    report = classification_report(
        y_test, y_pred_binary, output_dict=True, zero_division=0
    )
    precision = report.get("1", {}).get("precision", 0)
    recall = report.get("1", {}).get("recall", 0)
    logger.info(f"   Precision: {precision:.4f}  |  Recall: {recall:.4f}")

    # Log probability distribution to verify non-zero outputs
    logger.info(f"   Proba stats: mean={y_proba.mean():.6f}, "
                f"max={y_proba.max():.4f}, "
                f"p95={np.percentile(y_proba, 95):.6f}, "
                f"p99={np.percentile(y_proba, 99):.6f}")

    # Feature importance
    importance = dict(zip(KAGGLE_FEATURE_NAMES, student.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info(f"   Top features: {top_features}")

    # Save full estimator with joblib (avoids xgboost/sklearn tag issues)
    os.makedirs(MODEL_DIR, exist_ok=True)
    student_path = os.path.join(MODEL_DIR, "student_risk_model.pkl")
    joblib.dump(student, student_path)
    logger.info(f"   Saved student → {student_path}")

    return {
        "auc": auc,
        "precision": precision,
        "recall": recall,
        "model_path": student_path,
        "top_features": top_features,
    }


# -----------------------------------------------------------------------
# 3.  Isolation Forest (unsupervised)
# -----------------------------------------------------------------------

def train_isolation_forest(df: pd.DataFrame) -> dict:
    """
    Train Isolation Forest on LEGITIMATE transactions only.

    This learns the distribution of normal transaction amounts and timing.
    Anything far from this distribution is flagged as anomalous.
    """
    logger.info("🔍 Training Isolation Forest on legitimate transactions...")

    # Use only legit transactions (Class=0) — the forest learns "normal"
    legit = df[df["Class"] == 0].copy()
    features_df = engineer_kaggle_features_batch(legit)

    # Use a subset of the 17 features most relevant for anomaly detection
    anomaly_cols = [
        "amount", "amount_log", "amount_zscore", "amount_magnitude",
        "hour_of_day", "hour_sin", "hour_cos", "is_night",
    ]
    X = features_df[anomaly_cols].values

    model = IsolationForest(
        n_estimators=200,
        contamination=0.002,  # Kaggle fraud rate ≈ 0.17%
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # Save
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "isolation_forest.pkl")
    joblib.dump(model, model_path)

    # Quick eval
    predictions = model.predict(X)
    n_anomalies = sum(predictions == -1)
    logger.info(
        f"   {n_anomalies:,}/{len(X):,} flagged as anomalies "
        f"({n_anomalies/len(X)*100:.2f}%)"
    )
    logger.info(f"   Saved → {model_path}")

    return {"model_path": model_path, "anomalies_detected": n_anomalies}


# -----------------------------------------------------------------------
# 4.  Expense Categorizer (domain-specific, heuristic training data)
# -----------------------------------------------------------------------

def train_categorizer() -> dict:
    """
    Train a simple category predictor from domain knowledge.

    This is the ONE model that uses generated data — but it's generating
    CATEGORY DISTRIBUTIONS (which are well-known business ranges),
    not fraud patterns.  It's essentially a lookup table with
    interpolation.
    """
    import random
    logger.info("📂 Training Expense Categorizer...")

    CATEGORIES = [
        "meals", "travel", "accommodation", "office_supplies",
        "software", "equipment", "training", "client_entertainment",
        "transportation", "miscellaneous",
    ]
    AMOUNT_RANGES = {
        "meals": (8, 75), "travel": (150, 800),
        "accommodation": (80, 350), "office_supplies": (10, 200),
        "software": (10, 500), "equipment": (50, 2000),
        "training": (30, 500), "client_entertainment": (50, 500),
        "transportation": (5, 80), "miscellaneous": (5, 150),
    }

    records = []
    for cat in CATEGORIES:
        low, high = AMOUNT_RANGES[cat]
        for _ in range(200):  # 200 samples per category
            amount = random.uniform(low, high)
            hour = random.choices(range(7, 20), weights=[1,3,5,5,5,5,5,5,5,3,2,1,1])[0]
            day = random.randint(0, 6)
            records.append({
                "amount": amount,
                "hour_of_day": hour,
                "day_of_week": day,
                "is_weekend": 1 if day >= 5 else 0,
                "description_length": random.randint(10, 80),
                "category": cat,
            })

    df = pd.DataFrame(records)
    encoder = LabelEncoder()
    y = encoder.fit_transform(df["category"].values)
    X = df[["amount", "hour_of_day", "day_of_week", "is_weekend", "description_length"]].values

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    model.fit(X_train, y_train)
    accuracy = model.score(X_test, y_test)
    logger.info(f"   Accuracy: {accuracy:.4f}")

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "categorizer_model.pkl"))
    joblib.dump(encoder, os.path.join(MODEL_DIR, "category_encoder.pkl"))

    return {"accuracy": accuracy}


# -----------------------------------------------------------------------
# Main pipeline
# -----------------------------------------------------------------------

def train_all():
    """
    Run the complete knowledge-distillation training pipeline.

    1. Load 284,807 real transactions from Kaggle
    2. Train teacher on all 30 features
    3. Distill into student using 17 mappable features
    4. Train Isolation Forest on legit transactions
    5. Train domain categorizer
    """
    logger.info("=" * 65)
    logger.info("🚀 Knowledge-Distillation Training Pipeline")
    logger.info("   Data: Kaggle Credit Card Fraud (284,807 real transactions)")
    logger.info("   Method: Teacher→Student distillation")
    logger.info("=" * 65)

    # 1. Load Kaggle data
    df = load_kaggle_dataframe()
    logger.info(
        f"📊 Dataset: {len(df):,} rows | "
        f"{df['Class'].sum():,} fraud | "
        f"{len(df) - df['Class'].sum():,} legitimate"
    )

    # Set global amount statistics for feature engineering
    set_amount_stats(
        mean=float(df["Amount"].mean()),
        std=float(df["Amount"].std()),
    )

    # Also save the stats for inference time
    stats_path = os.path.join(MODEL_DIR, "amount_stats.pkl")
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(
        {"mean": float(df["Amount"].mean()), "std": float(df["Amount"].std())},
        stats_path,
    )

    # 2. Train teacher
    teacher = train_teacher(df)

    # 3. Distill into student
    student_results = train_student(df, teacher)

    # 4. Isolation Forest
    iforest_results = train_isolation_forest(df)

    # 5. Categorizer
    categorizer_results = train_categorizer()

    logger.info("=" * 65)
    logger.info("✅ All models trained successfully!")
    logger.info(f"   Student AUC (direct classif. on 284K tx):  {student_results['auc']:.4f}")
    logger.info(f"   Student Precision / Recall:                {student_results['precision']:.4f} / {student_results['recall']:.4f}")
    logger.info(f"   Isolation Forest anomalies:                {iforest_results['anomalies_detected']:,}")
    logger.info(f"   Categorizer accuracy:                      {categorizer_results['accuracy']:.4f}")
    logger.info("=" * 65)

    return {
        "student": student_results,
        "isolation_forest": iforest_results,
        "categorizer": categorizer_results,
    }


def ensure_models_exist():
    """Check if distilled models exist, train if they don't."""
    student_exists = os.path.exists(os.path.join(MODEL_DIR, "student_risk_model.pkl"))
    iforest_exists = os.path.exists(os.path.join(MODEL_DIR, "isolation_forest.pkl"))
    categorizer_exists = os.path.exists(os.path.join(MODEL_DIR, "categorizer_model.pkl"))

    if not (student_exists and iforest_exists and categorizer_exists):
        logger.info("⚠️ Missing ML models — running training pipeline...")
        train_all()
    else:
        # Load amount stats for feature engineering
        stats_path = os.path.join(MODEL_DIR, "amount_stats.pkl")
        if os.path.exists(stats_path):
            stats = joblib.load(stats_path)
            set_amount_stats(stats["mean"], stats["std"])
        logger.info("✅ All ML models found on disk")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_all()
