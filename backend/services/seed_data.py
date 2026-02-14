"""
Seed demo data for the application.
Creates sample employees with REAL Tempo testnet wallets, org hierarchy,
approval routing rules, and policies for demonstration.
"""

import json
import logging
from database import SessionLocal, EmployeeDB, PolicyDB, ApprovalRuleDB

logger = logging.getLogger("TempoExpenseAI.SeedData")

# -----------------------------------------------------------------------
# Real Tempo Testnet Wallets
# Each wallet has 1,000,000 AlphaUSD, BetaUSD, ThetaUSD, and PathUSD.
# Wallet 1 is reserved as the AGENT MASTER WALLET (sends payments).
# Wallets 2-5 are assigned to employees (receive payments).
# -----------------------------------------------------------------------

# Org hierarchy:
#
#   EMP0008 (CFO — Maria Garcia)
#       └── EMP0005 (Finance — Lisa Thompson)
#
#   EMP0007 (VP Sales — Robert Kim)
#       └── EMP0006 (Sales Manager — Amanda Foster)
#           └── EMP0001 (Sales — Sarah Chen)
#
#   EMP0004 (Eng Manager — James Park)
#       └── EMP0002 (Engineering — Dave Rodriguez)
#
#   EMP0003 (Marketing — Emily Watson) → reports to EMP0007 (VP)

DEMO_EMPLOYEES = [
    {
        "employee_id": "EMP0001",
        "name": "Sarah Chen",
        "email": "sarah.chen@company.com",
        "department": "sales",
        "role": "employee",
        "reports_to": "EMP0006",  # Amanda Foster (Sales Manager)
        "monthly_limit": 10000.0,
        "tempo_wallet": "0xAcF8dBD0352a9D47135DA146EA5DbEfAD58340C4",
    },
    {
        "employee_id": "EMP0002",
        "name": "Dave Rodriguez",
        "email": "dave.rodriguez@company.com",
        "department": "engineering",
        "role": "employee",
        "reports_to": "EMP0004",  # James Park (Eng Manager)
        "monthly_limit": 8000.0,
        "tempo_wallet": "0x41A75fc9817AF9F2DB0c0e58C71Bc826339b3Acb",
    },
    {
        "employee_id": "EMP0003",
        "name": "Emily Watson",
        "email": "emily.watson@company.com",
        "department": "marketing",
        "role": "employee",
        "reports_to": "EMP0007",  # Robert Kim (VP Sales & Marketing)
        "monthly_limit": 8000.0,
        "tempo_wallet": "0x88FB1167B01EcE2CAEe65c4E193Ba942D6F73d70",
    },
    {
        "employee_id": "EMP0004",
        "name": "James Park",
        "email": "james.park@company.com",
        "department": "engineering",
        "role": "manager",
        "reports_to": "EMP0008",  # Maria Garcia (CFO) — eng has no VP, reports to exec
        "monthly_limit": 15000.0,
        "tempo_wallet": "0xe945797ebC84F1953Ff8131bC29277e567b881D4",
    },
    {
        "employee_id": "EMP0005",
        "name": "Lisa Thompson",
        "email": "lisa.thompson@company.com",
        "department": "finance",
        "role": "finance",
        "reports_to": "EMP0008",  # Maria Garcia (CFO)
        "monthly_limit": 20000.0,
        "tempo_wallet": "0x031891A61200FedDd622EbACC10734BC90093B2A",
    },
    {
        "employee_id": "EMP0006",
        "name": "Amanda Foster",
        "email": "amanda.foster@company.com",
        "department": "sales",
        "role": "manager",
        "reports_to": "EMP0007",  # Robert Kim (VP)
        "monthly_limit": 15000.0,
        "tempo_wallet": None,
    },
    {
        "employee_id": "EMP0007",
        "name": "Robert Kim",
        "email": "robert.kim@company.com",
        "department": "sales",
        "role": "vp",
        "reports_to": "EMP0008",  # CFO
        "monthly_limit": 30000.0,
        "tempo_wallet": None,
    },
    {
        "employee_id": "EMP0008",
        "name": "Maria Garcia",
        "email": "maria.garcia@company.com",
        "department": "executive",
        "role": "cfo",
        "reports_to": None,  # Top of chain
        "monthly_limit": 100000.0,
        "tempo_wallet": None,
    },
]

DEMO_POLICIES = [
    {
        "name": "Receipt required above $200",
        "category": None,
        "max_amount": None,
        "requires_receipt_above": 200.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Meals limit per expense",
        "category": "meals",
        "max_amount": 500.0,
        "requires_receipt_above": 50.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Travel single expense limit",
        "category": "travel",
        "max_amount": 5000.0,
        "requires_receipt_above": 0.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Monthly employee limit",
        "category": None,
        "max_amount": None,
        "requires_receipt_above": 200.0,
        "monthly_limit": 10000.0,
        "department": None,
    },
    {
        "name": "Equipment requires approval",
        "category": "equipment",
        "max_amount": 3000.0,
        "requires_receipt_above": 0.0,
        "monthly_limit": None,
        "department": None,
    },
]

# -----------------------------------------------------------------------
# Approval Routing Rules
# Lower priority number = higher precedence (evaluated first)
# -----------------------------------------------------------------------

DEMO_APPROVAL_RULES = [
    {
        "name": "Client Entertainment — Manager + Finance",
        "description": "All client entertainment expenses require manager approval followed by finance review",
        "category": "client_entertainment",
        "department": None,
        "amount_min": None,
        "amount_max": None,
        "required_approvers": ["direct_manager", "finance"],
        "approval_type": "sequential",
        "priority": 10,
    },
    {
        "name": "Travel — Manager + Finance",
        "description": "All travel expenses require manager approval and finance sign-off",
        "category": "travel",
        "department": None,
        "amount_min": None,
        "amount_max": None,
        "required_approvers": ["direct_manager", "finance"],
        "approval_type": "sequential",
        "priority": 20,
    },
    {
        "name": "High-Value Equipment — Manager + Finance + CFO",
        "description": "Equipment purchases over $2,000 require triple approval",
        "category": "equipment",
        "department": None,
        "amount_min": 2000.0,
        "amount_max": None,
        "required_approvers": ["direct_manager", "finance", "cfo"],
        "approval_type": "sequential",
        "priority": 5,
    },
    {
        "name": "Large Expenses — Manager + Finance",
        "description": "Any expense over $1,000 requires manager and finance approval",
        "category": None,
        "department": None,
        "amount_min": 1000.0,
        "amount_max": None,
        "required_approvers": ["direct_manager", "finance"],
        "approval_type": "sequential",
        "priority": 50,
    },
    {
        "name": "Accommodation — Manager",
        "description": "Accommodation expenses require manager approval",
        "category": "accommodation",
        "department": None,
        "amount_min": None,
        "amount_max": None,
        "required_approvers": ["direct_manager"],
        "approval_type": "sequential",
        "priority": 30,
    },
    {
        "name": "Software Purchases — Manager",
        "description": "Software purchases require manager sign-off",
        "category": "software",
        "department": None,
        "amount_min": None,
        "amount_max": None,
        "required_approvers": ["direct_manager"],
        "approval_type": "sequential",
        "priority": 40,
    },
    {
        "name": "Training — Manager",
        "description": "Training expenses are approved by direct manager",
        "category": "training",
        "department": None,
        "amount_min": None,
        "amount_max": None,
        "required_approvers": ["direct_manager"],
        "approval_type": "sequential",
        "priority": 40,
    },
]


def seed_demo_data():
    """Seed the database with demo employees (real Tempo wallets), policies, and approval rules."""
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(EmployeeDB).count()
        if existing > 0:
            logger.info(f"ℹ️ Database already has {existing} employees, skipping seed")
            return

        # Seed employees with real Tempo testnet wallets + hierarchy
        for emp_data in DEMO_EMPLOYEES:
            employee = EmployeeDB(
                employee_id=emp_data["employee_id"],
                name=emp_data["name"],
                email=emp_data["email"],
                department=emp_data["department"],
                role=emp_data["role"],
                reports_to=emp_data.get("reports_to"),
                tempo_wallet=emp_data.get("tempo_wallet"),
                monthly_limit=emp_data["monthly_limit"],
            )
            db.add(employee)
            mgr_info = f" → reports to {emp_data.get('reports_to', 'nobody')}" if emp_data.get("reports_to") else " (top)"
            wallet_info = f" → {emp_data['tempo_wallet'][:10]}..." if emp_data.get("tempo_wallet") else ""
            logger.info(f"   👤 {emp_data['name']} ({emp_data['role']}){mgr_info}{wallet_info}")

        # Seed policies
        for pol_data in DEMO_POLICIES:
            policy = PolicyDB(
                name=pol_data["name"],
                category=pol_data["category"],
                max_amount=pol_data["max_amount"],
                requires_receipt_above=pol_data["requires_receipt_above"],
                monthly_limit=pol_data["monthly_limit"],
                department=pol_data["department"],
                active=True,
            )
            db.add(policy)
            logger.info(f"   📋 Policy: {pol_data['name']}")

        # Seed approval routing rules
        for rule_data in DEMO_APPROVAL_RULES:
            rule = ApprovalRuleDB(
                name=rule_data["name"],
                description=rule_data.get("description"),
                category=rule_data.get("category"),
                department=rule_data.get("department"),
                amount_min=rule_data.get("amount_min"),
                amount_max=rule_data.get("amount_max"),
                required_approvers=json.dumps(rule_data["required_approvers"]),
                approval_type=rule_data.get("approval_type", "sequential"),
                priority=rule_data.get("priority", 100),
                active=True,
            )
            db.add(rule)
            approvers = " → ".join(rule_data["required_approvers"])
            logger.info(f"   🔀 Rule: {rule_data['name']} [{approvers}]")

        db.commit()
        logger.info(
            f"✅ Seeded {len(DEMO_EMPLOYEES)} employees, "
            f"{len(DEMO_POLICIES)} policies, "
            f"{len(DEMO_APPROVAL_RULES)} approval rules"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seed data failed: {e}")
    finally:
        db.close()
