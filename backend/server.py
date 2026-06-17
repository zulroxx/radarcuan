import asyncio
import json
import logging
import os
import re
import sys
import uuid
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from contextlib import asynccontextmanager
from starlette.responses import Response

import yfinance as yf

from db_cache import get_cached, get_cached_sector_recommendations

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Cache file path for TradingView data
CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
CACHE_TTL_SECONDS = 3600  # 1 hour cache (file fallback)

# File-based storage fallback (when MongoDB is unavailable)
FEEDBACK_FILE = ROOT_DIR / "agent_cache" / "feedback.json"
WAITLIST_FILE = ROOT_DIR / "agent_cache" / "waitlist.json"
(ROOT_DIR / "agent_cache").mkdir(exist_ok=True)

# Scheduler interval
SCHEDULE_INTERVAL_SECONDS = 14400  # 4 hours


def load_json_fallback(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def save_json_fallback(path: Path, data: list) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# MongoDB connection (optional — required only for feedback/waitlist endpoints)
mongo_url = os.environ.get("MONGO_URL")
db = None
client = None
_mongo_failed = False

if mongo_url:
    try:
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=10000,
            tlsAllowInvalidCertificates=True,
        )
    except Exception as e:
        logger.warning(f"MongoDB client init error: {e}")
        client = None
        _mongo_failed = True


async def scheduler_loop():
    """Background loop: fetch all data every 4 hours and store in MongoDB."""
    await asyncio.sleep(30)  # wait for server to fully start
    while True:
        try:
            from scheduler import run_scheduled_fetch
            await run_scheduled_fetch(db)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(SCHEDULE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, _mongo_failed
    if client is not None:
        try:
            await client.admin.command("ping")
            db = client[os.environ.get("DB_NAME", "ihsg_screener")]
            logger.info("MongoDB connection established")
            # Start background scheduler (will also do initial fetch after 30s)
            asyncio.create_task(scheduler_loop())
        except Exception:
            _mongo_failed = True
            logger.warning("MongoDB tidak dapat dijangkau, menggunakan file storage fallback")

    logger.info("Application started")
    yield

    if client is not None:
        client.close()
        logger.info("MongoDB connection closed")

# Create the main app without a prefix
app = FastAPI(lifespan=lifespan)

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    model_config = ConfigDict(extra="ignore")  # Ignore MongoDB's _id field
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class StatusCheckCreate(BaseModel):
    client_name: str


class FeedbackCreate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    email: Optional[EmailStr] = None
    message: str = Field(min_length=5, max_length=1500)


class FeedbackResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    message: str
    created_at: str


class WaitlistCreate(BaseModel):
    email: EmailStr
    note: Optional[str] = Field(default=None, max_length=300)


class WaitlistResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    email: EmailStr
    note: Optional[str] = None
    created_at: str
    updated_at: str
    status: Literal["created", "updated"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# Cache helper functions for TradingView data
def load_cached_data() -> Optional[Dict[str, Any]]:
    """Load cached TradingView data if it exists and is not stale."""
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get('cached_at', ''))
        age_seconds = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if age_seconds < CACHE_TTL_SECONDS:
            return cached
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def save_cached_data(
    data: List[Dict[str, Any]],
    strong_buy_count: int,
    analysis_summary: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Save TradingView data to cache file."""
    cache_data = {
        'cached_at': now_iso(),
        'data': data,
        'total': len(data),
        'strong_buy_count': strong_buy_count,
        'analysis_summary': analysis_summary or {},
        'metadata': metadata or {},
    }
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)


# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root() -> Dict[str, str]:
    return {"message": "IHSG Smart Screener API aktif"}

def using_file_fallback() -> bool:
    return db is None or _mongo_failed

def require_db():
    if using_file_fallback():
        raise HTTPException(status_code=503, detail="MongoDB tidak tersedia. Menggunakan file storage.")
    return db

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate) -> StatusCheck:
    status_dict: Dict[str, str] = input.model_dump()
    status_obj = StatusCheck(**status_dict)
    
    # Convert to dict and serialize datetime to ISO string for MongoDB
    doc: Dict[str, Any] = status_obj.model_dump()
    doc['timestamp'] = doc['timestamp'].isoformat()
    
    _ = await require_db().status_checks.insert_one(doc)
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks() -> List[StatusCheck]:
    # Exclude MongoDB's _id field from the query results
    status_checks = await require_db().status_checks.find({}, {"_id": 0}).to_list(1000)
    
    # Convert ISO string timestamps back to datetime objects
    for check in status_checks:
        if isinstance(check['timestamp'], str):
            check['timestamp'] = datetime.fromisoformat(check['timestamp'])
    
    return status_checks


@api_router.post("/feedback", response_model=FeedbackResponse)
async def create_feedback(payload: FeedbackCreate) -> FeedbackResponse:
    feedback_doc: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "name": payload.name,
        "email": payload.email,
        "message": payload.message,
        "created_at": now_iso(),
    }
    if using_file_fallback():
        data = load_json_fallback(FEEDBACK_FILE)
        data.append(feedback_doc)
        save_json_fallback(FEEDBACK_FILE, data)
    else:
        await require_db().beta_feedback.insert_one(dict(feedback_doc))
    return FeedbackResponse(**feedback_doc)


@api_router.post("/waitlist", response_model=WaitlistResponse)
async def create_waitlist_entry(payload: WaitlistCreate) -> WaitlistResponse:
    timestamp = now_iso()

    if using_file_fallback():
        data = load_json_fallback(WAITLIST_FILE)
        existing = [e for e in data if e.get("email") == payload.email]
        if existing:
            entry = existing[0]
            entry["note"] = payload.note or entry.get("note")
            entry["updated_at"] = timestamp
            entry["status"] = "updated"
            save_json_fallback(WAITLIST_FILE, data)
            return WaitlistResponse(**entry)
        doc: Dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "email": payload.email,
            "note": payload.note,
            "created_at": timestamp,
            "updated_at": timestamp,
        }
        data.append(doc)
        save_json_fallback(WAITLIST_FILE, data)
        return WaitlistResponse(**{**doc, "status": "created"})

    existing_entry = await require_db().premium_waitlist.find_one({"email": payload.email}, {"_id": 0})

    if existing_entry:
        updated_doc: Dict[str, Any] = {
            "id": existing_entry["id"],
            "email": payload.email,
            "note": payload.note,
            "created_at": existing_entry["created_at"],
            "updated_at": timestamp,
            "status": "updated",
        }
        await db.premium_waitlist.update_one(
            {"email": payload.email},
            {
                "$set": {
                    "note": payload.note,
                    "updated_at": timestamp,
                }
            },
        )
        return WaitlistResponse(**updated_doc)

    waitlist_doc: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "email": payload.email,
        "note": payload.note,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    await require_db().premium_waitlist.insert_one(dict(waitlist_doc))
    return WaitlistResponse(**{**waitlist_doc, "status": "created"})


@api_router.get("/collections/summary")
async def get_collection_summary() -> Dict[str, int]:
    try:
        if using_file_fallback():
            feedback_data = load_json_fallback(FEEDBACK_FILE)
            waitlist_data = load_json_fallback(WAITLIST_FILE)
            return {
                "feedback_count": len(feedback_data),
                "waitlist_count": len(waitlist_data),
            }
        feedback_count = await require_db().beta_feedback.count_documents({})
        waitlist_count = await require_db().premium_waitlist.count_documents({})
        return {
            "feedback_count": feedback_count,
            "waitlist_count": waitlist_count,
        }
    except Exception as exc:
        logger.exception("Gagal membaca ringkasan koleksi")
        raise HTTPException(status_code=500, detail="Gagal membaca data ringkasan") from exc


@api_router.get("/tradingview/summary")
async def get_tradingview_summary(
    limit: int = Query(default=500, ge=10, le=1000),
) -> Dict[str, Any]:
    try:
        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "tradingview")
            if mongo_cached:
                data = mongo_cached.get("data", [])
                if limit and limit < len(data):
                    data = data[:limit]
                return {
                    "success": True,
                    "message": f"Data dari MongoDB cache (diperbarui {mongo_cached.get('cached_at', 'unknown')})",
                    "data": data,
                    "total": len(data),
                    "strong_buy_count": mongo_cached.get("strong_buy_count", 0),
                    "analysis_summary": mongo_cached.get("analysis_summary", {}),
                    "metadata": mongo_cached.get("metadata", {}),
                    "updated_at": mongo_cached.get("cached_at"),
                    "from_cache": True,
                }

        # Fallback to file cache
        cached = load_cached_data()
        if cached:
            data = cached.get("data", [])
            if limit and limit < len(data):
                data = data[:limit]
            return {
                "success": True,
                "message": f"Data dari file cache (diperbarui {cached.get('cached_at', 'unknown')})",
                "data": data,
                "total": len(data),
                "strong_buy_count": cached.get("strong_buy_count", 0),
                "analysis_summary": cached.get("analysis_summary", {}),
                "metadata": cached.get("metadata", {}),
                "updated_at": cached.get("cached_at"),
                "from_cache": True,
            }

        return {
            "success": False,
            "message": "Data belum tersedia. Sistem akan mengambil data secara otomatis dalam beberapa menit.",
            "data": [],
            "total": 0,
            "strong_buy_count": 0,
            "analysis_summary": {},
            "metadata": {},
        }
    except Exception as exc:
        logger.exception("Gagal mengambil data TradingView")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data TradingView: {str(exc)}") from exc


@api_router.get("/news/flow")
async def get_news_flow() -> Dict[str, Any]:
    try:
        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "news")
            if mongo_cached:
                return {
                    "success": True,
                    "message": f"Berita dari MongoDB cache ({mongo_cached.get('total_news', 0)} berita)",
                    "news": mongo_cached.get("news", []),
                    "analysis": mongo_cached.get("analysis", {}),
                    "total_news": mongo_cached.get("total_news", 0),
                    "generated_at": mongo_cached.get("generated_at"),
                    "model": mongo_cached.get("model"),
                    "from_cache": True,
                }

        # Fallback to file cache
        from news_flow_agent import load_cached_news
        cached = load_cached_news()
        if cached:
            return {
                "success": True,
                "message": f"Berita dari file cache ({cached.get('total_news', 0)} berita)",
                "news": cached.get("news", []),
                "analysis": cached.get("analysis", {}),
                "total_news": cached.get("total_news", 0),
                "generated_at": cached.get("generated_at"),
                "model": cached.get("model"),
                "from_cache": True,
            }

        return {
            "success": False,
            "message": "Data berita belum tersedia. Sistem akan mengambil data secara otomatis.",
            "news": [],
            "analysis": {},
            "total_news": 0,
        }
    except Exception as exc:
        logger.exception("Gagal mengambil news flow")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil news: {str(exc)}") from exc


ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")


class AdminLoginPayload(BaseModel):
    username: str
    password: str


@api_router.post("/admin/login")
async def admin_login(payload: AdminLoginPayload) -> Dict[str, Any]:
    if payload.username == ADMIN_USERNAME and payload.password == ADMIN_PASSWORD:
        return {"success": True, "token": "ihsg-admin-token"}
    raise HTTPException(status_code=401, detail="Username atau password salah")


def verify_admin(token: str = Query(...)) -> None:
    if token != "ihsg-admin-token":
        raise HTTPException(status_code=401, detail="Token admin tidak valid")


@api_router.post("/admin/refresh-cache")
async def admin_refresh_cache(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        from scheduler import run_scheduled_fetch
        results = await run_scheduled_fetch(db)
        return {
            "success": True,
            "message": "Cache refresh triggered",
            "results": {k: str(v) for k, v in results.items()},
        }
    except Exception as exc:
        logger.exception("Gagal refresh cache")
        raise HTTPException(status_code=500, detail=f"Gagal refresh cache: {str(exc)}") from exc


@api_router.get("/admin/feedback")
async def admin_get_feedback(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        if using_file_fallback():
            data = load_json_fallback(FEEDBACK_FILE)
            data.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return {"success": True, "data": data, "total": len(data)}
        data = await require_db().beta_feedback.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"success": True, "data": data, "total": len(data)}
    except Exception as exc:
        logger.exception("Gagal mengambil data feedback")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil feedback: {str(exc)}") from exc


@api_router.get("/admin/waitlist")
async def admin_get_waitlist(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        if using_file_fallback():
            data = load_json_fallback(WAITLIST_FILE)
            data.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return {"success": True, "data": data, "total": len(data)}
        data = await require_db().premium_waitlist.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
        return {"success": True, "data": data, "total": len(data)}
    except Exception as exc:
        logger.exception("Gagal mengambil data waitlist")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil waitlist: {str(exc)}") from exc


@api_router.get("/sector/predictions")
async def get_sector_predictions() -> Dict[str, Any]:
    try:
        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "sector_predictions")
            if mongo_cached:
                return {
                    "success": True,
                    "message": "Prediksi sektor dari MongoDB cache.",
                    "predictions": mongo_cached.get("predictions", {}),
                    "generated_at": mongo_cached.get("generated_at"),
                    "model": mongo_cached.get("model"),
                    "from_cache": True,
                }

        # Fallback to file cache
        from sector_predictor_agent import load_cached_predictions
        cached = load_cached_predictions()
        if cached:
            return {
                "success": True,
                "message": "Prediksi sektor dari file cache.",
                "predictions": cached.get("predictions", {}),
                "generated_at": cached.get("generated_at"),
                "model": cached.get("model"),
                "from_cache": True,
            }

        return {
            "success": False,
            "message": "Prediksi sektor belum tersedia. Sistem akan memperbarui secara otomatis.",
            "predictions": {},
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan prediksi sektor")
        raise HTTPException(status_code=500, detail=f"Gagal prediksi sektor: {str(exc)}") from exc


# ===== Order Book Simulation =====

TIMEFRAME_DAYS = {"1M": 30, "3M": 90, "6M": 180, "12M": 365}


def _fetch_current_price(ticker: str) -> Optional[float]:
    try:
        tk = yf.Ticker(f"{ticker}.JK")
        hist = tk.history(period="1d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 2)
        info = tk.info
        if info and "regularMarketPrice" in info:
            return round(float(info["regularMarketPrice"]), 2)
    except Exception:
        pass
    return None


def _fetch_price_at_date(ticker: str, date_str: str) -> Optional[float]:
    try:
        start = date.fromisoformat(date_str)
        end = start + timedelta(days=5)
        tk = yf.Ticker(f"{ticker}.JK")
        hist = tk.history(start=start.isoformat(), end=end.isoformat())
        if not hist.empty:
            return round(float(hist["Close"].iloc[0]), 2)
    except Exception:
        pass
    return None


@api_router.get("/order-book/simulation")
async def get_order_book_simulation(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        # Reuse sector predictions logic
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "sector_predictions")
            predictions_data = mongo_cached
        else:
            predictions_data = None

        if not predictions_data:
            from sector_predictor_agent import load_cached_predictions
            predictions_data = load_cached_predictions()

        predictions = (predictions_data or {}).get("predictions", {})
        if not predictions or all(not v for v in predictions.values()):
            return {
                "success": False,
                "simulations": [],
                "message": "Prediksi sektor belum tersedia. Jalankan scheduler terlebih dahulu.",
            }

        simulations = []

        for tf in TIMEFRAME_DAYS:
            preds = predictions.get(tf, [])
            if not preds:
                continue

            top_sector = preds[0]
            sector_name = top_sector["sector"]
            predicted_return = top_sector.get("predicted_return", 0)

            # Fetch stock recommendations for this sector (top 2)
            stocks_data = []
            if not using_file_fallback():
                mongo_recs = await get_cached_sector_recommendations(db, sector_name)
                if mongo_recs:
                    stocks_data = mongo_recs.get("recommendations", [])[:2]

            if not stocks_data:
                from stock_recommender_agent import load_cached_recommendations
                cached = load_cached_recommendations(sector_name, 2)
                if cached:
                    stocks_data = cached.get("recommendations", [])[:2]

            today = date.today()
            buy_date = today.isoformat()
            sell_date = (today + timedelta(days=TIMEFRAME_DAYS[tf])).isoformat()

            stock_simulations = []
            for stock in stocks_data[:2]:
                ticker = stock["ticker"]
                price = _fetch_current_price(ticker)
                buy_price = price
                current_price = price

                estimated_sell_price = None
                if buy_price and predicted_return:
                    estimated_sell_price = round(buy_price * (1 + predicted_return / 100), 2)

                actual_sell_price = None
                actual_return_pct = None
                if date.today() > date.fromisoformat(sell_date):
                    actual_sell_price = _fetch_price_at_date(ticker, sell_date)
                    if buy_price and actual_sell_price:
                        actual_return_pct = round((actual_sell_price - buy_price) / buy_price * 100, 2)

                stock_simulations.append({
                    "ticker": ticker,
                    "company_name": stock.get("company_name", ""),
                    "recommendation": stock.get("recommendation", ""),
                    "score": stock.get("score", 0),
                    "buy_date": buy_date,
                    "sell_date": sell_date,
                    "buy_price": buy_price,
                    "current_price": current_price,
                    "estimated_sell_price": estimated_sell_price,
                    "actual_sell_price": actual_sell_price,
                    "predicted_return_pct": round(predicted_return, 2),
                    "actual_return_pct": actual_return_pct,
                    "status": "closed" if actual_sell_price is not None else "open",
                    "key_metrics": {
                        "per": stock.get("key_metrics", {}).get("per"),
                        "pbv": stock.get("key_metrics", {}).get("pbv"),
                        "roe": stock.get("key_metrics", {}).get("roe"),
                    },
                })

            simulations.append({
                "timeframe": tf,
                "sector": {
                    "name": sector_name,
                    "rank": 1,
                    "predicted_return": predicted_return,
                    "confidence": top_sector.get("confidence"),
                    "rationale": top_sector.get("rationale", ""),
                },
                "stocks": stock_simulations,
            })

        return {
            "success": True,
            "simulations": simulations,
            "generated_at": now_iso(),
        }
    except Exception as exc:
        logger.exception("Gagal generate order book simulation")
        raise HTTPException(status_code=500, detail=f"Gagal: {str(exc)}") from exc


# ===== Historical Prices for Charts =====

@api_router.get("/stocks/{ticker}/history")
async def get_stock_history(
    ticker: str,
    period: str = Query(default="3mo"),
) -> Dict[str, Any]:
    try:
        if period not in ("1mo", "3mo", "6mo", "1y", "ytd", "max"):
            period = "3mo"
        tk = await asyncio.to_thread(yf.Ticker, f"{ticker}.JK")
        hist = await asyncio.to_thread(lambda: tk.history(period=period))
        if hist.empty:
            return {"success": False, "ticker": ticker, "prices": []}

        prices = []
        for idx, row in hist.iterrows():
            prices.append({
                "date": idx.strftime("%Y-%m-%d"),
                "close": round(float(row["Close"]), 2),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "volume": int(row["Volume"]),
            })

        return {"success": True, "ticker": ticker, "prices": prices}
    except Exception as exc:
        logger.warning(f"Gagal fetch history {ticker}: {exc}")
        return {"success": False, "ticker": ticker, "prices": []}


@api_router.get("/sector/{sector_name}/stocks")
async def get_sector_stock_recommendations(
    sector_name: str,
    limit: int = Query(default=10, ge=1, le=20),
) -> Dict[str, Any]:
    try:
        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached_sector_recommendations(db, sector_name)
            if mongo_cached:
                recs = mongo_cached.get("recommendations", [])[:limit]
                return {
                    "success": True,
                    "sector": sector_name,
                    "recommendations": recs,
                    "sector_prediction": mongo_cached.get("sector_prediction"),
                    "generated_at": mongo_cached.get("generated_at"),
                    "model": mongo_cached.get("model"),
                    "from_cache": True,
                }

        # Fallback to file cache
        from stock_recommender_agent import load_cached_recommendations
        cached = load_cached_recommendations(sector_name, limit)
        if cached:
            recs = cached.get("recommendations", [])[:limit]
            return {
                "success": True,
                "sector": sector_name,
                "recommendations": recs,
                "generated_at": cached.get("generated_at"),
                "model": cached.get("model"),
                "from_cache": True,
            }

        return {
            "success": False,
            "sector": sector_name,
            "recommendations": [],
            "message": "Rekomendasi saham belum tersedia. Sistem akan memperbarui secara otomatis.",
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan rekomendasi saham")
        raise HTTPException(status_code=500, detail=f"Gagal rekomendasi saham: {str(exc)}") from exc


@api_router.get("/sector/{sector_name}/stocks/scoring")
async def get_sector_stock_scoring(
    sector_name: str,
    limit: int = Query(default=10, ge=1, le=20),
) -> Dict[str, Any]:
    """Get stock recommendations with full scoring breakdown (technical + fundamental + valuation + macro).
    Uses cached TradingView data + cached fundamental data.
    """
    try:
        from stock_recommender_agent import get_stocks_in_sector
        from macro_agent import SECTOR_MACRO_SENSITIVITY, load_cache as load_macro_cache
        from scoring_model import calculate_combined_score
        from fundamental_service import get_financial_summary, get_fundamental_score
        import asyncio

        # Get macro data from MongoDB cache first
        macro_indicators = []
        if not using_file_fallback():
            mongo_macro = await get_cached(db, "macro")
            if mongo_macro:
                macro_indicators = mongo_macro.get("indicators", [])
        if not macro_indicators:
            macro_cached = load_macro_cache()
            if macro_cached:
                macro_indicators = macro_cached.get("indicators", [])

        relevant_ids = SECTOR_MACRO_SENSITIVITY.get(sector_name, [])
        sector_macro = [ind for ind in macro_indicators if ind.get("id") in relevant_ids]

        stocks = get_stocks_in_sector(sector_name)
        if not stocks:
            return {
                "success": False,
                "sector": sector_name,
                "scored_stocks": [],
                "message": "Tidak ada data saham untuk sektor ini. Data akan tersedia setelah scheduler berjalan.",
            }

        # Parallel fetch fundamental data
        async def fetch_fundamental(ticker: str) -> tuple:
            loop = asyncio.get_event_loop()
            financial = await loop.run_in_executor(None, get_financial_summary, ticker)
            fund_score, fund_details = await loop.run_in_executor(
                None, get_fundamental_score, financial
            )
            return ticker, financial, fund_score, fund_details

        tasks = [fetch_fundamental(stock.get("ticker", "")) for stock in stocks[:limit]]
        results = await asyncio.gather(*tasks)
        fundamental_map = {r[0]: (r[1], r[2], r[3]) for r in results}

        scored_stocks = []
        for stock in stocks[:limit]:
            ticker = stock.get("ticker", "")
            fin_data = fundamental_map.get(ticker)
            if fin_data:
                financial, fund_score, fund_details = fin_data
            else:
                financial = None
                fund_score, fund_details = 50.0, {"score": 50, "reason": "Data tidak tersedia"}

            scoring = calculate_combined_score(
                stock, sector_name, macro_indicators,
                fundamental_score=fund_score,
            )
            scored_stocks.append({
                "ticker": ticker,
                "companyName": stock.get("companyName"),
                "price": stock.get("price"),
                "scoring": scoring,
                "fundamental_details": fund_details,
                "key_metrics": {
                    "per": stock.get("per"),
                    "pbv": stock.get("pbv"),
                    "roe": stock.get("roe"),
                    "revenue_growth": stock.get("revenue_growth"),
                    "eps_growth": stock.get("eps_growth"),
                    "dividend_yield": stock.get("dividend_yield"),
                    "debt_to_equity": stock.get("debt_to_equity"),
                },
            })

        scored_stocks.sort(key=lambda x: x["scoring"]["combined_score"], reverse=True)

        return {
            "success": True,
            "sector": sector_name,
            "scored_stocks": scored_stocks,
            "sector_macro_context": sector_macro,
            "weights": {
                "technical": 0.30,
                "fundamental": 0.40,
                "macro_sector_fit": 0.15,
                "valuation": 0.15,
            },
        }
    except Exception as exc:
        logger.exception(f"Gagal scoring saham untuk {sector_name}")
        raise HTTPException(status_code=500, detail=f"Gagal scoring saham: {str(exc)}") from exc


@api_router.get("/sector/enhanced-analysis")
async def get_enhanced_sector_analysis() -> Dict[str, Any]:
    """Comprehensive sector analysis with weighted scoring (technical + fundamental + macro).
    Uses cached data from MongoDB/file cache.
    """
    try:
        from sector_predictor_agent import fetch_sector_data, compute_sector_averages, TV_TO_IDX_SECTOR
        from scoring_model import get_weighted_sector_score

        # Get macro data from MongoDB cache first
        macro_indicators = []
        if not using_file_fallback():
            mongo_macro = await get_cached(db, "macro")
            if mongo_macro:
                macro_indicators = mongo_macro.get("indicators", [])
        if not macro_indicators:
            from macro_agent import load_cache as load_macro_cache
            macro_cached = load_macro_cache()
            if macro_cached:
                macro_indicators = macro_cached.get("indicators", [])

        # Get sector predictions from MongoDB cache first
        ai_predictions = {}
        if not using_file_fallback():
            mongo_pred = await get_cached(db, "sector_predictions")
            if mongo_pred:
                ai_predictions = mongo_pred.get("predictions", {})
        if not ai_predictions:
            from sector_predictor_agent import load_cached_predictions
            pred_cached = load_cached_predictions()
            if pred_cached:
                ai_predictions = pred_cached.get("predictions", {})

        # TV sector data (from file cache - the composite source)
        sector_averages_raw = fetch_sector_data()

        mapped_data = {}
        for eng_name, metrics in sector_averages_raw.items():
            idx_name = TV_TO_IDX_SECTOR.get(eng_name, eng_name)
            if idx_name in mapped_data:
                existing = mapped_data[idx_name]
                for k in ["count", "avg_score"]:
                    existing[k] = (existing.get(k, 0) or 0) + (metrics.get(k, 0) or 0)
                continue
            mapped_data[idx_name] = dict(metrics)
            mapped_data[idx_name]["sector"] = idx_name

        scored_sectors = []
        for sector_name, averages in mapped_data.items():
            scoring = get_weighted_sector_score(averages, macro_indicators)
            scored_sectors.append({
                "sector": sector_name,
                "averages": averages,
                "scoring": scoring,
            })

        scored_sectors.sort(key=lambda x: x["scoring"]["combined_score"], reverse=True)

        return {
            "success": True,
            "scored_sectors": scored_sectors,
            "ai_predictions": ai_predictions,
            "macro_indicators": macro_indicators,
            "weights": {
                "technical": 0.30,
                "fundamental": 0.40,
                "macro_sector_fit": 0.15,
                "valuation": 0.15,
            },
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan enhanced analysis")
        raise HTTPException(status_code=500, detail=f"Gagal enhanced analysis: {str(exc)}") from exc


@api_router.get("/screener/companies")
async def get_screener_companies() -> Dict[str, Any]:
    """
    Get screener companies data from MongoDB cache or TradingView file cache.
    Returns data in format compatible with ihsgMockData.js structure.
    """
    try:
        records = []

        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "tradingview")
            if mongo_cached:
                records = mongo_cached.get("data", [])

        # Fallback to file cache
        if not records:
            cached = load_cached_data()
            if cached:
                records = cached.get("data", [])

        if records:
            companies = []
            for item in records:
                companies.append({
                    "stockCode": item.get("ticker", item.get('Ticker', '')),
                    "companyName": item.get("companyName", item.get('Nama Perusahaan', '')),
                    "industry": item.get("sector", "IHSG"),
                    "price": item.get("price") or 0,
                    "per": item.get("per") or 0,
                    "pbv": item.get("pbv") or 0,
                    "roe": item.get("roe") or 0,
                    "npm": item.get("roa") or 0,
                    "der": item.get("debt_to_equity") or 0,
                    "dividendYield": item.get("dividend_yield") or 0,
                    "regularDividend": (item.get("dividend_yield") or 0) > 0,
                    "analysis": item.get("analysis", {}),
                })

            return {
                "success": True,
                "data": companies,
                "total": len(companies),
                "from_cache": True,
            }

        return {
            "success": False,
            "message": "Tidak ada data cache tersedia. Data akan tersedia setelah scheduler berjalan.",
            "data": [],
            "total": 0,
        }
    except Exception as exc:
        logger.exception("Gagal mengambil data screener")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data screener: {str(exc)}") from exc

@api_router.get("/macro/indicators")
async def get_macro_indicators_endpoint() -> Dict[str, Any]:
    try:
        # Try MongoDB cache first
        if not using_file_fallback():
            mongo_cached = await get_cached(db, "macro")
            if mongo_cached:
                return {
                    "success": True,
                    "indicators": mongo_cached.get("indicators", []),
                    "total": mongo_cached.get("total", 0),
                    "cached_at": mongo_cached.get("cached_at"),
                    "from_cache": True,
                }

        # Fallback to file cache
        from macro_agent import load_cache
        cached = load_cache()
        if cached:
            return {
                "success": True,
                "indicators": cached.get("indicators", []),
                "total": len(cached.get("indicators", [])),
                "cached_at": cached.get("cached_at"),
                "from_cache": True,
            }

        return {
            "success": False,
            "message": "Data makro belum tersedia. Sistem akan mengambil data secara otomatis.",
            "indicators": [],
            "total": 0,
        }
    except Exception as exc:
        logger.exception("Gagal mengambil data makro ekonomi")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data makro: {str(exc)}") from exc


# Include the router in the main app
app.include_router(api_router)

# Custom CORS middleware
@app.middleware("http")
async def add_cors_header(request, call_next):
    if request.method == "OPTIONS":
        response = Response()
        response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Max-Age"] = "86400"
        return response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = request.headers.get("origin", "*")
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
