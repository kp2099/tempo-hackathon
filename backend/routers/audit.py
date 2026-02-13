"""Audit trail API endpoints - On-chain transparency."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database import get_db, AuditLogDB

router = APIRouter()


@router.get("/")
async def get_audit_trail(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    expense_id: str = Query(None),
    actor: str = Query(None),
    db: Session = Depends(get_db),
):
    """
    Get the full audit trail.
    Every AI decision and payment is logged here for transparency.
    """
    query = db.query(AuditLogDB)

    if expense_id:
        query = query.filter(AuditLogDB.expense_id == expense_id)
    if actor:
        query = query.filter(AuditLogDB.actor == actor)

    total = query.count()
    logs = query.order_by(desc(AuditLogDB.timestamp)).offset(skip).limit(limit).all()

    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "expense_id": log.expense_id,
                "action": log.action,
                "actor": log.actor,
                "details": log.details,
                "risk_score": log.risk_score,
                "tx_hash": log.tx_hash,
                "memo": log.memo,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "stellar_url": (
                    f"https://stellar.expert/explorer/testnet/tx/{log.tx_hash}"
                    if log.tx_hash else None
                ),
            }
            for log in logs
        ],
    }


@router.get("/stats")
async def get_audit_stats(db: Session = Depends(get_db)):
    """Get audit trail statistics."""
    total = db.query(AuditLogDB).count()
    agent_actions = db.query(AuditLogDB).filter(AuditLogDB.actor == "AgentFin").count()
    manager_actions = db.query(AuditLogDB).filter(AuditLogDB.actor == "Manager").count()
    on_chain = db.query(AuditLogDB).filter(AuditLogDB.tx_hash.isnot(None)).count()

    return {
        "total_actions": total,
        "agent_actions": agent_actions,
        "manager_actions": manager_actions,
        "on_chain_records": on_chain,
        "transparency_rate": round(on_chain / max(total, 1) * 100, 1),
    }

