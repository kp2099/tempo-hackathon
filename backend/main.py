"""
TempoExpenseAI - Autonomous AI-Powered Expense Approval Agent
Main FastAPI application entry point.

Uses Tempo blockchain (L1, Chain ID 42431) for instant stablecoin payments
with programmable memos for on-chain audit trails.
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

    # Seed demo data (employees with real Tempo testnet wallets)
    seed_demo_data()
    logger.info("✅ Demo data seeded")

    # Ensure ML models are trained
    ensure_models_exist()
    logger.info("✅ ML models loaded")

    logger.info("🤖 AgentFin is online and ready for autonomous expense processing!")
    logger.info(f"⛓️  Tempo RPC: {settings.tempo_rpc_url}")
    logger.info(f"🔍 Explorer: {settings.tempo_explorer_url}")
    yield
    logger.info("👋 TempoExpenseAI shutting down...")


app = FastAPI(
    title="TempoExpenseAI",
    description=(
        "Autonomous AI-powered expense approval agent that detects fraud, "
        "routes approvals, and instantly pays employees using Tempo's "
        "programmable stablecoin infrastructure on the Tempo L1 blockchain."
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
        "blockchain": "Tempo L1 (Moderato Testnet)",
        "chain_id": settings.tempo_chain_id,
        "description": (
            "Autonomous AI expense approval agent with "
            "Tempo stablecoin payments"
        ),
        "features": [
            "XGBoost risk scoring + Isolation Forest anomaly detection",
            "Three-tier approval (auto-approve / review / reject)",
            "Instant TIP-20 stablecoin payments on Tempo blockchain",
            "Programmable memos with AI reasoning (on-chain audit trail)",
            "Verifiable transactions on explore.tempo.xyz",
        ],
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "agent": "AgentFin", "chain": "tempo_moderato"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
