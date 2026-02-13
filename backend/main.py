"""
TempoExpenseAI - Autonomous AI-Powered Expense Approval Agent
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging

from config import settings
from database import create_tables, SessionLocal, PolicyDB
from routers import expenses, employees, audit
from ml.train import ensure_models_exist
from services.seed_data import seed_demo_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TempoExpenseAI")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("🚀 Starting TempoExpenseAI Agent...")

    # Create database tables
    create_tables()
    logger.info("✅ Database tables created")

    # Seed demo data
    seed_demo_data()
    logger.info("✅ Demo data seeded")

    # Ensure ML models are trained
    ensure_models_exist()
    logger.info("✅ ML models loaded")

    logger.info("🤖 AgentFin is online and ready for autonomous expense processing!")
    yield
    logger.info("👋 TempoExpenseAI shutting down...")


app = FastAPI(
    title="TempoExpenseAI",
    description=(
        "Autonomous AI-powered expense approval agent that detects fraud, "
        "routes approvals, and instantly pays employees using Tempo's "
        "programmable stablecoin infrastructure."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Trail"])


@app.get("/")
async def root():
    return {
        "name": "TempoExpenseAI",
        "agent": "AgentFin",
        "status": "online",
        "description": (
            "Autonomous AI expense approval agent with "
            "Tempo stablecoin payments"
        ),
        "features": [
            "XGBoost anomaly detection",
            "Behavioral risk scoring",
            "Three-tier approval (auto-approve / review / reject)",
            "Instant Stellar/Tempo stablecoin payments",
            "Programmable memos with AI reasoning",
            "On-chain tamper-proof audit trail",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "AgentFin"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )

