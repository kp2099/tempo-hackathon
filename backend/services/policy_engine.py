"""
Policy Engine - Enforces organizational expense rules.

Severity levels:
  - "warning" : logged, does NOT block approval
  - "flag"    : sends to manager review, does NOT hard-reject
  - "block"   : hard-rejects the expense
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from database import PolicyDB, ExpenseDB, EmployeeDB
from sqlalchemy import func
from datetime import datetime, timedelta

logger = logging.getLogger("TempoExpenseAI.PolicyEngine")


class PolicyViolation:
    """Represents a single policy violation."""
    def __init__(self, policy_name: str, message: str, severity: str = "warning"):
        self.policy_name = policy_name
        self.message = message
        self.severity = severity  # "warning", "flag", "block"

    def to_dict(self):
        return {
            "policy": self.policy_name,
            "message": self.message,
            "severity": self.severity,
        }


class PolicyEngine:
    """Evaluates expenses against organizational policies."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def check_all_policies(
        self,
        expense_data: dict,
        employee_id: str,
    ) -> dict:
        """
        Run all policy checks on an expense.

        Returns:
            dict with passed (bool), violations (list), and details
        """
        violations: List[PolicyViolation] = []

        # 1. Receipt requirement
        violations.extend(self._check_receipt(expense_data))

        # 2. Maximum single expense
        violations.extend(self._check_max_amount(expense_data))

        # 3. Category-specific limits
        violations.extend(self._check_category_limit(expense_data))

        # 4. Monthly spending limit
        if self.db:
            violations.extend(
                self._check_monthly_limit(expense_data, employee_id)
            )

        # 5. Duplicate detection
        if self.db:
            violations.extend(
                self._check_duplicates(expense_data, employee_id)
            )

        # 6. OCR receipt verification
        violations.extend(self._check_ocr_verification(expense_data))

        # Determine overall result
        blocking = [v for v in violations if v.severity == "block"]
        warnings = [v for v in violations if v.severity == "warning"]
        flags = [v for v in violations if v.severity == "flag"]

        passed = len(blocking) == 0

        return {
            "passed": passed,
            "violations": [v.to_dict() for v in violations],
            "blocking_count": len(blocking),
            "warning_count": len(warnings),
            "flag_count": len(flags),
            "summary": (
                "All policies passed" if passed
                else f"Blocked by {len(blocking)} policy violation(s)"
            ),
        }

    def _check_receipt(self, expense_data: dict) -> List[PolicyViolation]:
        """Check if receipt is required but missing."""
        amount = expense_data.get("amount", 0)
        receipt = expense_data.get("receipt_attached", False)

        if amount > 25 and not receipt:
            # Only hard-block for very large amounts with no receipt
            if amount > 1000:
                return [PolicyViolation(
                    "Receipt Required",
                    f"Receipt required for expenses above $1,000 "
                    f"(expense: ${amount:.2f})",
                    severity="block",
                )]
            elif amount > 200:
                # Flag for manager review but don't hard-reject
                return [PolicyViolation(
                    "Receipt Recommended",
                    f"No receipt attached for ${amount:.2f} expense. "
                    f"Recommended for amounts above $200.",
                    severity="flag",
                )]
            else:
                # Just a warning for smaller amounts
                return [PolicyViolation(
                    "Receipt Suggested",
                    f"Consider attaching receipt for ${amount:.2f} expense.",
                    severity="warning",
                )]
        return []

    def _check_max_amount(self, expense_data: dict) -> List[PolicyViolation]:
        """Check single expense maximum."""
        amount = expense_data.get("amount", 0)

        if amount > 25000:
            return [PolicyViolation(
                "Maximum Expense Limit",
                f"Expense ${amount:.2f} exceeds maximum single expense "
                f"limit of $25,000",
                severity="block",
            )]
        elif amount > 10000:
            return [PolicyViolation(
                "High Value Expense",
                f"Expense ${amount:.2f} exceeds $10,000 — requires manager approval",
                severity="flag",
            )]
        return []

    def _check_category_limit(self, expense_data: dict) -> List[PolicyViolation]:
        """Check category-specific limits."""
        category = expense_data.get("category", "")
        amount = expense_data.get("amount", 0)

        # Much more reasonable limits
        category_limits = {
            "meals": {"warn": 200, "block": 500},
            "transportation": {"warn": 300, "block": 800},
            "office_supplies": {"warn": 1000, "block": 3000},
            "client_entertainment": {"warn": 600, "block": 2000},
        }

        limits = category_limits.get(category)
        if limits:
            if amount > limits["block"]:
                return [PolicyViolation(
                    f"{category.replace('_', ' ').title()} Limit",
                    f"${amount:.2f} exceeds {category.replace('_', ' ')} "
                    f"limit of ${limits['block']:.0f}",
                    severity="flag",  # Flag, don't hard-block
                )]
            elif amount > limits["warn"]:
                return [PolicyViolation(
                    f"{category.replace('_', ' ').title()} Advisory",
                    f"${amount:.2f} is above typical {category.replace('_', ' ')} "
                    f"range (${limits['warn']:.0f})",
                    severity="warning",
                )]
        return []

    def _check_monthly_limit(
        self, expense_data: dict, employee_id: str
    ) -> List[PolicyViolation]:
        """Check monthly spending limit for employee."""
        if not self.db:
            return []

        try:
            # Get employee's monthly limit
            employee = self.db.query(EmployeeDB).filter(
                EmployeeDB.employee_id == employee_id
            ).first()

            monthly_limit = employee.monthly_limit if employee else 10000.0

            # Only count APPROVED/PAID expenses toward monthly total
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            monthly_total = self.db.query(func.sum(ExpenseDB.amount)).filter(
                ExpenseDB.employee_id == employee_id,
                ExpenseDB.submitted_at >= month_start,
                ExpenseDB.status.in_(["auto_approved", "approved", "paid"]),
            ).scalar() or 0.0

            new_total = monthly_total + expense_data.get("amount", 0)

            if new_total > monthly_limit:
                severity = "block" if new_total > monthly_limit * 1.5 else "flag"
                return [PolicyViolation(
                    "Monthly Spending Limit",
                    f"Monthly total ${new_total:.2f} would exceed limit of "
                    f"${monthly_limit:.2f} (already spent: ${monthly_total:.2f})",
                    severity=severity,
                )]
        except Exception as e:
            logger.warning(f"Monthly limit check failed: {e}")

        return []

    def _check_duplicates(
        self, expense_data: dict, employee_id: str
    ) -> List[PolicyViolation]:
        """Check for duplicate expenses."""
        if not self.db:
            return []

        try:
            # Look for same amount, category, merchant within last 24h
            yesterday = datetime.utcnow() - timedelta(hours=24)
            duplicates = self.db.query(ExpenseDB).filter(
                ExpenseDB.employee_id == employee_id,
                ExpenseDB.amount == expense_data.get("amount"),
                ExpenseDB.category == expense_data.get("category"),
                ExpenseDB.merchant == expense_data.get("merchant"),
                ExpenseDB.submitted_at >= yesterday,
                # Only check against expenses that weren't already rejected
                ExpenseDB.status.notin_(["rejected", "flagged"]),
            ).count()

            if duplicates > 0:
                return [PolicyViolation(
                    "Potential Duplicate",
                    f"Found {duplicates} similar expense(s) in last 24 hours "
                    f"(same amount, category, and merchant)",
                    severity="warning",  # Just a warning, not a block
                )]
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")

        return []

    def _check_ocr_verification(self, expense_data: dict) -> List[PolicyViolation]:
        """Check OCR-extracted receipt data against submitted expense data."""
        if not expense_data.get("ocr_success"):
            return []

        violations = []
        amount = expense_data.get("amount", 0)

        # Amount mismatch — OCR total vs submitted amount
        amt_mismatch = float(expense_data.get("amount_mismatch", 0))
        if amt_mismatch > 0.50:
            ocr_amt = expense_data.get("ocr_amount", "?")
            violations.append(PolicyViolation(
                "Receipt Amount Mismatch",
                f"Receipt shows ${ocr_amt} but ${amount:.2f} was submitted "
                f"({amt_mismatch:.0%} difference)",
                severity="flag",
            ))
        elif amt_mismatch > 0.15:
            ocr_amt = expense_data.get("ocr_amount", "?")
            violations.append(PolicyViolation(
                "Receipt Amount Discrepancy",
                f"Receipt shows ${ocr_amt} vs submitted ${amount:.2f} "
                f"({amt_mismatch:.0%} difference)",
                severity="warning",
            ))

        # Merchant mismatch
        if expense_data.get("merchant_mismatch"):
            ocr_merch = expense_data.get("ocr_merchant", "unknown")
            submitted_merch = expense_data.get("merchant", "unknown")
            violations.append(PolicyViolation(
                "Receipt Merchant Mismatch",
                f"Receipt merchant '{ocr_merch}' doesn't match "
                f"submitted '{submitted_merch}'",
                severity="warning",
            ))

        # Old/stale receipt
        date_gap = int(expense_data.get("date_gap_days", 0))
        if date_gap > 90:
            violations.append(PolicyViolation(
                "Stale Receipt",
                f"Receipt date is {date_gap} days old — "
                f"possible reused or old receipt",
                severity="flag",
            ))
        elif date_gap > 30:
            violations.append(PolicyViolation(
                "Old Receipt",
                f"Receipt date is {date_gap} days ago",
                severity="warning",
            ))

        return violations
