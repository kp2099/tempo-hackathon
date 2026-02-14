"""SQLAlchemy database setup and table definitions."""

from sqlalchemy import (
    create_engine, Column, Integer, Float, String, DateTime, Boolean, Text, Enum,
    ForeignKey, JSON
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

from config import settings

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# --- Enums ---

class ExpenseStatus(str, enum.Enum):
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    MANAGER_REVIEW = "manager_review"
    PENDING_APPROVAL = "pending_approval"  # Multi-step: waiting on next approver
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"
    DISPUTED = "disputed"
    ESCALATED = "escalated"
    PAID = "paid"


class ExpenseCategory(str, enum.Enum):
    MEALS = "meals"
    TRAVEL = "travel"
    ACCOMMODATION = "accommodation"
    OFFICE_SUPPLIES = "office_supplies"
    SOFTWARE = "software"
    EQUIPMENT = "equipment"
    TRAINING = "training"
    CLIENT_ENTERTAINMENT = "client_entertainment"
    TRANSPORTATION = "transportation"
    MISCELLANEOUS = "miscellaneous"


# --- DB Models ---

class EmployeeDB(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    department = Column(String(50), nullable=False)
    role = Column(String(50), default="employee")
    reports_to = Column(String(50), nullable=True)  # employee_id of direct manager
    tempo_wallet = Column(String(42), nullable=True)  # Tempo EVM address (0x...)
    monthly_limit = Column(Float, default=10000.0)
    created_at = Column(DateTime, default=datetime.utcnow)


class ExpenseDB(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(String(50), unique=True, index=True, nullable=False)
    employee_id = Column(String(50), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    category = Column(String(30), nullable=False)
    merchant = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    receipt_attached = Column(Boolean, default=False)
    receipt_file_path = Column(String(300), nullable=True)  # Path to uploaded receipt

    # OCR Data (extracted from receipt image)
    ocr_amount = Column(Float, nullable=True)
    ocr_merchant = Column(String(100), nullable=True)
    ocr_date = Column(String(20), nullable=True)
    ocr_confidence = Column(Float, nullable=True)
    ocr_raw_text = Column(Text, nullable=True)
    ocr_data = Column(Text, nullable=True)  # Full OCR result as JSON

    # AI Scoring
    risk_score = Column(Float, nullable=True)
    anomaly_score = Column(Float, nullable=True)
    ai_category = Column(String(30), nullable=True)  # ML-predicted category
    risk_factors = Column(Text, nullable=True)  # JSON string of risk factors

    # Approval
    status = Column(String(20), default=ExpenseStatus.PENDING)
    current_step = Column(Integer, default=0)  # Current approval step (0 = not started)
    total_steps = Column(Integer, default=0)   # Total approval steps required
    approved_by = Column(String(50), nullable=True)  # "AgentFin" or manager name
    approval_reason = Column(Text, nullable=True)

    # Tempo Blockchain
    tx_hash = Column(String(100), nullable=True)  # Tempo transaction hash (0x...)
    memo = Column(Text, nullable=True)  # On-chain memo content
    tempo_tx_url = Column(String(200), nullable=True)  # explore.tempo.xyz link

    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    paid_at = Column(DateTime, nullable=True)


class AuditLogDB(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(String(50), nullable=False, index=True)
    action = Column(String(50), nullable=False)
    actor = Column(String(50), nullable=False)  # "AgentFin", employee name, manager
    details = Column(Text, nullable=True)
    risk_score = Column(Float, nullable=True)
    tx_hash = Column(String(100), nullable=True)
    memo = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)


class PolicyDB(Base):
    __tablename__ = "policies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(30), nullable=True)
    max_amount = Column(Float, nullable=True)
    requires_receipt_above = Column(Float, default=25.0)
    monthly_limit = Column(Float, nullable=True)
    department = Column(String(50), nullable=True)  # None = applies to all
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApprovalRuleDB(Base):
    """
    Configurable approval routing rules.
    Determines which approvers are required for a given expense based on
    category, department, and amount thresholds.
    """
    __tablename__ = "approval_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)

    # Match criteria (None / "*" = match all)
    category = Column(String(30), nullable=True)       # e.g. "travel", "client_entertainment", None=any
    department = Column(String(50), nullable=True)      # e.g. "sales", "engineering", None=any
    amount_min = Column(Float, nullable=True)           # Minimum amount to trigger rule
    amount_max = Column(Float, nullable=True)           # Maximum amount (None = no upper bound)

    # Approval chain — JSON list of approver roles in order
    # e.g. ["direct_manager", "finance"] or ["direct_manager", "department_head"]
    # Valid roles: direct_manager, department_head, finance, vp, cfo
    required_approvers = Column(Text, nullable=False)   # JSON array of role strings

    # sequential = step 1 must approve before step 2 sees it
    approval_type = Column(String(20), default="sequential")  # "sequential" or "parallel"

    priority = Column(Integer, default=100)  # Lower number = higher priority (first match wins)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ApprovalStepDB(Base):
    """
    Individual approval steps for an expense.
    Tracks the state of each approver in the multi-step approval chain.
    """
    __tablename__ = "approval_steps"

    id = Column(Integer, primary_key=True, index=True)
    expense_id = Column(String(50), nullable=False, index=True)
    step_order = Column(Integer, nullable=False)       # 1, 2, 3...
    approver_role = Column(String(50), nullable=False)  # "direct_manager", "finance", etc.
    approver_id = Column(String(50), nullable=True)     # Resolved employee_id of the approver
    approver_name = Column(String(100), nullable=True)  # Display name
    status = Column(String(20), default="pending")      # pending, approved, rejected, escalated, skipped
    comments = Column(Text, nullable=True)
    acted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Dependency for FastAPI - yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
