"""Pydantic models for expense data validation and serialization."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExpenseCreate(BaseModel):
    """Schema for creating a new expense."""
    employee_id: str = Field(..., description="Employee ID submitting the expense")
    amount: float = Field(..., gt=0, description="Expense amount in USD")
    category: str = Field(..., description="Expense category")
    merchant: Optional[str] = Field(None, description="Merchant/vendor name")
    description: Optional[str] = Field(None, description="Expense description")
    receipt_attached: bool = Field(False, description="Whether a receipt is attached")


class RiskAssessment(BaseModel):
    """AI risk assessment result."""
    risk_score: float = Field(..., ge=0, le=1, description="Risk score 0-1")
    anomaly_score: float = Field(..., ge=0, le=1, description="Anomaly score 0-1")
    predicted_category: str = Field(..., description="ML-predicted category")
    risk_factors: List[str] = Field(default_factory=list, description="List of risk factors")
    decision: str = Field(..., description="auto_approved, manager_review, or rejected")
    decision_reason: str = Field(..., description="Human-readable decision reason")


class ExpenseResponse(BaseModel):
    """Full expense response with AI scoring."""
    id: int
    expense_id: str
    employee_id: str
    amount: float
    currency: str
    category: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    receipt_attached: bool

    # AI Scoring
    risk_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    ai_category: Optional[str] = None
    risk_factors: Optional[str] = None

    # Approval
    status: str
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None

    # Blockchain
    tx_hash: Optional[str] = None
    memo: Optional[str] = None
    stellar_tx_url: Optional[str] = None

    # Timestamps
    submitted_at: datetime
    processed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseListResponse(BaseModel):
    """Paginated list of expenses."""
    total: int
    expenses: List[ExpenseResponse]


class ExpenseStats(BaseModel):
    """Dashboard statistics."""
    total_expenses: int
    total_amount: float
    auto_approved: int
    manager_review: int
    rejected: int
    flagged: int
    paid: int
    avg_risk_score: float
    total_saved_time_hours: float  # estimated time saved

