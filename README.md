# IHSG Smart Screener

AI-powered stock screening and macro-economic analysis platform for the Indonesia Stock Exchange (IDX/IHSG).

## Features

- **Smart Screener** — Screen IHSG stocks using TradingView data with AI-powered analysis (valuation, quality, growth, risk scoring)
- **Sector Prediction Agent** — AI agent predicts sector performance across 1M/3M/6M/12M timeframes using Mistral AI
- **Stock Recommendations** — Get AI-generated buy/hold/sell recommendations with fundamental analysis for each sector
- **News Intelligence** — Real-time news aggregation from TradingView with AI-powered sentiment analysis and sector impact assessment
- **Macro Economics Dashboard** — Live macroeconomic indicators (BI Rate, inflation, USD/IDR, GDP, commodity prices) with Yahoo Finance integration
- **Financial Decision Summary (RPK)** — Automated financial guidance based on current macro conditions (Tightening/Stable/Sluggish)
- **Admin Panel** — Manage feedback, waitlist, and monitor system status

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19, React Router 7, Tailwind CSS 3, shadcn/ui, Recharts, Framer Motion |
| Backend | Python 3.13, FastAPI, Uvicorn, Motor (MongoDB async driver) |
| Database | MongoDB (optional — file-based fallback included) |
| AI/ML | Mistral AI (LLM), yfinance, TradingView API |
| Build | CRACO (Create React App configuration override) |

## Project Structure

```
IHSG_SMART_SCREENING/
├── frontend/                  # React SPA
│   └── src/
│       ├── components/        # UI components
│       │   ├── ui/            # shadcn/ui primitives
│       │   └── AgentDashboard/# Prediction & News agents
│       ├── hooks/             # Custom React hooks
│       ├── data/              # Mock data
│       ├── constants/         # Test IDs, constants
│       └── lib/               # Utilities
├── backend/                   # FastAPI server
│   ├── server.py              # Main app with all routes
│   ├── tradingview_agent.py   # TradingView screener + analysis
│   ├── sector_predictor_agent.py  # Sector prediction AI agent
│   ├── stock_recommender_agent.py # Stock recommendation AI agent
│   ├── news_flow_agent.py     # News scraping + AI analysis
│   ├── macro_agent.py         # Macroeconomic data fetcher
│   └── agent_cache/           # JSON cache files
├── tests/                     # Integration tests
└── memory/                    # Project memory/guidelines
```

## Quick Start

### Prerequisites

- Node.js ≥ 20
- Python ≥ 3.13
- Git

### 1. Clone & Install

```bash
git clone <repo-url>
cd IHSG_SMART_SCREENING

# Backend
cd backend
python -m venv .venv
source .venv/bin/activate    # Linux/Mac
# .\.venv\Scripts\activate   # Windows PowerShell
pip install -r requirements.txt
cp .env.example .env

# Frontend
cd ../frontend
npm install
```

### 2. Configure Environment

Edit `backend/.env`:

```env
# Optional — only needed for feedback/waitlist features
MONGO_URL=mongodb://localhost:27017
DB_NAME=ihsg_screener

# CORS — add your frontend URL
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Mistral AI API key (required for AI agents)
LLM_API_KEY=your_mistral_api_key
LLM_BASE_URL=https://api.mistral.ai
LLM_MODEL=mistral-small-latest
```

### 3. Run

```bash
# Terminal 1 — Backend (http://localhost:8000)
cd backend && python server.py

# Terminal 2 — Frontend (http://localhost:3000)
cd frontend && npm start
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/` | Health check |
| GET | `/api/tradingview/summary` | TradingView screener data + AI analysis |
| GET | `/api/sector/predictions` | AI sector predictions by timeframe |
| GET | `/api/sector/{sector}/stocks` | Stock recommendations for a sector |
| GET | `/api/news/flow` | News feed + AI sector analysis |
| GET | `/api/macro/indicators` | Macroeconomic indicators (live + cached) |
| POST | `/api/feedback` | Submit beta feedback |
| POST | `/api/waitlist` | Join premium waitlist |
| POST | `/api/admin/login` | Admin authentication |
| GET | `/api/admin/feedback` | List feedback (admin) |
| GET | `/api/admin/waitlist` | List waitlist (admin) |

## Frontend Routes

| Route | Page |
|-------|------|
| `/` | Screener — stock screening with AI analysis |
| `/prediction` | Predictions — sector forecasts & stock recommendations |
| `/macro` | Macro Economics — live indicators & RPK financial summary |
| `/admin` | Admin panel — feedback & waitlist management |

## AI Agents

### TradingView Agent
Screens IHSG stocks via TradingView API, analyzes fundamentals, and generates:
- **Investment Score** (0-100) based on valuation, quality, growth, dividends, leverage, momentum
- **Reasons to Invest** (bullish factors)
- **Key Risks** (bearish factors)

### Sector Prediction Agent
Uses Mistral AI to predict sector performance across 4 timeframes with confidence levels and key drivers.

### News Intelligence Agent
Scrapes TradingView news headlines and uses Mistral AI to:
- Summarize market-moving news
- Identify benefiting/warning sectors
- Extract key macroeconomic indicators
- Generate trading recommendations

### Macro Agent
Fetches live macroeconomic data:
- **Real-time**: USD/IDR, IHSG, Brent Oil via Yahoo Finance
- **Cached fundamentals**: BI Rate, inflation, GDP (updated on official releases)
- **Auto-classifies** economic status: Mengetat / Stabil / Lesu

## Deployment

- **Frontend**: Build with `cd frontend && npm run build`, deploy the `build/` folder to Vercel, Netlify, Cloudflare Pages, or any static host
- **Backend**: Deploy as a Python service to Railway, Render, Fly.io, or a VPS — set environment variables on the hosting platform
- **Database**: MongoDB Atlas (free tier) or skip for file-based fallback

## License

MIT
