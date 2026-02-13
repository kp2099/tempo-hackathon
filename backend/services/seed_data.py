"""
Seed demo data for the application.
Creates sample employees and policies for demonstration.
"""

import logging
from database import SessionLocal, EmployeeDB, PolicyDB
from services.tempo_client import get_tempo_client

logger = logging.getLogger("TempoExpenseAI.SeedData")

DEMO_EMPLOYEES = [
    {
        "employee_id": "EMP0001",
        "name": "Sarah Chen",
        "email": "sarah.chen@company.com",
        "department": "sales",
        "role": "employee",
        "monthly_limit": 5000.0,
    },
    {
        "employee_id": "EMP0002",
        "name": "Dave Rodriguez",
        "email": "dave.rodriguez@company.com",
        "department": "engineering",
        "role": "employee",
        "monthly_limit": 3000.0,
    },
    {
        "employee_id": "EMP0003",
        "name": "Emily Watson",
        "email": "emily.watson@company.com",
        "department": "marketing",
        "role": "employee",
        "monthly_limit": 4000.0,
    },
    {
        "employee_id": "EMP0004",
        "name": "James Park",
        "email": "james.park@company.com",
        "department": "engineering",
        "role": "manager",
        "monthly_limit": 8000.0,
    },
    {
        "employee_id": "EMP0005",
        "name": "Lisa Thompson",
        "email": "lisa.thompson@company.com",
        "department": "finance",
        "role": "finance",
        "monthly_limit": 10000.0,
    },
]

DEMO_POLICIES = [
    {
        "name": "Receipt required above $25",
        "category": None,
        "max_amount": None,
        "requires_receipt_above": 25.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Meals limit per expense",
        "category": "meals",
        "max_amount": 100.0,
        "requires_receipt_above": 25.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Travel single expense limit",
        "category": "travel",
        "max_amount": 2000.0,
        "requires_receipt_above": 0.0,
        "monthly_limit": None,
        "department": None,
    },
    {
        "name": "Monthly employee limit",
        "category": None,
        "max_amount": None,
        "requires_receipt_above": 25.0,
        "monthly_limit": 5000.0,
        "department": None,
    },
    {
        "name": "Equipment requires approval",
        "category": "equipment",
        "max_amount": 500.0,
        "requires_receipt_above": 0.0,
        "monthly_limit": None,
        "department": None,
    },
]


def seed_demo_data():
    """Seed the database with demo employees and policies."""
    db = SessionLocal()
    try:
        # Check if already seeded
        existing = db.query(EmployeeDB).count()
        if existing > 0:
            logger.info(f"ℹ️ Database already has {existing} employees, skipping seed")
            return

        tempo_client = get_tempo_client()

        # Seed employees
        for emp_data in DEMO_EMPLOYEES:
            # Provision wallet
            wallet = tempo_client.provision_wallet(emp_data["employee_id"])

            employee = EmployeeDB(
                employee_id=emp_data["employee_id"],
                name=emp_data["name"],
                email=emp_data["email"],
                department=emp_data["department"],
                role=emp_data["role"],
                stellar_wallet=wallet["public_key"],
                monthly_limit=emp_data["monthly_limit"],
            )
            db.add(employee)
            logger.info(f"   👤 Created employee: {emp_data['name']} ({emp_data['employee_id']})")

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
            logger.info(f"   📋 Created policy: {pol_data['name']}")

        db.commit()
        logger.info(f"✅ Seeded {len(DEMO_EMPLOYEES)} employees and {len(DEMO_POLICIES)} policies")

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Seed data failed: {e}")
    finally:
        db.close()

