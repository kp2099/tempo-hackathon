"""
Approval Routing Service — resolves approval chains based on configurable rules.

Given an expense + employee, this service:
1. Finds all matching ApprovalRules (category, department, amount)
2. Picks the highest-priority rule
3. Resolves each approver role to a real employee (walking the org hierarchy)
4. Creates ApprovalStep rows for the expense

Approver role resolution:
  - "direct_manager"   → employee.reports_to
  - "department_head"  → walk up reports_to until role == "vp" or "director"
  - "finance"          → any employee with role == "finance" in finance dept
  - "vp"               → walk up to role == "vp"
  - "cfo"              → employee with role == "cfo"
"""

import json
import logging
from typing import List, Optional, Dict
from datetime import datetime
from sqlalchemy.orm import Session

from database import EmployeeDB, ApprovalRuleDB, ApprovalStepDB, AuditLogDB

logger = logging.getLogger("TempoExpenseAI.ApprovalRouting")


class ApprovalRoutingService:
    """Matches expenses to approval rules and builds the approval chain."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve_approval_chain(
        self,
        expense_id: str,
        employee_id: str,
        category: str,
        department: str,
        amount: float,
    ) -> List[dict]:
        """
        Find the best matching rule and create approval steps.

        Returns list of created step dicts (empty if no rule matched,
        meaning single-tier AI approval is sufficient).
        """
        rule = self._find_matching_rule(category, department, amount)
        if not rule:
            logger.info(f"   No approval rule matched for {expense_id} — AI-only approval")
            return []

        approver_roles: List[str] = json.loads(rule.required_approvers)
        logger.info(
            f"   Rule matched: '{rule.name}' (priority {rule.priority}) "
            f"→ approvers: {approver_roles}"
        )

        steps_created = []
        for idx, role in enumerate(approver_roles, start=1):
            resolved = self._resolve_approver(role, employee_id, department)
            step = ApprovalStepDB(
                expense_id=expense_id,
                step_order=idx,
                approver_role=role,
                approver_id=resolved.get("employee_id"),
                approver_name=resolved.get("name"),
                status="pending" if idx == 1 else "waiting",
                created_at=datetime.utcnow(),
            )
            self.db.add(step)
            steps_created.append({
                "step_order": idx,
                "approver_role": role,
                "approver_id": resolved.get("employee_id"),
                "approver_name": resolved.get("name"),
                "status": step.status,
            })

        # Audit log
        audit = AuditLogDB(
            expense_id=expense_id,
            action="approval_chain_created",
            actor="AgentFin",
            details=json.dumps({
                "rule": rule.name,
                "rule_id": rule.id,
                "steps": steps_created,
            }),
        )
        self.db.add(audit)

        return steps_created

    def get_pending_for_approver(self, approver_id: str) -> List[ApprovalStepDB]:
        """Get all approval steps that are pending for a given approver."""
        return (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.approver_id == approver_id,
                ApprovalStepDB.status == "pending",
            )
            .all()
        )

    def approve_step(
        self,
        expense_id: str,
        approver_id: str,
        comments: Optional[str] = None,
    ) -> dict:
        """
        Approve the current pending step for this expense by the given approver.
        Advances to the next step or marks expense as fully approved.

        Returns dict with action taken.
        """
        step = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.approver_id == approver_id,
                ApprovalStepDB.status == "pending",
            )
            .first()
        )
        if not step:
            return {"error": "No pending approval step found for this approver"}

        step.status = "approved"
        step.comments = comments
        step.acted_at = datetime.utcnow()

        # Audit
        audit = AuditLogDB(
            expense_id=expense_id,
            action=f"step_{step.step_order}_approved",
            actor=step.approver_name or approver_id,
            details=json.dumps({
                "step_order": step.step_order,
                "approver_role": step.approver_role,
                "comments": comments,
            }),
        )
        self.db.add(audit)

        # Check if there's a next step to activate
        next_step = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.step_order == step.step_order + 1,
            )
            .first()
        )

        if next_step:
            next_step.status = "pending"
            # Audit for next step activation
            audit2 = AuditLogDB(
                expense_id=expense_id,
                action="approval_pending",
                actor="System",
                details=json.dumps({
                    "step_order": next_step.step_order,
                    "approver_role": next_step.approver_role,
                    "approver": next_step.approver_name or next_step.approver_id,
                }),
            )
            self.db.add(audit2)
            return {
                "action": "next_step_activated",
                "current_step": next_step.step_order,
                "total_steps": self._count_steps(expense_id),
                "next_approver": next_step.approver_name,
                "next_role": next_step.approver_role,
                "fully_approved": False,
            }
        else:
            # All steps complete!
            return {
                "action": "fully_approved",
                "current_step": step.step_order,
                "total_steps": step.step_order,
                "fully_approved": True,
            }

    def reject_step(
        self,
        expense_id: str,
        approver_id: str,
        comments: Optional[str] = None,
    ) -> dict:
        """Reject at any step — stops the chain immediately."""
        step = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.approver_id == approver_id,
                ApprovalStepDB.status == "pending",
            )
            .first()
        )
        if not step:
            return {"error": "No pending approval step found for this approver"}

        step.status = "rejected"
        step.comments = comments
        step.acted_at = datetime.utcnow()

        # Mark all subsequent steps as skipped
        remaining = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.step_order > step.step_order,
            )
            .all()
        )
        for s in remaining:
            s.status = "skipped"

        audit = AuditLogDB(
            expense_id=expense_id,
            action=f"step_{step.step_order}_rejected",
            actor=step.approver_name or approver_id,
            details=json.dumps({
                "step_order": step.step_order,
                "approver_role": step.approver_role,
                "comments": comments,
            }),
        )
        self.db.add(audit)

        return {"action": "rejected", "rejected_by": step.approver_name or approver_id}

    def escalate_step(
        self,
        expense_id: str,
        approver_id: str,
        comments: Optional[str] = None,
    ) -> dict:
        """
        Escalate: current approver passes it up their own chain.
        Inserts a new step before the remaining steps.
        """
        step = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.approver_id == approver_id,
                ApprovalStepDB.status == "pending",
            )
            .first()
        )
        if not step:
            return {"error": "No pending approval step found for this approver"}

        # Mark current step as escalated
        step.status = "escalated"
        step.comments = comments or "Escalated to higher authority"
        step.acted_at = datetime.utcnow()

        # Find who the approver reports to
        approver_emp = self.db.query(EmployeeDB).filter(
            EmployeeDB.employee_id == approver_id
        ).first()
        escalation_target_id = approver_emp.reports_to if approver_emp else None

        if not escalation_target_id:
            return {"error": "Cannot escalate — approver has no manager in hierarchy"}

        escalation_target = self.db.query(EmployeeDB).filter(
            EmployeeDB.employee_id == escalation_target_id
        ).first()

        # Bump step_order of all subsequent steps
        remaining = (
            self.db.query(ApprovalStepDB)
            .filter(
                ApprovalStepDB.expense_id == expense_id,
                ApprovalStepDB.step_order > step.step_order,
            )
            .all()
        )
        for s in remaining:
            s.step_order += 1

        # Insert new step right after the escalated one
        new_step = ApprovalStepDB(
            expense_id=expense_id,
            step_order=step.step_order + 1,
            approver_role="escalated_manager",
            approver_id=escalation_target_id,
            approver_name=escalation_target.name if escalation_target else None,
            status="pending",
            created_at=datetime.utcnow(),
        )
        self.db.add(new_step)

        # Audit
        audit = AuditLogDB(
            expense_id=expense_id,
            action="step_escalated",
            actor=step.approver_name or approver_id,
            details=json.dumps({
                "escalated_from": step.approver_name or approver_id,
                "escalated_to": escalation_target.name if escalation_target else escalation_target_id,
                "reason": comments,
            }),
        )
        self.db.add(audit)

        return {
            "action": "escalated",
            "escalated_from": step.approver_name or approver_id,
            "escalated_to": escalation_target.name if escalation_target else escalation_target_id,
            "new_step_order": new_step.step_order,
            "total_steps": self._count_steps(expense_id) + 1,  # +1 for the new step
        }

    def get_steps_for_expense(self, expense_id: str) -> List[ApprovalStepDB]:
        """Get all approval steps for an expense, ordered."""
        return (
            self.db.query(ApprovalStepDB)
            .filter(ApprovalStepDB.expense_id == expense_id)
            .order_by(ApprovalStepDB.step_order)
            .all()
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _find_matching_rule(
        self, category: str, department: str, amount: float
    ) -> Optional[ApprovalRuleDB]:
        """Find the highest-priority active rule that matches."""
        rules = (
            self.db.query(ApprovalRuleDB)
            .filter(ApprovalRuleDB.active == True)
            .order_by(ApprovalRuleDB.priority)
            .all()
        )

        for rule in rules:
            if rule.category and rule.category != category:
                continue
            if rule.department and rule.department != department:
                continue
            if rule.amount_min is not None and amount < rule.amount_min:
                continue
            if rule.amount_max is not None and amount > rule.amount_max:
                continue
            return rule

        return None

    def _resolve_approver(
        self, role: str, employee_id: str, department: str
    ) -> Dict[str, Optional[str]]:
        """Resolve an approver role to a real employee."""
        employee = self.db.query(EmployeeDB).filter(
            EmployeeDB.employee_id == employee_id
        ).first()

        if role == "direct_manager":
            if employee and employee.reports_to:
                mgr = self.db.query(EmployeeDB).filter(
                    EmployeeDB.employee_id == employee.reports_to
                ).first()
                if mgr:
                    return {"employee_id": mgr.employee_id, "name": mgr.name}
            return {"employee_id": None, "name": "Unassigned Manager"}

        elif role == "department_head":
            return self._walk_up_to_role(employee, ["vp", "director", "department_head"])

        elif role == "finance":
            fin = self.db.query(EmployeeDB).filter(
                EmployeeDB.role == "finance"
            ).first()
            if fin:
                return {"employee_id": fin.employee_id, "name": fin.name}
            return {"employee_id": None, "name": "Finance Team"}

        elif role == "vp":
            return self._walk_up_to_role(employee, ["vp"])

        elif role == "cfo":
            cfo = self.db.query(EmployeeDB).filter(
                EmployeeDB.role == "cfo"
            ).first()
            if cfo:
                return {"employee_id": cfo.employee_id, "name": cfo.name}
            return {"employee_id": None, "name": "CFO"}

        # Fallback: try to find by role string directly
        emp = self.db.query(EmployeeDB).filter(
            EmployeeDB.role == role
        ).first()
        if emp:
            return {"employee_id": emp.employee_id, "name": emp.name}

        return {"employee_id": None, "name": f"Unresolved ({role})"}

    def _walk_up_to_role(
        self, employee: Optional[EmployeeDB], target_roles: List[str], max_depth: int = 5
    ) -> Dict[str, Optional[str]]:
        """Walk up the org hierarchy until we find someone with one of the target roles."""
        current = employee
        for _ in range(max_depth):
            if not current or not current.reports_to:
                break
            mgr = self.db.query(EmployeeDB).filter(
                EmployeeDB.employee_id == current.reports_to
            ).first()
            if not mgr:
                break
            if mgr.role in target_roles:
                return {"employee_id": mgr.employee_id, "name": mgr.name}
            current = mgr
        return {"employee_id": None, "name": f"Unresolved ({'/'.join(target_roles)})"}

    def _count_steps(self, expense_id: str) -> int:
        return (
            self.db.query(ApprovalStepDB)
            .filter(ApprovalStepDB.expense_id == expense_id)
            .count()
        )
