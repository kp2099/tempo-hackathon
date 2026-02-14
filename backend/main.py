"""
TempoExpenseAI - Autonomous AI-Powered Expense Approval Agent
Main FastAPI application entry point.

Uses Tempo blockchain (L1, Chain ID 42431) for instant stablecoin payments
with programmable memos for on-chain audit trails.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import os
import logging

from config import settings
from database import create_tables, SessionLocal, PolicyDB
from routers import expenses, employees, audit
from routers import approval_rules
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
allowed_origins = [
    "https://tempo-hackathon-iojj-j2j4niivn-karthiks-projects-e8a6be20.vercel.app",
    "https://tempo-hackathon-iojj.vercel.app",  # Vercel production URL
    "https://tempo-hackathon.vercel.app",
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
]
# Also allow any *.vercel.app preview deploys
cors_origin_regex = r"https://tempo-hackathon.*\.vercel\.app"

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(expenses.router, prefix="/api/expenses", tags=["Expenses"])
app.include_router(employees.router, prefix="/api/employees", tags=["Employees"])
app.include_router(audit.router, prefix="/api/audit", tags=["Audit Trail"])
app.include_router(approval_rules.router, prefix="/api/approval", tags=["Approval Rules & Org"])

# Serve uploaded receipt files
uploads_dir = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


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
    import os
    # Render sets $PORT dynamically — MUST bind to it or deploy fails
    port = int(os.environ.get("PORT", settings.api_port))
    logger.info(f"🔌 Binding to port {port}")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
