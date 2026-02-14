"""
Seed demo data for the application.
Creates sample employees with REAL Tempo testnet wallets and policies for demonstration.
"""

import logging
from database import SessionLocal, EmployeeDB, PolicyDB

logger = logging.getLogger("TempoExpenseAI.SeedData")

# -----------------------------------------------------------------------
# Real Tempo Testnet Wallets
# Each wallet has 1,000,000 AlphaUSD, BetaUSD, ThetaUSD, and PathUSD.
# Wallet 1 is reserved as the AGENT MASTER WALLET (sends payments).
# Wallets 2-5 are assigned to employees (receive payments).
# -----------------------------------------------------------------------

DEMO_EMPLOYEES = [
    {
        "employee_id": "EMP0001",
        "name": "Sarah Chen",
        "email": "sarah.chen@company.com",
        "department": "sales",
        "role": "employee",
        "monthly_limit": 10000.0,
        # Wallet 2 — real funded Tempo testnet wallet
        "tempo_wallet": "0xAcF8dBD0352a9D47135DA146EA5DbEfAD58340C4",
    },
    {
        "employee_id": "EMP0002",
        "name": "Dave Rodriguez",
        "email": "dave.rodriguez@company.com",
        "department": "engineering",
        "role": "employee",
        "monthly_limit": 8000.0,
        # Wallet 3 — real funded Tempo testnet wallet
        "tempo_wallet": "0x41A75fc9817AF9F2DB0c0e58C71Bc826339b3Acb",
    },
    {
        "employee_id": "EMP0003",
        "name": "Emily Watson",
        "email": "emily.watson@company.com",
        "department": "marketing",
        "role": "employee",
        "monthly_limit": 8000.0,
        # Wallet 4 — real funded Tempo testnet wallet
        "tempo_wallet": "0x88FB1167B01EcE2CAEe65c4E193Ba942D6F73d70",
    },
    {
        "employee_id": "EMP0004",
        "name": "James Park",
        "email": "james.park@company.com",
        "department": "engineering",
        "role": "manager",
        "monthly_limit": 15000.0,
        # Wallet 5 — real funded Tempo testnet wallet
        "tempo_wallet": "0xe945797ebC84F1953Ff8131bC29277e567b881D4",
    },
    {
        "employee_id": "EMP0005",
        "name": "Lisa Thompson",
        "email": "lisa.thompson@company.com",
        "department": "finance",
        "role": "finance",
        "monthly_limit": 20000.0,
        # Uses a derived address (not one of the 5 test wallets)
        "tempo_wallet": "0x031891A61200FedDd622EbACC10734BC90093B2A",
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


def seed_demo_data():
    """Seed the database with demo employees (real Tempo wallets) and policies."""
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(EmployeeDB).count()
        if existing > 0:
            logger.info(f"ℹ️ Database already has {existing} employees, skipping seed")
            return

        # Seed employees with real Tempo testnet wallets
        for emp_data in DEMO_EMPLOYEES:
            employee = EmployeeDB(
                employee_id=emp_data["employee_id"],
                name=emp_data["name"],
                email=emp_data["email"],
                department=emp_data["department"],
                role=emp_data["role"],
                tempo_wallet=emp_data["tempo_wallet"],
                monthly_limit=emp_data["monthly_limit"],
            )
            db.add(employee)
            logger.info(
                f"   👤 {emp_data['name']} ({emp_data['employee_id']}) "
                f"→ {emp_data['tempo_wallet'][:10]}..."
            )

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

        db.commit()
        logger.info(
            f"✅ Seeded {len(DEMO_EMPLOYEES)} employees (real Tempo wallets) "
            f"and {len(DEMO_POLICIES)} policies"
        )

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seed data failed: {e}")
    finally:
        db.close()
