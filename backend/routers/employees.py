"""Employee management API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime

from database import get_db, EmployeeDB, ExpenseDB
from models.employee import EmployeeCreate, EmployeeResponse, EmployeeSpendingSummary
from services.tempo_client import get_tempo_client

router = APIRouter()


@router.post("/", response_model=EmployeeResponse)
async def create_employee(employee: EmployeeCreate, db: Session = Depends(get_db)):
    """Create a new employee with a Tempo wallet address."""
    existing = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == employee.employee_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Employee ID already exists")

    db_employee = EmployeeDB(
        employee_id=employee.employee_id,
        name=employee.name,
        email=employee.email,
        department=employee.department,
        role=employee.role,
        tempo_wallet=employee.tempo_wallet,
        monthly_limit=employee.monthly_limit,
    )

    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)

    return db_employee


@router.get("/", response_model=list[EmployeeResponse])
async def list_employees(db: Session = Depends(get_db)):
    """List all employees."""
    return db.query(EmployeeDB).all()


@router.get("/{employee_id}", response_model=EmployeeResponse)
async def get_employee(employee_id: str, db: Session = Depends(get_db)):
    """Get a single employee."""
    employee = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


@router.get("/{employee_id}/spending")
async def get_spending_summary(employee_id: str, db: Session = Depends(get_db)):
    """Get employee spending analytics."""
    employee = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    expenses = db.query(ExpenseDB).filter(
        ExpenseDB.employee_id == employee_id
    ).all()

    total_amount = sum(e.amount for e in expenses)
    avg_amount = total_amount / len(expenses) if expenses else 0
    avg_risk = (
        sum(e.risk_score for e in expenses if e.risk_score is not None)
        / max(len([e for e in expenses if e.risk_score is not None]), 1)
    )
    flagged = sum(1 for e in expenses if e.status in ["flagged", "rejected"])

    # Monthly remaining
    now = datetime.utcnow()
    monthly_spent = sum(
        e.amount for e in expenses
        if e.submitted_at and e.submitted_at.month == now.month
        and e.status not in ["rejected", "flagged"]
    )

    return {
        "employee_id": employee.employee_id,
        "name": employee.name,
        "department": employee.department,
        "total_expenses": len(expenses),
        "total_amount": round(total_amount, 2),
        "avg_expense_amount": round(avg_amount, 2),
        "avg_risk_score": round(avg_risk, 4),
        "flagged_count": flagged,
        "monthly_limit": employee.monthly_limit,
        "monthly_spent": round(monthly_spent, 2),
        "monthly_remaining": round(employee.monthly_limit - monthly_spent, 2),
        "wallet": employee.tempo_wallet,
    }


@router.get("/{employee_id}/wallet")
async def get_wallet_info(employee_id: str, db: Session = Depends(get_db)):
    """Get employee's Tempo wallet info and AlphaUSD balance."""
    employee = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")

    tempo_client = get_tempo_client()
    balance = tempo_client.get_balance(employee.tempo_wallet or "")

    return {
        "employee_id": employee.employee_id,
        "name": employee.name,
        "wallet_address": employee.tempo_wallet,
        "balance": balance,
        "network": "Tempo Testnet (Moderato)",
        "explorer": f"{tempo_client.w3 and 'https://explore.tempo.xyz/address/' + (employee.tempo_wallet or '')}",
    }
