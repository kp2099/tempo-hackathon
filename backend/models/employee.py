"""Pydantic models for employee data validation and serialization."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee."""
    employee_id: str = Field(..., description="Unique employee identifier")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    department: str = Field(..., description="Department name")
    role: str = Field("employee", description="Role: employee, manager, finance, vp, cfo")
    reports_to: Optional[str] = Field(None, description="Employee ID of direct manager")
    tempo_wallet: Optional[str] = Field(None, description="Tempo wallet address (0x...)")
    monthly_limit: float = Field(5000.0, description="Monthly spending limit in USD")


class EmployeeResponse(BaseModel):
    """Employee response schema."""
    id: int
    employee_id: str
    name: str
    email: str
    department: str
    role: str
    reports_to: Optional[str] = None
    tempo_wallet: Optional[str] = None
    monthly_limit: float
    created_at: datetime

    class Config:
        from_attributes = True


class EmployeeSpendingSummary(BaseModel):
    """Employee spending analytics."""
    employee_id: str
    name: str
    department: str
    total_expenses: int
    total_amount: float
    avg_expense_amount: float
    avg_risk_score: float
    flagged_count: int
    monthly_remaining: float


class OrgNode(BaseModel):
    """A node in the org hierarchy tree."""
    employee_id: str
    name: str
    department: str
    role: str
    reports_to: Optional[str] = None
    direct_reports: List["OrgNode"] = []

    class Config:
        from_attributes = True


# --- Approval Rule schemas ---

class ApprovalRuleCreate(BaseModel):
    """Schema for creating an approval routing rule."""
    name: str = Field(..., description="Rule name")
    description: Optional[str] = Field(None, description="Rule description")
    category: Optional[str] = Field(None, description="Expense category to match (None = any)")
    department: Optional[str] = Field(None, description="Employee department to match (None = any)")
    amount_min: Optional[float] = Field(None, description="Minimum amount to trigger")
    amount_max: Optional[float] = Field(None, description="Maximum amount (None = no upper)")
    required_approvers: List[str] = Field(..., description="Ordered list of approver roles")
    approval_type: str = Field("sequential", description="sequential or parallel")
    priority: int = Field(100, description="Rule priority (lower = higher priority)")
    active: bool = Field(True)


class ApprovalRuleResponse(BaseModel):
    """Approval rule response schema."""
    id: int
    name: str
    description: Optional[str] = None
    category: Optional[str] = None
    department: Optional[str] = None
    amount_min: Optional[float] = None
    amount_max: Optional[float] = None
    required_approvers: List[str] = []
    approval_type: str
    priority: int
    active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalStepResponse(BaseModel):
    """Single approval step in the chain."""
    id: int
    expense_id: str
    step_order: int
    approver_role: str
    approver_id: Optional[str] = None
    approver_name: Optional[str] = None
    status: str
    comments: Optional[str] = None
    acted_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
