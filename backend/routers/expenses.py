"""
Expense API endpoints.
Handles submission, AI processing, approval, and payment execution on Tempo.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from datetime import datetime
from typing import Optional
import uuid
import json
import os
import logging

from database import get_db, ExpenseDB, AuditLogDB, EmployeeDB
from models.expense import ExpenseCreate, ExpenseResponse, ExpenseListResponse, ExpenseStats
from services.approval_engine import ApprovalEngine
from services.tempo_client import get_tempo_client
from services.nl_parser import parse_natural_language
from services.risk_explainer import explain_risk
from services.ocr_service import extract_receipt_data, compute_ocr_features

logger = logging.getLogger("TempoExpenseAI.ExpensesRouter")

router = APIRouter()


class NLParseRequest(BaseModel):
    """Request body for natural language parsing."""
    text: str


class DisputeRequest(BaseModel):
    """Request body for disputing a rejected/flagged expense."""
    reason: str


def _build_expense_features(expense: ExpenseCreate, db: Session, ocr_features: dict = None) -> dict:
    """Build the full feature dict needed by the ML models."""
    now = datetime.utcnow()

    # Get employee's historical data for behavioral features
    # IMPORTANT: Exclude rejected/flagged expenses so they don't skew averages
    employee_expenses = db.query(ExpenseDB).filter(
        ExpenseDB.employee_id == expense.employee_id,
        ExpenseDB.status.notin_(["rejected", "flagged"]),
    ).all()

    monthly_expenses = [
        e for e in employee_expenses
        if e.submitted_at and e.submitted_at.month == now.month
    ]

    monthly_count = len(monthly_expenses)
    monthly_total = sum(e.amount for e in monthly_expenses)
    avg_amount = (monthly_total / monthly_count) if monthly_count > 0 else expense.amount

    # Category frequency
    cat_count = sum(1 for e in employee_expenses if e.category == expense.category)
    cat_freq = cat_count / max(len(employee_expenses), 1)

    # Merchant frequency
    merch_count = sum(1 for e in employee_expenses if e.merchant == expense.merchant)
    merch_freq = merch_count / max(len(employee_expenses), 1)

    # Days since last expense
    if employee_expenses:
        last_expense = max(e.submitted_at for e in employee_expenses if e.submitted_at)
        days_since = (now - last_expense).days
    else:
        days_since = 30

    features = {
        "amount": expense.amount,
        "category": expense.category,
        "merchant": expense.merchant or "Unknown",
        "description": expense.description or "",
        "receipt_attached": expense.receipt_attached,
        "hour_of_day": now.hour,
        "day_of_week": now.weekday(),
        "is_weekend": 1 if now.weekday() >= 5 else 0,
        "days_since_last_expense": days_since,
        "monthly_expense_count": monthly_count,
        "monthly_total_amount": monthly_total,
        "amount_vs_avg_ratio": round(expense.amount / max(avg_amount, 1), 2),
        "category_frequency": round(cat_freq, 2),
        "merchant_frequency": round(merch_freq, 2),
        "is_round_number": 1 if expense.amount % 10 == 0 else 0,
        "description_length": len(expense.description or ""),
    }

    # Merge OCR-derived features if available
    if ocr_features:
        features.update(ocr_features)

    return features


@router.post("/submit")
async def submit_expense(expense: ExpenseCreate, db: Session = Depends(get_db)):
    """
    Submit a new expense for AI-powered autonomous processing.

    This is the main endpoint that triggers the entire AI agent pipeline:
    1. Feature extraction & behavioral analysis
    2. XGBoost risk scoring
    3. Isolation Forest anomaly detection
    4. Policy compliance checks
    5. Autonomous approval decision
    6. Instant Tempo stablecoin payment (if approved)
    """
    # Verify employee exists
    employee = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == expense.employee_id
    ).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {expense.employee_id} not found")

    # Generate unique expense ID
    expense_id = f"EXP-{uuid.uuid4().hex[:8].upper()}"

    # ─── OCR: Extract data from receipt if uploaded ───
    ocr_result = {}
    ocr_features = {}
    if expense.receipt_file_path:
        # Resolve the absolute path to the uploaded receipt
        # receipt_file_path is like "/uploads/receipts/receipt_xxx.png"
        # UPLOAD_DIR is the absolute path to the uploads/receipts directory
        receipt_filename = os.path.basename(expense.receipt_file_path)
        receipt_abs_path = os.path.join(UPLOAD_DIR, receipt_filename)

        logger.info(f"🧾 Looking for receipt at: {receipt_abs_path} (exists: {os.path.exists(receipt_abs_path)})")

        if os.path.exists(receipt_abs_path):
            try:
                ocr_result = extract_receipt_data(receipt_abs_path)
                ocr_features = compute_ocr_features(
                    ocr_result,
                    {"amount": expense.amount, "merchant": expense.merchant, "category": expense.category},
                )
                logger.info(
                    f"🔍 OCR features for {expense_id}: "
                    f"ocr_success={ocr_features.get('ocr_success')}, "
                    f"ocr_amount={ocr_result.get('ocr_amount')}, "
                    f"amount_mismatch={ocr_features.get('amount_mismatch', 0):.2%}, "
                    f"merchant_mismatch={ocr_features.get('merchant_mismatch', False)}"
                )
            except Exception as e:
                logger.warning(f"⚠️ OCR processing failed for {expense_id}: {e}")
        else:
            logger.warning(f"⚠️ Receipt file not found at {receipt_abs_path}")

    # Build features for ML models (includes OCR features if available)
    features = _build_expense_features(expense, db, ocr_features=ocr_features)

    # Initialize AI approval engine
    approval_engine = ApprovalEngine(db=db)

    # 🤖 AgentFin evaluates the expense
    decision = approval_engine.evaluate(features, expense.employee_id)

    # Generate plain English risk explanation
    risk_explanation = explain_risk(
        expense_data=features,
        risk_score=decision.risk_score,
        anomaly_score=decision.anomaly_score,
        risk_factors=decision.risk_factors,
        decision=decision.decision,
        policy_result=decision.policy_result,
    )

    # Create expense record
    db_expense = ExpenseDB(
        expense_id=expense_id,
        employee_id=expense.employee_id,
        amount=expense.amount,
        currency="USD",
        category=expense.category,
        merchant=expense.merchant,
        description=expense.description,
        receipt_attached=expense.receipt_attached,
        receipt_file_path=expense.receipt_file_path,
        # OCR data
        ocr_amount=ocr_result.get("ocr_amount"),
        ocr_merchant=ocr_result.get("ocr_merchant"),
        ocr_date=ocr_result.get("ocr_date"),
        ocr_confidence=ocr_result.get("ocr_confidence"),
        ocr_raw_text=ocr_result.get("ocr_raw_text"),
        ocr_data=json.dumps(ocr_result) if ocr_result else None,
        # AI scoring
        risk_score=decision.risk_score,
        anomaly_score=decision.anomaly_score,
        ai_category=decision.predicted_category,
        risk_factors=json.dumps(decision.risk_factors),
        status=decision.decision,
        approved_by="AgentFin" if decision.decision == "auto_approved" else None,
        approval_reason=decision.reason,
        memo=decision.memo,
        submitted_at=datetime.utcnow(),
        processed_at=datetime.utcnow(),
    )

    # If auto-approved, execute instant payment via Tempo blockchain
    if decision.decision == "auto_approved" and employee.tempo_wallet:
        tempo_client = get_tempo_client()
        payment = tempo_client.send_payment(
            destination=employee.tempo_wallet,
            amount=expense.amount,
            memo=decision.memo,
            expense_id=expense_id,
        )

        if payment["success"]:
            db_expense.tx_hash = payment["tx_hash"]
            db_expense.tempo_tx_url = payment["tempo_tx_url"]
            db_expense.paid_at = datetime.utcnow()
            db_expense.status = "paid"

    db.add(db_expense)

    # Create audit log entry
    audit = AuditLogDB(
        expense_id=expense_id,
        action=f"expense_{decision.decision}",
        actor="AgentFin",
        details=json.dumps({
            "decision": decision.decision,
            "reason": decision.reason,
            "risk_score": decision.risk_score,
            "anomaly_score": decision.anomaly_score,
            "policy_result": decision.policy_result,
        }),
        risk_score=decision.risk_score,
        tx_hash=db_expense.tx_hash,
        memo=decision.memo,
    )
    db.add(audit)

    db.commit()
    db.refresh(db_expense)

    logger.info(
        f"✅ Expense {expense_id}: ${expense.amount:.2f} → "
        f"{db_expense.status} (Risk: {decision.risk_score:.3f})"
    )

    # Get ensemble layer scores from the risk scorer for transparency
    risk_scorer = approval_engine.risk_scorer
    layer_scores = {}
    model_used = "ensemble"
    try:
        risk_result = risk_scorer.predict_risk(features)
        layer_scores = risk_result.get("layer_scores", {})
        model_used = risk_result.get("model_used", "ensemble")
    except Exception:
        pass

    # Build enriched response with risk explanation and fee info
    response_data = ExpenseResponse.model_validate(db_expense)
    result = response_data.model_dump()
    result["risk_explanation"] = risk_explanation
    result["fee_sponsored"] = db_expense.tx_hash is not None
    result["fee_sponsor_label"] = "AgentFin Agent Wallet" if db_expense.tx_hash else None
    result["model_used"] = model_used
    result["risk_level"] = (
        "low" if decision.risk_score < 0.3
        else "medium" if decision.risk_score < 0.7
        else "high"
    )
    result["layer_scores"] = layer_scores

    # Include OCR verification results if available
    if ocr_result.get("ocr_success"):
        result["ocr_verification"] = {
            "ocr_amount": ocr_result.get("ocr_amount"),
            "ocr_merchant": ocr_result.get("ocr_merchant"),
            "ocr_date": ocr_result.get("ocr_date"),
            "ocr_confidence": ocr_result.get("ocr_confidence"),
            "ocr_item_count": ocr_result.get("ocr_item_count", 0),
            "ocr_tax": ocr_result.get("ocr_tax"),
            "amount_mismatch": ocr_features.get("amount_mismatch", 0),
            "amount_mismatch_flag": ocr_features.get("amount_mismatch_flag", False),
            "merchant_mismatch": ocr_features.get("merchant_mismatch", False),
            "date_gap_days": ocr_features.get("date_gap_days", 0),
            "date_mismatch_flag": ocr_features.get("date_mismatch_flag", False),
        }

    return result


@router.get("/", response_model=ExpenseListResponse)
async def list_expenses(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: str = Query(None),
    employee_id: str = Query(None),
    db: Session = Depends(get_db),
):
    """List all expenses with optional filtering."""
    query = db.query(ExpenseDB)

    if status:
        query = query.filter(ExpenseDB.status == status)
    if employee_id:
        query = query.filter(ExpenseDB.employee_id == employee_id)

    total = query.count()
    expenses = query.order_by(desc(ExpenseDB.submitted_at)).offset(skip).limit(limit).all()

    return ExpenseListResponse(total=total, expenses=expenses)


@router.get("/stats", response_model=ExpenseStats)
async def get_expense_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    total = db.query(ExpenseDB).count()
    total_amount = db.query(func.sum(ExpenseDB.amount)).scalar() or 0.0
    auto_approved = db.query(ExpenseDB).filter(ExpenseDB.status.in_(["auto_approved", "paid"])).count()
    manager_review = db.query(ExpenseDB).filter(ExpenseDB.status == "manager_review").count()
    rejected = db.query(ExpenseDB).filter(ExpenseDB.status == "rejected").count()
    flagged = db.query(ExpenseDB).filter(ExpenseDB.status == "flagged").count()
    paid = db.query(ExpenseDB).filter(ExpenseDB.status == "paid").count()
    avg_risk = db.query(func.avg(ExpenseDB.risk_score)).scalar() or 0.0

    # Estimate time saved: 20 min per expense manually, ~3 sec with AI
    time_saved = (total * 20) / 60  # hours saved

    return ExpenseStats(
        total_expenses=total,
        total_amount=round(total_amount, 2),
        auto_approved=auto_approved,
        manager_review=manager_review,
        rejected=rejected,
        flagged=flagged,
        paid=paid,
        avg_risk_score=round(avg_risk, 4),
        total_saved_time_hours=round(time_saved, 1),
    )


@router.get("/{expense_id}", response_model=ExpenseResponse)
async def get_expense(expense_id: str, db: Session = Depends(get_db)):
    """Get a single expense by ID."""
    expense = db.query(ExpenseDB).filter(ExpenseDB.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@router.post("/{expense_id}/approve")
async def manually_approve(expense_id: str, db: Session = Depends(get_db)):
    """Manually approve an expense (manager action) and pay via Tempo."""
    expense = db.query(ExpenseDB).filter(ExpenseDB.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status not in ["manager_review", "pending", "disputed"]:
        raise HTTPException(status_code=400, detail=f"Cannot approve expense in '{expense.status}' status")

    # Get employee wallet
    employee = db.query(EmployeeDB).filter(
        EmployeeDB.employee_id == expense.employee_id
    ).first()

    expense.status = "approved"
    expense.approved_by = "Manager"
    expense.processed_at = datetime.utcnow()

    # Execute payment on Tempo
    if employee and employee.tempo_wallet:
        tempo_client = get_tempo_client()
        payment = tempo_client.send_payment(
            destination=employee.tempo_wallet,
            amount=expense.amount,
            memo=expense.memo or f"Approved by manager | Expense {expense_id}",
            expense_id=expense_id,
        )

        if payment["success"]:
            expense.tx_hash = payment["tx_hash"]
            expense.tempo_tx_url = payment["tempo_tx_url"]
            expense.paid_at = datetime.utcnow()
            expense.status = "paid"

    # Audit log
    audit = AuditLogDB(
        expense_id=expense_id,
        action="manually_approved",
        actor="Manager",
        details=f"Manually approved and paid ${expense.amount:.2f}",
        tx_hash=expense.tx_hash,
    )
    db.add(audit)
    db.commit()

    return {"message": f"Expense {expense_id} approved and paid", "status": expense.status}


@router.post("/{expense_id}/reject")
async def manually_reject(expense_id: str, db: Session = Depends(get_db)):
    """Manually reject an expense."""
    expense = db.query(ExpenseDB).filter(ExpenseDB.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    expense.status = "rejected"
    expense.approved_by = "Manager"
    expense.approval_reason = "Manually rejected by manager"
    expense.processed_at = datetime.utcnow()

    audit = AuditLogDB(
        expense_id=expense_id,
        action="manually_rejected",
        actor="Manager",
        details=f"Expense ${expense.amount:.2f} rejected by manager",
    )
    db.add(audit)
    db.commit()

    return {"message": f"Expense {expense_id} rejected", "status": "rejected"}


# ─── Receipt Upload ──────────────────────────────────────────────

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads", "receipts")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload-receipt")
async def upload_receipt(file: UploadFile = File(...)):
    """
    Upload a receipt image/PDF. Runs OCR to extract structured data.
    Returns the file path and OCR results to attach to an expense.
    Supports JPEG, PNG, PDF files up to 10MB.
    """
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "application/pdf"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{file.content_type}' not allowed. Use JPEG, PNG, or PDF."
        )

    # Validate file size (10MB max)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum 10MB.")

    # Save file with unique name
    ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
    filename = f"receipt_{uuid.uuid4().hex[:12]}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)

    with open(filepath, "wb") as f:
        f.write(contents)

    logger.info(f"📎 Receipt uploaded: {filename} ({len(contents)} bytes)")

    # Run OCR on the uploaded image
    ocr_result = {}
    if file.content_type and file.content_type.startswith("image/"):
        try:
            ocr_result = extract_receipt_data(filepath)
            logger.info(
                f"🔍 OCR complete: amount=${ocr_result.get('ocr_amount')}, "
                f"merchant={ocr_result.get('ocr_merchant')}, "
                f"confidence={ocr_result.get('ocr_confidence', 0):.1%}"
            )
        except Exception as e:
            logger.warning(f"⚠️ OCR failed for {filename}: {e}")
            ocr_result = {"ocr_success": False, "ocr_error": str(e)}

    return {
        "filename": filename,
        "filepath": f"/uploads/receipts/{filename}",
        "size_bytes": len(contents),
        "content_type": file.content_type,
        "ocr": ocr_result,
    }


# ─── Dispute / Raise Exception ──────────────────────────────────

@router.post("/{expense_id}/dispute")
async def dispute_expense(
    expense_id: str,
    request: DisputeRequest,
    db: Session = Depends(get_db),
):
    """
    Raise an exception / dispute a rejected or flagged expense.

    This allows employees to contest AI decisions. The expense moves
    to 'disputed' status and is escalated for manager review with the
    employee's justification attached.
    """
    expense = db.query(ExpenseDB).filter(ExpenseDB.expense_id == expense_id).first()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    if expense.status not in ["rejected", "flagged"]:
        raise HTTPException(
            status_code=400,
            detail=f"Can only dispute rejected or flagged expenses. "
                   f"Current status: '{expense.status}'"
        )

    old_status = expense.status
    expense.status = "disputed"
    expense.approval_reason = (
        f"[DISPUTED] Employee contested {old_status} decision. "
        f"Reason: {request.reason}. "
        f"Original: {expense.approval_reason or 'N/A'}"
    )

    # Create audit log entry
    audit = AuditLogDB(
        expense_id=expense_id,
        action="expense_disputed",
        actor=expense.employee_id,
        details=json.dumps({
            "previous_status": old_status,
            "dispute_reason": request.reason,
            "risk_score": expense.risk_score,
        }),
        risk_score=expense.risk_score,
    )
    db.add(audit)
    db.commit()
    db.refresh(expense)

    logger.info(
        f"⚠️ Expense {expense_id} disputed by {expense.employee_id}: {request.reason}"
    )

    return {
        "message": f"Exception raised for expense {expense_id}",
        "expense_id": expense_id,
        "previous_status": old_status,
        "new_status": "disputed",
        "dispute_reason": request.reason,
    }


# ─── Natural Language Parsing ─────────────────────────────────────

@router.post("/parse")
async def parse_expense_text(request: NLParseRequest):
    """
    Parse a natural language expense description into structured fields.

    Example: "Spent $120 at Marriott for the Chicago conference"
    → { amount: 120, merchant: "Marriott", category: "accommodation", ... }
    """
    result = parse_natural_language(request.text)
    return result


# ─── Batch Approve (Parallel Tempo Payments) ──────────────────────

@router.post("/batch-approve")
async def batch_approve_pending(db: Session = Depends(get_db)):
    """
    Approve and pay ALL pending manager_review expenses in parallel.

    Uses Tempo's 2D nonce system for concurrent transaction submission.
    This demonstrates high-throughput payment processing capability.
    """
    # Get all pending expenses
    pending = db.query(ExpenseDB).filter(
        ExpenseDB.status == "manager_review"
    ).all()

    if not pending:
        return {
            "message": "No expenses pending review",
            "approved": 0,
            "total_amount": 0,
        }

    # Build payment list
    payments = []
    expense_map = {}

    for expense in pending:
        employee = db.query(EmployeeDB).filter(
            EmployeeDB.employee_id == expense.employee_id
        ).first()

        if employee and employee.tempo_wallet:
            payment = {
                "destination": employee.tempo_wallet,
                "amount": expense.amount,
                "memo": expense.memo or f"Batch approved | {expense.expense_id}",
                "expense_id": expense.expense_id,
            }
            payments.append(payment)
            expense_map[expense.expense_id] = expense

    if not payments:
        return {
            "message": "No expenses with valid wallets",
            "approved": 0,
            "total_amount": 0,
        }

    # Execute batch payment on Tempo
    tempo_client = get_tempo_client()
    batch_result = tempo_client.send_batch_payments(payments)

    # Update database records
    approved_count = 0
    for result in batch_result.get("results", []):
        eid = result.get("expense_id")
        if eid and eid in expense_map and result.get("success"):
            expense = expense_map[eid]
            expense.status = "paid"
            expense.approved_by = "Manager (Batch)"
            expense.tx_hash = result.get("tx_hash")
            expense.tempo_tx_url = result.get("tempo_tx_url")
            expense.paid_at = datetime.utcnow()
            expense.processed_at = datetime.utcnow()

            # Audit log
            audit = AuditLogDB(
                expense_id=eid,
                action="batch_approved",
                actor="Manager",
                details=json.dumps({
                    "batch": True,
                    "parallel": True,
                    "fee_sponsored": True,
                    "amount": expense.amount,
                }),
                tx_hash=result.get("tx_hash"),
                memo=expense.memo,
            )
            db.add(audit)
            approved_count += 1

    db.commit()

    total_amount = sum(
        r.get("amount", 0) for r in batch_result.get("results", []) if r.get("success")
    )

    logger.info(
        f"⚡ Batch approved: {approved_count}/{len(payments)} expenses | "
        f"Total: ${total_amount:,.2f} | Parallel: True"
    )

    return {
        "message": f"Batch approved {approved_count} expenses",
        "approved": approved_count,
        "failed": batch_result.get("failed", 0),
        "total_amount": round(total_amount, 2),
        "parallel_execution": True,
        "nonce_strategy": batch_result.get("nonce_strategy", "unknown"),
        "fee_sponsored": True,
        "transactions": [
            {
                "expense_id": r.get("expense_id"),
                "tx_hash": r.get("tx_hash"),
                "amount": r.get("amount"),
                "tempo_tx_url": r.get("tempo_tx_url"),
                "nonce_key": r.get("nonce_key"),
                "tx_type": r.get("tx_type"),
            }
            for r in batch_result.get("results", []) if r.get("success")
        ],
    }
