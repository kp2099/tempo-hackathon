"""Pydantic models for employee data validation and serialization."""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EmployeeCreate(BaseModel):
    """Schema for creating a new employee."""
    employee_id: str = Field(..., description="Unique employee identifier")
    name: str = Field(..., description="Full name")
    email: str = Field(..., description="Email address")
    department: str = Field(..., description="Department name")
    role: str = Field("employee", description="Role: employee, manager, finance")
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
