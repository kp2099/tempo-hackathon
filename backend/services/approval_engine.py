"""
Approval Engine - The AI Agent's decision-making core.
Combines ML risk scoring, anomaly detection, and policy checks
to make autonomous approval decisions.

Memos are encoded as bytes32 for Tempo's TIP-20 transferWithMemo().
"""

import logging
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session

from ml.risk_scorer import get_risk_scorer
from ml.anomaly_detector import get_anomaly_detector
from ml.categorizer import get_categorizer
from services.policy_engine import PolicyEngine
from config import settings

logger = logging.getLogger("TempoExpenseAI.ApprovalEngine")


class ApprovalDecision:
    """Represents the AI agent's approval decision."""

    def __init__(
        self,
        decision: str,
        risk_score: float,
        anomaly_score: float,
        predicted_category: str,
        risk_factors: list,
        policy_result: dict,
        reason: str,
        memo: str,
    ):
        self.decision = decision  # auto_approved, manager_review, rejected, flagged
        self.risk_score = risk_score
        self.anomaly_score = anomaly_score
        self.predicted_category = predicted_category
        self.risk_factors = risk_factors
        self.policy_result = policy_result
        self.reason = reason
        self.memo = memo  # For Tempo blockchain memo (bytes32)
        self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "decision": self.decision,
            "risk_score": self.risk_score,
            "anomaly_score": self.anomaly_score,
            "predicted_category": self.predicted_category,
            "risk_factors": self.risk_factors,
            "policy_result": self.policy_result,
            "reason": self.reason,
            "memo": self.memo,
            "timestamp": self.timestamp.isoformat(),
        }


class ApprovalEngine:
    """
    AgentFin's autonomous decision engine.

    Three-tier decision system:
    🟢 Low Risk (< 0.3)  → AUTO-APPROVE + instant payment on Tempo
    🟡 Medium Risk (0.3-0.7) → MANAGER REVIEW with AI recommendation
    🔴 High Risk (> 0.7) → AUTO-REJECT + flag for investigation
    """

    AGENT_NAME = "AgentFin"

    def __init__(self, db: Optional[Session] = None):
        self.risk_scorer = get_risk_scorer()
        self.anomaly_detector = get_anomaly_detector()
        self.categorizer = get_categorizer()
        self.policy_engine = PolicyEngine(db=db)

    def evaluate(self, expense_data: dict, employee_id: str) -> ApprovalDecision:
        """
        Evaluate an expense and make an autonomous approval decision.

        This is the core AI agent logic.
        """
        logger.info(f"🤖 {self.AGENT_NAME} evaluating expense: "
                     f"${expense_data.get('amount', 0):.2f} "
                     f"({expense_data.get('category', 'unknown')})")

        # Step 1: ML Risk Scoring
        risk_result = self.risk_scorer.predict_risk(expense_data)
        risk_score = risk_result["risk_score"]
        risk_factors = risk_result["risk_factors"]

        # Step 2: Anomaly Detection
        anomaly_result = self.anomaly_detector.detect(expense_data)
        anomaly_score = anomaly_result["anomaly_score"]

        # Step 3: Auto-categorize
        category_result = self.categorizer.predict_category(expense_data)
        predicted_category = category_result["predicted_category"]

        # Step 4: Policy Checks
        policy_result = self.policy_engine.check_all_policies(
            expense_data, employee_id
        )

        # Step 5: MAKE THE DECISION
        decision, reason = self._make_decision(
            risk_score=risk_score,
            anomaly_score=anomaly_score,
            anomaly_detected=anomaly_result["is_anomaly"],
            policy_passed=policy_result["passed"],
            policy_violations=policy_result["violations"],
            amount=expense_data.get("amount", 0),
            risk_factors=risk_factors,
        )

        # Step 6: Build Tempo on-chain memo (bytes32)
        memo = self._build_memo(
            risk_score=risk_score,
            category=expense_data.get("category", predicted_category),
            decision=decision,
            amount=expense_data.get("amount", 0),
        )

        logger.info(f"   Decision: {decision} | Risk: {risk_score:.3f} | "
                     f"Anomaly: {anomaly_score:.3f} | Memo: {memo}")

        return ApprovalDecision(
            decision=decision,
            risk_score=risk_score,
            anomaly_score=anomaly_score,
            predicted_category=predicted_category,
            risk_factors=risk_factors,
            policy_result=policy_result,
            reason=reason,
            memo=memo,
        )

    def _make_decision(
        self,
        risk_score: float,
        anomaly_score: float,
        anomaly_detected: bool,
        policy_passed: bool,
        policy_violations: list,
        amount: float,
        risk_factors: list,
    ) -> tuple:
        """
        Core decision logic.

        Returns (decision, reason) tuple.
        """
        # Hard block: Policy violations that are blocking
        blocking_violations = [v for v in policy_violations if v["severity"] == "block"]
        if blocking_violations:
            reasons = "; ".join([v["message"] for v in blocking_violations])
            return ("rejected", f"Policy violation: {reasons}")

        # High risk → auto-reject
        if risk_score > settings.risk_threshold_auto_reject:
            return (
                "flagged",
                f"High risk score ({risk_score:.2f}). "
                f"Factors: {', '.join(risk_factors[:3]) if risk_factors else 'Multiple signals'}"
            )

        # Anomaly detected → flag for review (only for very strong anomalies)
        if anomaly_detected and anomaly_score > 0.8:
            return (
                "flagged",
                f"Strong anomaly detected (score: {anomaly_score:.2f}). "
                f"Statistical outlier in spending pattern."
            )

        # Medium risk → manager review
        if risk_score > settings.risk_threshold_auto_approve:
            return (
                "manager_review",
                f"Moderate risk ({risk_score:.2f}). "
                f"Recommended for manager review. "
                f"Factors: {', '.join(risk_factors[:2]) if risk_factors else 'Borderline signals'}"
            )

        # Large amount → manager review even if low risk
        if amount > settings.max_auto_approve_amount:
            return (
                "manager_review",
                f"Amount ${amount:.2f} exceeds auto-approve limit "
                f"(${settings.max_auto_approve_amount:.2f}). Low risk ({risk_score:.2f})."
            )

        # Policy warnings (non-blocking) → still approve but note it
        flag_violations = [v for v in policy_violations if v["severity"] == "flag"]
        warning_note = ""
        if flag_violations:
            warning_note = f" Note: {flag_violations[0]['message']}"

        # Low risk → AUTO-APPROVE 🎉
        return (
            "auto_approved",
            f"Low risk ({risk_score:.2f}), all policies passed. "
            f"Auto-approved by {self.AGENT_NAME}.{warning_note}"
        )

    def _build_memo(
        self,
        risk_score: float,
        category: str,
        decision: str,
        amount: float,
    ) -> str:
        """
        Build a programmable memo for the Tempo TIP-20 transferWithMemo().

        Tempo uses bytes32 memos (32 bytes). We pack the key AI decision
        data into a compact format that fits on-chain:
          R=0.10|C=meal|D=appr|$45

        The full human-readable memo is stored in our database for the UI.
        """
        # Compact on-chain memo (≤32 bytes for Tempo bytes32)
        compact = (
            f"R={risk_score:.2f}|"
            f"C={category[:4]}|"
            f"D={decision[:4]}|"
            f"${amount:.0f}"
        )

        # Full memo stored in DB and displayed in UI
        full_memo = (
            f"Risk={risk_score:.2f} | "
            f"Category={category} | "
            f"Decision={decision} | "
            f"Amount=${amount:.2f} | "
            f"Agent={self.AGENT_NAME}"
        )

        return full_memo
