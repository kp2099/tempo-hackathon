"""
Kaggle Credit Card Fraud Dataset Loader.

Downloads and caches the ULB credit card fraud dataset (284,807 real
transactions with 492 real fraud cases) via kagglehub.

Dataset: https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud
Source:  ULB Machine Learning Group (Université Libre de Bruxelles)
Paper:   Andrea Dal Pozzolo et al. "Calibrating Probability with
         Undersampling for Unbalanced Classification" (IEEE SSCI 2015)
"""

import os
import logging
import pandas as pd

logger = logging.getLogger("TempoExpenseAI.KaggleLoader")

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def download_kaggle_dataset() -> str:
    """
    Download the credit card fraud dataset via kagglehub.

    Returns the path to the directory containing creditcard.csv.
    The download is cached — subsequent calls are instant.
    """
    try:
        import kagglehub

        logger.info("📥 Downloading Kaggle Credit Card Fraud dataset...")
        path = kagglehub.dataset_download("mlg-ulb/creditcardfraud")
        logger.info(f"   Cached at: {path}")
        return path
    except Exception as e:
        logger.error(f"❌ Kaggle download failed: {e}")
        raise


def load_kaggle_dataframe() -> pd.DataFrame:
    """
    Load the Kaggle credit card fraud dataset as a pandas DataFrame.

    Returns:
        DataFrame with columns: Time, V1-V28, Amount, Class
        - 284,807 rows
        - Class: 0 = legitimate, 1 = fraud (492 cases)
    """
    # Check for a local copy first
    local_path = os.path.join(DATA_DIR, "creditcard.csv")
    if os.path.exists(local_path):
        logger.info(f"📊 Loading Kaggle data from local cache: {local_path}")
        df = pd.read_csv(local_path)
        logger.info(f"   {len(df):,} rows | {df['Class'].sum():,} fraud cases")
        return df

    # Download via kagglehub
    dataset_dir = download_kaggle_dataset()

    # Find the CSV in the downloaded directory
    csv_path = None
    for root, dirs, files in os.walk(dataset_dir):
        for f in files:
            if f.lower() == "creditcard.csv":
                csv_path = os.path.join(root, f)
                break
        if csv_path:
            break

    if csv_path is None:
        raise FileNotFoundError(
            f"creditcard.csv not found in downloaded dataset at {dataset_dir}"
        )

    logger.info(f"📊 Loading Kaggle data from: {csv_path}")
    df = pd.read_csv(csv_path)
    logger.info(f"   {len(df):,} rows | {df['Class'].sum():,} fraud cases")

    # Cache a local copy for faster subsequent loads
    os.makedirs(DATA_DIR, exist_ok=True)
    df.to_csv(local_path, index=False)
    logger.info(f"   Cached locally at: {local_path}")

    return df


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = load_kaggle_dataframe()
    print(f"\nDataset shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"\nClass distribution:")
    print(df["Class"].value_counts())
    print(f"\nAmount stats:")
    print(df["Amount"].describe())

