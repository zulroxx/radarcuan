import json
import logging
import os
import re
import sys
import uuid
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from contextlib import asynccontextmanager
from starlette.responses import Response

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Cache file path for TradingView data
CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
CACHE_TTL_SECONDS = 3600  # 1 hour cache

# File-based storage fallback (when MongoDB is unavailable)
FEEDBACK_FILE = ROOT_DIR / "agent_cache" / "feedback.json"
WAITLIST_FILE = ROOT_DIR / "agent_cache" / "waitlist.json"
(ROOT_DIR / "agent_cache").mkdir(exist_ok=True)


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
    client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=3000)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, _mongo_failed
    if client is not None:
        try:
            await client.admin.command("ping")
            db = client[os.environ.get("DB_NAME", "ihsg_screener")]
            logger.info("MongoDB connection established")
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
    refresh: bool = Query(default=False),
    limit: int = Query(default=500, ge=10, le=1000),
) -> Dict[str, Any]:
    try:
        # Check for cached data first
        cached = load_cached_data()
        if cached and not refresh:
            logger.info("Menggunakan data dari cache")
            return {
                "success": True,
                "message": f"Data dari cache (diperbarui {cached.get('cached_at', 'unknown')})",
                "data": cached['data'],
                "total": cached['total'],
                "strong_buy_count": cached['strong_buy_count'],
                "analysis_summary": cached.get("analysis_summary", {}),
                "metadata": cached.get("metadata", {}),
                "updated_at": cached.get("cached_at"),
                "from_cache": True,
            }
        
        # Add backend directory to path so we can import scraper
        backend_dir = Path(__file__).parent
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        
        from tradingview_agent import fetch_and_analyze_tradingview_screen

        records, analysis_summary, metadata = fetch_and_analyze_tradingview_screen(limit=limit)

        if not records:
            return {
                "success": False,
                "message": "Tidak ada data yang berhasil diambil dari TradingView screener",
                "data": [],
                "total": 0,
                "strong_buy_count": 0,
                "analysis_summary": analysis_summary,
                "metadata": metadata,
            }

        strong_buy_count = sum(1 for item in records if item.get("Rekomendasi Analis") == "Pembelian kuat")
        
        # Save to cache
        save_cached_data(records, strong_buy_count, analysis_summary, metadata)
        
        return {
            "success": True,
            "message": f"Berhasil mengambil dan menganalisis {len(records)} saham dari TradingView",
            "data": records,
            "total": len(records),
            "strong_buy_count": strong_buy_count,
            "analysis_summary": analysis_summary,
            "metadata": metadata,
            "updated_at": now_iso(),
            "from_cache": False,
        }
    except Exception as exc:
        # Try to return cached data as fallback on error
        cached = load_cached_data()
        if cached:
            logger.info("Menggunakan data cache sebagai fallback karena error")
            return {
                "success": True,
                "message": f"Data dari cache (error: {str(exc)})",
                "data": cached['data'],
                "total": cached['total'],
                "strong_buy_count": cached['strong_buy_count'],
                "analysis_summary": cached.get("analysis_summary", {}),
                "metadata": cached.get("metadata", {}),
                "updated_at": cached.get("cached_at"),
                "from_cache": True,
            }
        logger.exception("Gagal mengambil data TradingView")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data TradingView: {str(exc)}") from exc


@api_router.get("/news/flow")
async def get_news_flow(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from news_flow_agent import get_news_analysis
        result = get_news_analysis(refresh=refresh)
        return {
            "success": True,
            "message": f"Berhasil mengambil {result.get('total_news', 0)} berita dan analisis.",
            "news": result.get("news", []),
            "analysis": result.get("analysis", {}),
            "total_news": result.get("total_news", 0),
            "generated_at": result.get("generated_at"),
            "model": result.get("model"),
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
async def get_sector_predictions(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from sector_predictor_agent import get_predictions_by_timeframe
        result = get_predictions_by_timeframe(timeframe=None, refresh=refresh)
        return {
            "success": True,
            "message": "Prediksi sektor berhasil di-generate oleh AI agent.",
            "predictions": result.get("predictions", {}),
            "generated_at": result.get("generated_at"),
            "model": result.get("model"),
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan prediksi sektor")
        raise HTTPException(status_code=500, detail=f"Gagal prediksi sektor: {str(exc)}") from exc


@api_router.get("/sector/{sector_name}/stocks")
async def get_sector_stock_recommendations(
    sector_name: str,
    limit: int = Query(default=10, ge=1, le=20),
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from sector_predictor_agent import predict_sectors
        from stock_recommender_agent import recommend_stocks

        sector_prediction_data = predict_sectors(refresh=False)
        sector_predictions = sector_prediction_data.get("predictions", {})

        sector_prediction = None
        for tf in ["1M", "3M", "6M", "12M"]:
            tf_preds = sector_predictions.get(tf, [])
            for pred in tf_preds:
                if pred.get("sector", "").lower() == sector_name.lower():
                    if sector_prediction is None:
                        sector_prediction = pred
                    break

        result = recommend_stocks(
            sector_name=sector_name,
            limit=limit,
            refresh=refresh,
            sector_prediction=sector_prediction,
        )
        return {
            "success": True,
            "sector": sector_name,
            "recommendations": result.get("recommendations", []),
            "sector_prediction": sector_prediction,
            "generated_at": result.get("generated_at"),
            "model": result.get("model"),
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan rekomendasi saham")
        raise HTTPException(status_code=500, detail=f"Gagal rekomendasi saham: {str(exc)}") from exc


@api_router.get("/sector/{sector_name}/stocks/scoring")
async def get_sector_stock_scoring(
    sector_name: str,
    limit: int = Query(default=10, ge=1, le=20),
) -> Dict[str, Any]:
    """Get stock recommendations with full scoring breakdown (technical + fundamental + valuation + macro)."""
    try:
        from stock_recommender_agent import get_stocks_in_sector
        from macro_agent import get_macro_indicators, get_sector_macro_context
        from scoring_model import calculate_combined_score, score_macro_sector_fit
        from fundamental_service import get_financial_summary, get_fundamental_score

        macro_data = get_macro_indicators()
        sector_macro = get_sector_macro_context(sector_name)

        stocks = get_stocks_in_sector(sector_name)

        scored_stocks = []
        for stock in stocks[:limit]:
            ticker = stock.get("ticker", "")
            financial = get_financial_summary(ticker)
            fund_score, fund_details = get_fundamental_score(financial)
            scoring = calculate_combined_score(
                stock, sector_name, macro_data["indicators"],
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
async def get_enhanced_sector_analysis(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    """Comprehensive sector analysis with weighted scoring (technical + fundamental + macro)."""
    try:
        from sector_predictor_agent import get_predictions_by_timeframe, fetch_sector_data, compute_sector_averages, TV_TO_IDX_SECTOR
        from macro_agent import get_macro_indicators
        from scoring_model import get_weighted_sector_score, score_macro_sector_fit

        macro_data = get_macro_indicators(refresh=refresh)
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
            scoring = get_weighted_sector_score(averages, macro_data["indicators"])
            scored_sectors.append({
                "sector": sector_name,
                "averages": averages,
                "scoring": scoring,
            })

        scored_sectors.sort(key=lambda x: x["scoring"]["combined_score"], reverse=True)

        predictions = get_predictions_by_timeframe(timeframe=None, refresh=refresh)
        ai_predictions = predictions.get("predictions", {})

        return {
            "success": True,
            "scored_sectors": scored_sectors,
            "ai_predictions": ai_predictions,
            "macro_indicators": macro_data["indicators"],
            "weights": {
                "technical": 0.30,
                "fundamental": 0.40,
                "macro_sector_fit": 0.15,
                "valuation": 0.15,
            },
            "generated_at": macro_data.get("cached_at"),
        }
    except Exception as exc:
        logger.exception("Gagal menjalankan enhanced analysis")
        raise HTTPException(status_code=500, detail=f"Gagal enhanced analysis: {str(exc)}") from exc


@api_router.get("/screener/companies")
async def get_screener_companies() -> Dict[str, Any]:
    """
    Get screener companies data from TradingView cache.
    Returns data in format compatible with ihsgMockData.js structure.
    """
    try:
        cached = load_cached_data()
        if cached:
            # Transform TradingView data to screener format
            companies = []
            for item in cached['data']:
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
                    "updated_at": cached.get('cached_at'),
                })
            
            return {
                "success": True,
                "data": companies,
                "total": len(companies),
                "updated_at": cached.get('cached_at'),
                "from_cache": True,
            }
        
        return {
            "success": False,
            "message": "Tidak ada data cache tersedia",
            "data": [],
            "total": 0,
        }
    except Exception as exc:
        logger.exception("Gagal mengambil data screener")
        raise HTTPException(status_code=500, detail=f"Gagal mengambil data screener: {str(exc)}") from exc

@api_router.get("/macro/indicators")
async def get_macro_indicators(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from macro_agent import get_macro_indicators as fetch_macro
        result = fetch_macro(refresh=refresh)
        return {
            "success": True,
            "indicators": result.get("indicators", []),
            "total": result.get("total", 0),
            "cached_at": result.get("cached_at"),
            "from_cache": result.get("from_cache", False),
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
