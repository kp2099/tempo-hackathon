"""
Policy Engine - Enforces organizational expense rules.
Rules can be loaded from DB or configured via code.
"""

import logging
from typing import List, Optional
from sqlalchemy.orm import Session
from database import PolicyDB, ExpenseDB, EmployeeDB
from sqlalchemy import func
from datetime import datetime, timedelta

logger = logging.getLogger("TempoExpenseAI.PolicyEngine")


# Default policies (used if no DB policies configured)
DEFAULT_POLICIES = [
    {
        "name": "Receipt required above $25",
        "check": "receipt_required",
        "requires_receipt_above": 25.0,
    },
    {
        "name": "Single expense limit $5000",
        "check": "max_single_expense",
        "max_amount": 5000.0,
    },
    {
        "name": "Meals limit $100 per expense",
        "check": "category_limit",
        "category": "meals",
        "max_amount": 100.0,
    },
    {
        "name": "Monthly employee limit $5000",
        "check": "monthly_limit",
        "max_amount": 5000.0,
    },
]


class PolicyViolation:
    """Represents a single policy violation."""
    def __init__(self, policy_name: str, message: str, severity: str = "warning"):
        self.policy_name = policy_name
        self.message = message
        self.severity = severity  # "warning", "block", "flag"

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
        threshold = 25.0

        if amount > threshold and not receipt:
            severity = "block" if amount > 100 else "warning"
            return [PolicyViolation(
                "Receipt Required",
                f"Receipt required for expenses above ${threshold:.2f} "
                f"(expense: ${amount:.2f})",
                severity=severity,
            )]
        return []

    def _check_max_amount(self, expense_data: dict) -> List[PolicyViolation]:
        """Check single expense maximum."""
        amount = expense_data.get("amount", 0)
        max_amount = 5000.0

        if amount > max_amount:
            return [PolicyViolation(
                "Maximum Expense Limit",
                f"Expense ${amount:.2f} exceeds maximum single expense "
                f"limit of ${max_amount:.2f}",
                severity="block",
            )]
        return []

    def _check_category_limit(self, expense_data: dict) -> List[PolicyViolation]:
        """Check category-specific limits."""
        category = expense_data.get("category", "")
        amount = expense_data.get("amount", 0)

        category_limits = {
            "meals": 100.0,
            "transportation": 150.0,
            "office_supplies": 500.0,
            "client_entertainment": 300.0,
        }

        limit = category_limits.get(category)
        if limit and amount > limit:
            return [PolicyViolation(
                f"{category.title()} Category Limit",
                f"${amount:.2f} exceeds {category} limit of ${limit:.2f}",
                severity="warning" if amount < limit * 1.5 else "block",
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

            monthly_limit = employee.monthly_limit if employee else 5000.0

            # Calculate current month's total
            month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
            monthly_total = self.db.query(func.sum(ExpenseDB.amount)).filter(
                ExpenseDB.employee_id == employee_id,
                ExpenseDB.submitted_at >= month_start,
                ExpenseDB.status.notin_(["rejected", "flagged"]),
            ).scalar() or 0.0

            new_total = monthly_total + expense_data.get("amount", 0)

            if new_total > monthly_limit:
                return [PolicyViolation(
                    "Monthly Spending Limit",
                    f"Monthly total ${new_total:.2f} would exceed limit of "
                    f"${monthly_limit:.2f} (already spent: ${monthly_total:.2f})",
                    severity="block",
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
            # Look for same amount, category within last 24h
            yesterday = datetime.utcnow() - timedelta(hours=24)
            duplicates = self.db.query(ExpenseDB).filter(
                ExpenseDB.employee_id == employee_id,
                ExpenseDB.amount == expense_data.get("amount"),
                ExpenseDB.category == expense_data.get("category"),
                ExpenseDB.submitted_at >= yesterday,
            ).count()

            if duplicates > 0:
                return [PolicyViolation(
                    "Potential Duplicate",
                    f"Found {duplicates} similar expense(s) in last 24 hours "
                    f"(same amount and category)",
                    severity="flag",
                )]
        except Exception as e:
            logger.warning(f"Duplicate check failed: {e}")

        return []

