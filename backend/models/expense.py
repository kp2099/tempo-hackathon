"""Pydantic models for expense data validation and serialization."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ExpenseCreate(BaseModel):
    """Schema for submitting a new expense."""
    employee_id: str = Field(..., description="Employee who incurred the expense")
    amount: float = Field(..., gt=0, description="Expense amount in USD")
    category: str = Field(..., description="Expense category")
    merchant: Optional[str] = Field(None, description="Merchant/vendor name")
    description: Optional[str] = Field(None, description="Expense description")
    receipt_attached: bool = Field(False, description="Whether a receipt is attached")
    receipt_file_path: Optional[str] = Field(None, description="Path to uploaded receipt file")


class ApprovalStepInfo(BaseModel):
    """Approval step info embedded in expense response."""
    step_order: int
    approver_role: str
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None
    status: str
    comments: Optional[str] = None
    acted_at: Optional[datetime] = None


class ExpenseResponse(BaseModel):
    """Full expense response with AI scoring and blockchain data."""
    id: int
    expense_id: str
    employee_id: str
    amount: float
    currency: str
    category: str
    merchant: Optional[str] = None
    description: Optional[str] = None
    receipt_attached: bool
    receipt_file_path: Optional[str] = None

    # OCR Data
    ocr_amount: Optional[float] = None
    ocr_merchant: Optional[str] = None
    ocr_date: Optional[str] = None
    ocr_confidence: Optional[float] = None

    # AI Scoring
    risk_score: Optional[float] = None
    anomaly_score: Optional[float] = None
    ai_category: Optional[str] = None
    risk_factors: Optional[str] = None

    # Approval
    status: str
    current_step: Optional[int] = 0
    total_steps: Optional[int] = 0
    approved_by: Optional[str] = None
    approval_reason: Optional[str] = None

    # Tempo Blockchain
    tx_hash: Optional[str] = None
    memo: Optional[str] = None
    tempo_tx_url: Optional[str] = None

    # Timestamps
    submitted_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ExpenseDetailResponse(ExpenseResponse):
    """Extended expense response with approval steps."""
    approval_steps: List[ApprovalStepInfo] = []


class ExpenseListResponse(BaseModel):
    """Paginated expense list."""
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
    pending_approval: int
    avg_risk_score: float
    total_saved_time_hours: float
