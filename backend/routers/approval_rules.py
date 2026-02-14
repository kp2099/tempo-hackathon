"""
Approval Rules & Org Hierarchy API endpoints.
Manage configurable approval routing rules and view org structure.
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from datetime import datetime

from database import get_db, ApprovalRuleDB, EmployeeDB
from models.employee import ApprovalRuleCreate, ApprovalRuleResponse, OrgNode

router = APIRouter()


# ─── Approval Rules CRUD ──────────────────────────────────────────

@router.get("/rules")
async def list_approval_rules(
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
):
    """List all approval routing rules."""
    query = db.query(ApprovalRuleDB)
    if active_only:
        query = query.filter(ApprovalRuleDB.active == True)
    rules = query.order_by(ApprovalRuleDB.priority).all()

    return {
        "total": len(rules),
        "rules": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "category": r.category,
                "department": r.department,
                "amount_min": r.amount_min,
                "amount_max": r.amount_max,
                "required_approvers": json.loads(r.required_approvers) if r.required_approvers else [],
                "approval_type": r.approval_type,
                "priority": r.priority,
                "active": r.active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rules
        ],
    }


@router.post("/rules")
async def create_approval_rule(rule: ApprovalRuleCreate, db: Session = Depends(get_db)):
    """Create a new approval routing rule."""
    db_rule = ApprovalRuleDB(
        name=rule.name,
        description=rule.description,
        category=rule.category,
        department=rule.department,
        amount_min=rule.amount_min,
        amount_max=rule.amount_max,
        required_approvers=json.dumps(rule.required_approvers),
        approval_type=rule.approval_type,
        priority=rule.priority,
        active=rule.active,
    )
    db.add(db_rule)
    db.commit()
    db.refresh(db_rule)

    return {
        "id": db_rule.id,
        "name": db_rule.name,
        "description": db_rule.description,
        "category": db_rule.category,
        "department": db_rule.department,
        "amount_min": db_rule.amount_min,
        "amount_max": db_rule.amount_max,
        "required_approvers": json.loads(db_rule.required_approvers),
        "approval_type": db_rule.approval_type,
        "priority": db_rule.priority,
        "active": db_rule.active,
        "message": "Approval rule created",
    }


@router.put("/rules/{rule_id}")
async def update_approval_rule(
    rule_id: int,
    rule: ApprovalRuleCreate,
    db: Session = Depends(get_db),
):
    """Update an existing approval rule."""
    db_rule = db.query(ApprovalRuleDB).filter(ApprovalRuleDB.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db_rule.name = rule.name
    db_rule.description = rule.description
    db_rule.category = rule.category
    db_rule.department = rule.department
    db_rule.amount_min = rule.amount_min
    db_rule.amount_max = rule.amount_max
    db_rule.required_approvers = json.dumps(rule.required_approvers)
    db_rule.approval_type = rule.approval_type
    db_rule.priority = rule.priority
    db_rule.active = rule.active

    db.commit()
    return {"message": "Rule updated", "id": rule_id}


@router.delete("/rules/{rule_id}")
async def delete_approval_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete an approval rule."""
    db_rule = db.query(ApprovalRuleDB).filter(ApprovalRuleDB.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(db_rule)
    db.commit()
    return {"message": "Rule deleted", "id": rule_id}


@router.patch("/rules/{rule_id}/toggle")
async def toggle_approval_rule(rule_id: int, db: Session = Depends(get_db)):
    """Toggle a rule active/inactive."""
    db_rule = db.query(ApprovalRuleDB).filter(ApprovalRuleDB.id == rule_id).first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db_rule.active = not db_rule.active
    db.commit()
    return {"message": f"Rule {'activated' if db_rule.active else 'deactivated'}", "active": db_rule.active}


# ─── Org Hierarchy ────────────────────────────────────────────────

@router.get("/org-tree")
async def get_org_tree(db: Session = Depends(get_db)):
    """
    Get the full org hierarchy as a tree structure.
    Returns root nodes (employees with no manager) with nested direct_reports.
    """
    employees = db.query(EmployeeDB).all()

    # Build a lookup map
    emp_map = {e.employee_id: e for e in employees}
    children_map: dict = {}
    roots = []

    for e in employees:
        if e.reports_to and e.reports_to in emp_map:
            children_map.setdefault(e.reports_to, []).append(e)
        else:
            roots.append(e)

    def build_node(emp):
        kids = children_map.get(emp.employee_id, [])
        return {
            "employee_id": emp.employee_id,
            "name": emp.name,
            "department": emp.department,
            "role": emp.role,
            "reports_to": emp.reports_to,
            "direct_reports": [build_node(c) for c in kids],
        }

    return {"org_tree": [build_node(r) for r in roots]}


@router.get("/org-flat")
async def get_org_flat(db: Session = Depends(get_db)):
    """Get all employees in a flat list with hierarchy info."""
    employees = db.query(EmployeeDB).all()
    emp_map = {e.employee_id: e for e in employees}

    result = []
    for e in employees:
        manager_name = None
        if e.reports_to and e.reports_to in emp_map:
            manager_name = emp_map[e.reports_to].name

        result.append({
            "employee_id": e.employee_id,
            "name": e.name,
            "email": e.email,
            "department": e.department,
            "role": e.role,
            "reports_to": e.reports_to,
            "manager_name": manager_name,
            "tempo_wallet": e.tempo_wallet,
        })

    return {"employees": result}
