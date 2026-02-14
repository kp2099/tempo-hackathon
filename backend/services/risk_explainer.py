"""
Risk Explainer — Generates plain English explanations of AI decisions.

Instead of just showing "Risk: 0.35", this tells the user:
"This $450 client entertainment expense needs manager review because:
- The amount is 3x higher than your department's average
- No receipt was attached
- This is your first expense in this category"

This is key for the judges — it proves the AI isn't a black box.
"""

import logging
from typing import Optional

logger = logging.getLogger("TempoExpenseAI.RiskExplainer")


def explain_risk(
    expense_data: dict,
    risk_score: float,
    anomaly_score: float,
    risk_factors: list,
    decision: str,
    policy_result: dict,
) -> str:
    """
    Generate a plain English explanation of the AI agent's decision.

    Returns a human-readable paragraph that a non-technical user can understand.
    """
    amount = expense_data.get("amount", 0)
    category = expense_data.get("category", "unknown")
    merchant = expense_data.get("merchant", "unknown vendor")
    receipt = expense_data.get("receipt_attached", False)
    monthly_total = expense_data.get("monthly_total_amount", 0)
    monthly_count = expense_data.get("monthly_expense_count", 0)
    amount_ratio = expense_data.get("amount_vs_avg_ratio", 1.0)
    cat_freq = expense_data.get("category_frequency", 0)
    is_weekend = expense_data.get("is_weekend", 0)
    hour = expense_data.get("hour_of_day", 12)

    explanations = []
    details = []

    # ─── Overall Summary ──────────────────────────────────────────
    category_display = category.replace("_", " ")

    if decision == "auto_approved" or decision == "paid":
        explanations.append(
            f"✅ This ${amount:,.2f} {category_display} expense from {merchant} "
            f"was automatically approved by AgentFin."
        )
    elif decision == "manager_review":
        explanations.append(
            f"⏳ This ${amount:,.2f} {category_display} expense from {merchant} "
            f"needs manager review."
        )
    elif decision in ("rejected", "flagged"):
        explanations.append(
            f"🚨 This ${amount:,.2f} {category_display} expense from {merchant} "
            f"was flagged for investigation."
        )

    # ─── Specific Reasons ──────────────────────────────────────────
    # Amount-based insights
    if amount_ratio > 3:
        details.append(
            f"The amount is {amount_ratio:.1f}x higher than the employee's "
            f"typical expense"
        )
    elif amount_ratio > 1.5:
        details.append(
            f"The amount is somewhat higher than usual "
            f"({amount_ratio:.1f}x the average)"
        )
    elif amount_ratio < 0.5:
        details.append("The amount is well below the employee's average — routine expense")

    # Receipt
    if not receipt and amount > 25:
        details.append(f"No receipt attached for a ${amount:,.2f} expense")
    elif receipt:
        details.append("Receipt is attached ✓")

    # Anomaly insights
    if anomaly_score > 0.6:
        details.append(
            f"Statistical anomaly detected — this expense deviates significantly "
            f"from the employee's normal spending pattern "
            f"(anomaly confidence: {anomaly_score:.0%})"
        )
    elif anomaly_score > 0.3:
        details.append(
            f"Spending pattern is slightly unusual (anomaly score: {anomaly_score:.0%})"
        )

    # Category frequency
    if cat_freq < 0.05 and cat_freq > 0:
        details.append(
            f"This employee rarely submits {category_display} expenses "
            f"(only {cat_freq:.0%} of their history)"
        )
    elif cat_freq == 0:
        details.append(f"This is the employee's first {category_display} expense")

    # Monthly context
    if monthly_total > 0:
        details.append(
            f"Employee has submitted {monthly_count} expense(s) this month "
            f"totaling ${monthly_total:,.2f}"
        )

    # Timing
    if is_weekend:
        details.append("Submitted on a weekend (unusual for business expenses)")
    if hour < 6 or hour > 22:
        details.append(f"Submitted at an unusual hour ({hour}:00)")

    # OCR receipt verification
    if expense_data.get("ocr_success"):
        ocr_confidence = expense_data.get("ocr_confidence", 0)
        amt_mismatch = expense_data.get("amount_mismatch", 0)

        if amt_mismatch > 0.15:
            ocr_amt = expense_data.get("ocr_amount", "?")
            details.append(
                f"🧾 Receipt OCR detected amount ${ocr_amt} vs submitted "
                f"${amount:,.2f} ({amt_mismatch:.0%} mismatch)"
            )
        elif amt_mismatch == 0 and expense_data.get("ocr_amount") is not None:
            details.append("🧾 Receipt amount matches submitted amount ✓")

        if expense_data.get("merchant_mismatch"):
            ocr_merch = expense_data.get("ocr_merchant", "unknown")
            details.append(
                f"🧾 Receipt merchant '{ocr_merch}' differs from submitted merchant"
            )

        date_gap = expense_data.get("date_gap_days", 0)
        if date_gap > 30:
            details.append(f"🧾 Receipt date is {date_gap} days old")

        if ocr_confidence > 0:
            details.append(f"🧾 Receipt OCR confidence: {ocr_confidence:.0%}")

    # Policy violations
    violations = policy_result.get("violations", [])
    for v in violations:
        severity_icon = "🚫" if v.get("severity") == "block" else "⚠️"
        details.append(f"{severity_icon} Policy: {v.get('message', '')}")

    # ML risk factors (from the model)
    if risk_factors:
        readable_factors = []
        for f in risk_factors[:3]:
            readable_factors.append(_humanize_factor(f))
        if readable_factors:
            details.append(
                f"AI risk signals: {'; '.join(readable_factors)}"
            )

    # ─── Compose Final Explanation ────────────────────────────────
    if details:
        explanations.append("Here's why: " + ". ".join(details) + ".")

    # Risk score summary
    risk_pct = risk_score * 100
    if risk_score < 0.3:
        explanations.append(f"Overall risk: {risk_pct:.0f}% (Low ✅)")
    elif risk_score < 0.7:
        explanations.append(f"Overall risk: {risk_pct:.0f}% (Medium ⚠️)")
    else:
        explanations.append(f"Overall risk: {risk_pct:.0f}% (High 🔴)")

    return " ".join(explanations)


def _humanize_factor(factor: str) -> str:
    """Convert ML feature names into human-readable text."""
    mapping = {
        "amount": "expense amount",
        "amount_vs_avg_ratio": "amount vs average",
        "monthly_total_amount": "monthly spending total",
        "monthly_expense_count": "number of expenses this month",
        "category_frequency": "category usage frequency",
        "merchant_frequency": "merchant history",
        "is_round_number": "suspiciously round amount",
        "description_length": "description detail level",
        "days_since_last_expense": "time since last expense",
        "is_weekend": "weekend submission",
        "hour_of_day": "submission timing",
        "receipt_attached": "receipt status",
    }
    return mapping.get(factor, factor)

