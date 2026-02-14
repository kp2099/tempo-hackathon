# TempoExpenseAI 🤖💰

An autonomous AI-powered expense approval agent that detects fraud, routes approvals, and instantly pays employees using Tempo's programmable stablecoin infrastructure on the Tempo L1 blockchain.

## 🌟 Features

- **XGBoost Risk Scoring** + Isolation Forest anomaly detection
- **Three-tier approval system** (auto-approve / review / reject)
- **Instant TIP-20 stablecoin payments** on Tempo blockchain
- **Programmable memos** with AI reasoning (on-chain audit trail)
- **Verifiable transactions** on explore.tempo.xyz

## 🏗️ Tech Stack

- **Backend**: FastAPI + SQLAlchemy + XGBoost + Web3.py
- **Frontend**: React + Vite + Tailwind CSS
- **Blockchain**: Tempo L1 (Moderato Testnet, Chain ID 42431)
- **Stablecoin**: AlphaUSD (TIP-20 token)

## 🚀 Quick Start (Docker - Recommended)

### Prerequisites
- Docker and Docker Compose installed

### Run the Application

```bash
# Start the application
docker-compose up --build

# Access:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:8000
# - API Docs: http://localhost:8000/docs

# Stop the application
docker-compose down
```

## 🛠️ Manual Setup (Without Docker)

### Prerequisites
- Python 3.12+
- Node.js 18+
- Homebrew (macOS) for installing libomp

### Backend Setup

```bash
# Install OpenMP library (macOS)
brew install libomp

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt

# Run backend
python main.py
# Runs on http://localhost:8000
```

### Frontend Setup

```bash
# Install dependencies
cd frontend
npm install

# Run frontend
npm run dev
# Runs on http://localhost:3000
```

## 📝 Environment Variables

Configuration is in `docker-compose.yml` or create a `.env` file from `env.example`:

- `TEMPO_RPC_URL` - Tempo blockchain RPC endpoint
- `TEMPO_CHAIN_ID` - Chain ID (42431 for Moderato testnet)
- `TEMPO_PRIVATE_KEY` - Test wallet private key
- `ALPHA_USD_ADDRESS` - TIP-20 stablecoin address
- `RISK_THRESHOLD_AUTO_APPROVE` - Auto-approve threshold (0.3)
- `RISK_THRESHOLD_AUTO_REJECT` - Auto-reject threshold (0.7)
- `MAX_AUTO_APPROVE_AMOUNT` - Max auto-approve amount ($500)

## 🎮 Using the Application

1. **Submit an Expense**: Go to http://localhost:3000/submit
2. **AI Processing**: Agent analyzes risk, detects anomalies, and makes a decision
3. **Instant Payment**: If auto-approved, payment is sent immediately to employee's Tempo wallet
4. **View Audit Trail**: Check transactions on explore.tempo.xyz

## 📚 API Endpoints

- `POST /api/expenses/submit` - Submit expense
- `GET /api/expenses/` - List expenses
- `GET /api/employees/` - List employees
- `GET /api/audit/trail` - Audit trail
- `GET /health` - Health check

Full API docs: http://localhost:8000/docs

## 🔒 Security Note

⚠️ The private key in `env.example` is a TEST WALLET for Moderato testnet only. Never use real private keys in code.

## 📄 License

MIT License

---

**Made with ❤️ for the Tempo Hackathon**
