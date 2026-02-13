"""
Generate realistic synthetic expense data for training the ML models.
Includes both normal expenses and injected anomalies/fraud patterns.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import random
import os

CATEGORIES = [
    "meals", "travel", "accommodation", "office_supplies",
    "software", "equipment", "training", "client_entertainment",
    "transportation", "miscellaneous"
]

DEPARTMENTS = ["engineering", "sales", "marketing", "hr", "finance", "operations"]

MERCHANTS = {
    "meals": ["Chipotle", "Starbucks", "Subway", "Local Restaurant", "DoorDash", "UberEats"],
    "travel": ["Delta Airlines", "United Airlines", "American Airlines", "Southwest", "JetBlue"],
    "accommodation": ["Marriott", "Hilton", "Holiday Inn", "Airbnb", "Hampton Inn"],
    "office_supplies": ["Staples", "Amazon", "Office Depot", "Best Buy"],
    "software": ["Adobe", "Slack", "Zoom", "GitHub", "AWS", "Google Cloud"],
    "equipment": ["Apple Store", "Dell", "Lenovo", "Amazon", "Best Buy"],
    "training": ["Udemy", "Coursera", "Conference Registration", "Workshop"],
    "client_entertainment": ["Restaurant", "Event Venue", "Golf Club", "Sports Event"],
    "transportation": ["Uber", "Lyft", "Taxi", "Car Rental", "Parking"],
    "miscellaneous": ["Various", "Other", "Misc Vendor"],
}

# Typical amount ranges per category
AMOUNT_RANGES = {
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


def generate_normal_expense(employee_id: str, department: str) -> dict:
    """Generate a single normal (non-fraudulent) expense."""
    category = random.choice(CATEGORIES)
    low, high = AMOUNT_RANGES[category]
    amount = round(random.uniform(low, high), 2)

    # Normal business hours submission (8am - 7pm, weekdays)
    hour = random.choices(range(7, 20), weights=[1, 3, 5, 5, 5, 5, 5, 5, 5, 3, 2, 1, 1])[0]
    day_of_week = random.choices(range(7), weights=[5, 5, 5, 5, 5, 1, 1])[0]
    is_weekend = 1 if day_of_week >= 5 else 0

    merchant = random.choice(MERCHANTS.get(category, ["Unknown"]))

    return {
        "employee_id": employee_id,
        "department": department,
        "amount": amount,
        "category": category,
        "merchant": merchant,
        "description": f"{category.replace('_', ' ').title()} - {merchant}",
        "receipt_attached": random.random() > 0.15,  # 85% attach receipts
        "hour_of_day": hour,
        "day_of_week": day_of_week,
        "is_weekend": is_weekend,
        "is_round_number": 1 if amount % 10 == 0 else 0,
        "description_length": random.randint(10, 80),
        "is_anomaly": 0,
    }


def generate_anomalous_expense(employee_id: str, department: str) -> dict:
    """Generate a fraudulent/anomalous expense."""
    anomaly_type = random.choice([
        "high_amount", "odd_time", "category_mismatch",
        "round_number_pattern", "no_receipt_high", "duplicate_pattern"
    ])

    category = random.choice(CATEGORIES)
    merchant = random.choice(MERCHANTS.get(category, ["Unknown"]))

    expense = {
        "employee_id": employee_id,
        "department": department,
        "category": category,
        "merchant": merchant,
        "receipt_attached": True,
        "is_weekend": 0,
        "description_length": random.randint(5, 30),
        "is_anomaly": 1,
    }

    if anomaly_type == "high_amount":
        # Unusually high amount for the category
        low, high = AMOUNT_RANGES[category]
        expense["amount"] = round(random.uniform(high * 2, high * 5), 2)
        expense["hour_of_day"] = random.randint(8, 18)
        expense["day_of_week"] = random.randint(0, 4)
        expense["is_round_number"] = 0
        expense["receipt_attached"] = random.random() > 0.5

    elif anomaly_type == "odd_time":
        # Submitted at unusual hours (midnight - 5am)
        low, high = AMOUNT_RANGES[category]
        expense["amount"] = round(random.uniform(low, high * 1.5), 2)
        expense["hour_of_day"] = random.randint(0, 5)
        expense["day_of_week"] = random.randint(0, 6)
        expense["is_weekend"] = 1 if expense["day_of_week"] >= 5 else 0
        expense["is_round_number"] = 0

    elif anomaly_type == "category_mismatch":
        # Amount doesn't match category norms
        expense["category"] = "office_supplies"
        expense["amount"] = round(random.uniform(800, 3000), 2)
        expense["hour_of_day"] = random.randint(8, 18)
        expense["day_of_week"] = random.randint(0, 4)
        expense["is_round_number"] = 0

    elif anomaly_type == "round_number_pattern":
        # Suspicious round numbers
        expense["amount"] = float(random.choice([100, 200, 300, 500, 1000, 2000]))
        expense["hour_of_day"] = random.randint(8, 18)
        expense["day_of_week"] = random.randint(0, 6)
        expense["is_round_number"] = 1
        expense["is_weekend"] = 1 if expense["day_of_week"] >= 5 else 0

    elif anomaly_type == "no_receipt_high":
        # High amount with no receipt
        low, high = AMOUNT_RANGES[category]
        expense["amount"] = round(random.uniform(high * 1.5, high * 3), 2)
        expense["receipt_attached"] = False
        expense["hour_of_day"] = random.randint(8, 18)
        expense["day_of_week"] = random.randint(0, 4)
        expense["is_round_number"] = 0

    elif anomaly_type == "duplicate_pattern":
        # Same amount repeated (suspicious)
        expense["amount"] = round(random.uniform(50, 300), 2)
        expense["hour_of_day"] = random.randint(8, 18)
        expense["day_of_week"] = random.randint(0, 4)
        expense["is_round_number"] = 0

    expense["description"] = f"{category.replace('_', ' ').title()} - {merchant}"
    return expense


def generate_dataset(
    n_employees: int = 50,
    expenses_per_employee: int = 40,
    anomaly_rate: float = 0.12,
) -> pd.DataFrame:
    """Generate a complete synthetic expense dataset."""
    records = []

    for i in range(n_employees):
        employee_id = f"EMP{i+1:04d}"
        department = random.choice(DEPARTMENTS)

        n_expenses = random.randint(
            int(expenses_per_employee * 0.5),
            int(expenses_per_employee * 1.5)
        )

        # Track this employee's spending for behavioral features
        employee_expenses = []

        for _ in range(n_expenses):
            if random.random() < anomaly_rate:
                expense = generate_anomalous_expense(employee_id, department)
            else:
                expense = generate_normal_expense(employee_id, department)

            employee_expenses.append(expense["amount"])

            # Add behavioral features
            expense["monthly_expense_count"] = len(employee_expenses)
            expense["monthly_total_amount"] = sum(employee_expenses)
            avg = np.mean(employee_expenses) if employee_expenses else expense["amount"]
            expense["amount_vs_avg_ratio"] = round(expense["amount"] / max(avg, 1), 2)

            if len(employee_expenses) > 1:
                expense["days_since_last_expense"] = random.randint(0, 14)
            else:
                expense["days_since_last_expense"] = random.randint(7, 30)

            # Category and merchant frequency (simulated)
            expense["category_frequency"] = round(random.uniform(0.1, 0.9), 2)
            expense["merchant_frequency"] = round(random.uniform(0.05, 0.6), 2)

            records.append(expense)

    df = pd.DataFrame(records)
    return df


def save_dataset(output_dir: str = None):
    """Generate and save the synthetic dataset."""
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(__file__), "data")

    os.makedirs(output_dir, exist_ok=True)

    print("📊 Generating synthetic expense data...")
    df = generate_dataset(n_employees=50, expenses_per_employee=40, anomaly_rate=0.12)

    filepath = os.path.join(output_dir, "synthetic_expenses.csv")
    df.to_csv(filepath, index=False)
    print(f"✅ Saved {len(df)} records to {filepath}")
    print(f"   Normal: {len(df[df['is_anomaly'] == 0])}")
    print(f"   Anomalous: {len(df[df['is_anomaly'] == 1])}")

    return df


if __name__ == "__main__":
    save_dataset()

