"""
Training pipeline for all ML models:
1. XGBoost Risk Scorer
2. Isolation Forest Anomaly Detector
3. Random Forest Expense Categorizer
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

from ml.generate_synthetic_data import generate_dataset

logger = logging.getLogger("TempoExpenseAI.Training")

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# Feature columns for risk model
RISK_FEATURES = [
    "amount", "hour_of_day", "day_of_week", "is_weekend",
    "days_since_last_expense", "monthly_expense_count",
    "monthly_total_amount", "amount_vs_avg_ratio",
    "category_frequency", "merchant_frequency",
    "is_round_number", "receipt_attached", "description_length",
]

ANOMALY_FEATURES = [
    "amount", "hour_of_day", "day_of_week", "is_weekend",
    "monthly_expense_count", "monthly_total_amount",
    "amount_vs_avg_ratio", "is_round_number",
]


def train_risk_model(df: pd.DataFrame) -> dict:
    """Train XGBoost risk scoring model."""
    logger.info("🎯 Training XGBoost Risk Scorer...")

    # Convert boolean columns to int
    for col in ["receipt_attached", "is_weekend", "is_round_number"]:
        if col in df.columns:
            df[col] = df[col].astype(int)

    X = df[RISK_FEATURES].values
    y = df["is_anomaly"].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=150,
        max_depth=6,
        learning_rate=0.1,
        objective="binary:logistic",
        eval_metric="auc",
        use_label_encoder=False,
        scale_pos_weight=len(y_train[y_train == 0]) / max(len(y_train[y_train == 1]), 1),
        random_state=42,
    )

    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=False,
    )

    # Evaluate
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_proba)

    # Save model
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "risk_model.json")
    model.save_model(model_path)

    report = classification_report(y_test, y_pred, output_dict=True)
    logger.info(f"   AUC-ROC: {auc:.4f}")
    logger.info(f"   Precision: {report['1']['precision']:.4f}")
    logger.info(f"   Recall: {report['1']['recall']:.4f}")

    # Feature importance
    importance = dict(zip(RISK_FEATURES, model.feature_importances_))
    top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]
    logger.info(f"   Top features: {top_features}")

    return {"auc": auc, "report": report, "model_path": model_path}


def train_anomaly_model(df: pd.DataFrame) -> dict:
    """Train Isolation Forest anomaly detector."""
    logger.info("🔍 Training Isolation Forest Anomaly Detector...")

    for col in ["is_weekend", "is_round_number"]:
        if col in df.columns:
            df[col] = df[col].astype(int)

    X = df[ANOMALY_FEATURES].values

    model = IsolationForest(
        n_estimators=100,
        contamination=0.12,  # match our anomaly rate
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    # Save
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "anomaly_model.pkl")
    joblib.dump(model, model_path)

    # Quick eval
    predictions = model.predict(X)
    n_anomalies = sum(predictions == -1)
    logger.info(f"   Detected {n_anomalies}/{len(X)} anomalies ({n_anomalies/len(X)*100:.1f}%)")

    return {"model_path": model_path, "anomalies_detected": n_anomalies}


def train_categorizer(df: pd.DataFrame) -> dict:
    """Train Random Forest expense categorizer."""
    logger.info("📂 Training Expense Categorizer...")

    encoder = LabelEncoder()
    y = encoder.fit_transform(df["category"].values)

    features = ["amount", "hour_of_day", "day_of_week", "is_weekend", "description_length"]
    for col in ["is_weekend"]:
        if col in df.columns:
            df[col] = df[col].astype(int)

    X = df[features].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=10,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    accuracy = model.score(X_test, y_test)
    logger.info(f"   Accuracy: {accuracy:.4f}")

    # Save
    os.makedirs(MODEL_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_DIR, "categorizer_model.pkl")
    encoder_path = os.path.join(MODEL_DIR, "category_encoder.pkl")
    joblib.dump(model, model_path)
    joblib.dump(encoder, encoder_path)

    return {"accuracy": accuracy, "model_path": model_path}


def train_all():
    """Run the complete training pipeline."""
    logger.info("=" * 60)
    logger.info("🚀 Starting ML Training Pipeline")
    logger.info("=" * 60)

    # Generate or load data
    data_path = os.path.join(DATA_DIR, "synthetic_expenses.csv")
    if os.path.exists(data_path):
        logger.info(f"📊 Loading existing dataset from {data_path}")
        df = pd.read_csv(data_path)
    else:
        logger.info("📊 Generating synthetic dataset...")
        os.makedirs(DATA_DIR, exist_ok=True)
        df = generate_dataset(n_employees=50, expenses_per_employee=40, anomaly_rate=0.12)
        df.to_csv(data_path, index=False)
        logger.info(f"   Saved {len(df)} records")

    logger.info(f"📊 Dataset: {len(df)} records, {df['is_anomaly'].sum()} anomalies")

    # Train all models
    risk_results = train_risk_model(df.copy())
    anomaly_results = train_anomaly_model(df.copy())
    categorizer_results = train_categorizer(df.copy())

    logger.info("=" * 60)
    logger.info("✅ All models trained successfully!")
    logger.info(f"   Risk Model AUC: {risk_results['auc']:.4f}")
    logger.info(f"   Anomaly Detector: {anomaly_results['anomalies_detected']} anomalies found")
    logger.info(f"   Categorizer Accuracy: {categorizer_results['accuracy']:.4f}")
    logger.info("=" * 60)

    return {
        "risk": risk_results,
        "anomaly": anomaly_results,
        "categorizer": categorizer_results,
    }


def ensure_models_exist():
    """Check if models exist, train if they don't."""
    risk_exists = os.path.exists(os.path.join(MODEL_DIR, "risk_model.json"))
    anomaly_exists = os.path.exists(os.path.join(MODEL_DIR, "anomaly_model.pkl"))
    categorizer_exists = os.path.exists(os.path.join(MODEL_DIR, "categorizer_model.pkl"))

    if not (risk_exists and anomaly_exists and categorizer_exists):
        logger.info("⚠️ Missing ML models — running training pipeline...")
        train_all()
    else:
        logger.info("✅ All ML models found on disk")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    train_all()

