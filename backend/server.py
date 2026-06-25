import asyncio
import json
import logging
import os
import re
import sys
import time
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Query, Request
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from contextlib import asynccontextmanager
from starlette.responses import Response

import pytz
import yfinance as yf

logging.getLogger("yfinance").setLevel(logging.ERROR)
_yf_tz_cache = Path(__file__).parent / "agent_cache" / "yfinance_tz"
_yf_tz_cache.mkdir(parents=True, exist_ok=True)
yf.set_tz_cache_location(str(_yf_tz_cache))

from agent_status import get_status_summary, update_agent_status
from cache_versioning import cache_version_manager
from circuit_breaker import circuit_breaker_registry
from agent_metrics import agent_metrics
from db_cache import (
    get_cached, set_cached, get_cached_sector_recommendations, set_cached_sector_recommendations,
    delete_cached, delete_cached_sector_recommendations
)
from fine_tuning.config import FINETUNE_ENABLED, FINETUNED_MODEL_ID, FINETUNE_TRAFFIC_PERCENT, RAW_DIR, PREPARED_DIR
from llm_rate_limiter import global_llm_limiter
from order_book_store import OrderBookStore
from yfinance_session import yfinance_session_manager

ROOT_DIR = Path(__file__).parent
LOG_FILE = ROOT_DIR / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)
load_dotenv(ROOT_DIR / '.env')

# Cache file path for TradingView data
CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
CACHE_TTL_SECONDS = 3600  # 1 hour cache (file fallback)

# File-based storage fallback (when MongoDB is unavailable)
FEEDBACK_FILE = ROOT_DIR / "agent_cache" / "feedback.json"
WAITLIST_FILE = ROOT_DIR / "agent_cache" / "waitlist.json"
ORDER_BOOK_FILE = ROOT_DIR / "agent_cache" / "order_book_history.json"
RATING_FILE = ROOT_DIR / "agent_cache" / "ratings.json"
(ROOT_DIR / "agent_cache").mkdir(exist_ok=True)

# Locks for concurrent request deduplication
# Prevents multiple users from triggering the same external API call simultaneously
_tv_fetch_lock = asyncio.Lock()
_rec_locks: Dict[str, asyncio.Lock] = {}
_rec_locks_lock = asyncio.Lock()
_scoring_locks: Dict[str, asyncio.Lock] = {}
_scoring_locks_lock = asyncio.Lock()
_refresh_cache_lock = asyncio.Lock()
_history_fetch_lock = asyncio.Lock()
_order_book_lock = asyncio.Lock()
_order_book_store: Optional[OrderBookStore] = None
# Simple in-memory cache for stock history (yfinance calls on every chart render)
_stock_history_cache: Dict[str, Any] = {}
STOCK_HISTORY_CACHE_TTL = 1800  # 30 minutes

# Rate limiting for feedback/waitlist (per-IP, sliding window)
_rate_limit_store: Dict[str, List[float]] = {}
RATE_LIMIT_WINDOW = 60  # seconds
RATE_LIMIT_MAX_REQUESTS = 5  # max requests per window

# Max lock dictionaries size to prevent memory leak
_MAX_LOCK_DICT_SIZE = 100
_MAX_STOCK_HISTORY_CACHE_SIZE = 500


def _evict_stock_history_cache() -> None:
    """Evict oldest entries from stock history cache if too large."""
    if len(_stock_history_cache) <= _MAX_STOCK_HISTORY_CACHE_SIZE:
        return
    # Remove oldest 20% of entries
    sorted_keys = sorted(
        _stock_history_cache.keys(),
        key=lambda k: _stock_history_cache[k][0],
    )
    evict_count = max(1, len(sorted_keys) // 5)
    for key in sorted_keys[:evict_count]:
        _stock_history_cache.pop(key, None)


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
_last_mongo_retry = 0.0
MONGO_RETRY_INTERVAL = 30  # seconds between retry attempts

if mongo_url:
    try:
        client = AsyncIOMotorClient(
            mongo_url,
            serverSelectionTimeoutMS=5000,
        )
    except Exception as e:
        logger.warning(f"MongoDB client init error: {e}")
        client = None


async def _ensure_mongo_connection():
    global db, client, _mongo_failed, _order_book_store
    if db is not None:
        return True
    if not mongo_url:
        return False
    try:
        if client is None:
            client = AsyncIOMotorClient(mongo_url, serverSelectionTimeoutMS=5000)
        await client.admin.command("ping")
        db = client[os.environ.get("DB_NAME", "ihsg_screener")]
        _mongo_failed = False
        logger.info("MongoDB connection established")

        old_store = _order_book_store
        try:
            new_store = OrderBookStore(mongo_db=db, file_path=ORDER_BOOK_FILE)
            if new_store.is_file_fallback and old_store is None:
                _order_book_store = new_store
                logger.info("OrderBookStore initialized with file-only (MongoDB unavailable)")
            elif not new_store.is_file_fallback:
                await new_store.sync_file_from_mongo()
                _order_book_store = new_store
                logger.info("OrderBookStore upgraded to MongoDB")
        except Exception as e:
            logger.warning("OrderBookStore init error: %s", e)
            if old_store is not None:
                _order_book_store = old_store

        return True
    except Exception as e:
        _mongo_failed = True
        logger.warning("MongoDB connection failed: %s", e)
        return False


async def _mongo_retry_loop():
    global _last_mongo_retry
    while True:
        await asyncio.sleep(MONGO_RETRY_INTERVAL)
        if db is None:
            _last_mongo_retry = time.time()
            await _ensure_mongo_connection()


async def scheduler_loop():
    """
    Background loop: fetch data sesuai jadwal pasar IDX.
    - 09:00 WIB  → fetch (pembukaan)
    - 13:00 WIB  → fetch (update tengah hari)
    - 16:00 WIB  → stop, tidak ada fetch otomatis sampai hari berikutnya
    - Hari libur nasional & weekend → skip ke hari market berikutnya
    """
    await asyncio.sleep(5)
    try:
        from scheduler import check_all_caches_exist, reset_scheduler_cancelled_flag
        await check_all_caches_exist(db)
        reset_scheduler_cancelled_flag()
    except Exception as e:
        logger.warning(f"Cache check skipped: {e}")
    while True:
        next_time = _get_next_schedule_time()
        tz = pytz.timezone("Asia/Jakarta")
        now = datetime.now(tz)
        wait_seconds = max((next_time - now).total_seconds(), 0)
        if wait_seconds > 0:
            logger.info(
                "Jadwal AI Agent berikutnya: %s WIB (%d menit lagi)",
                next_time.strftime("%H:%M %A %d-%m-%Y"),
                int(wait_seconds / 60),
            )
            await asyncio.sleep(wait_seconds)
        try:
            from scheduler import reset_scheduler_cancelled_flag
            reset_scheduler_cancelled_flag()
            logger.info("Menjalankan scheduled fetch sesuai jadwal...")
            await run_scheduled_fetch(db)
        except Exception as e:
            logger.error(f"Scheduler error: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, _mongo_failed, _order_book_store

    if client is not None:
        connected = await _ensure_mongo_connection()
        if not connected:
            _mongo_failed = True
            logger.warning(
                "MongoDB tidak dapat dijangkau pada startup. "
                "Akan mencoba kembali setiap %d detik. "
                "Menggunakan file storage fallback sementara.",
                MONGO_RETRY_INTERVAL,
            )
            asyncio.create_task(_mongo_retry_loop())

    if _order_book_store is None:
        try:
            _order_book_store = OrderBookStore(mongo_db=None, file_path=ORDER_BOOK_FILE)
            logger.info("OrderBookStore initialized with file-only storage")
        except Exception as e:
            logger.error("OrderBookStore init error: %s", e)

    asyncio.create_task(scheduler_loop())
    asyncio.create_task(_periodic_lock_cleanup())
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


class RatingCreate(BaseModel):
    agent_type: Literal["sector_prediction", "stock_recommendation", "news_analysis"]
    target_id: str = Field(min_length=1, max_length=200)
    rating: Literal[1, -1]
    sector: Optional[str] = Field(default=None, max_length=100)
    ticker: Optional[str] = Field(default=None, max_length=20)


class RatingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    agent_type: str
    target_id: str
    rating: int
    sector: Optional[str] = None
    ticker: Optional[str] = None
    created_at: str


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
    global _mongo_failed, _last_mongo_retry
    if db is not None:
        return False
    if _mongo_failed and mongo_url:
        now = time.time()
        if now - _last_mongo_retry > MONGO_RETRY_INTERVAL:
            _last_mongo_retry = now
            asyncio.create_task(_ensure_mongo_connection())
    return True


def require_db():
    if using_file_fallback():
        raise HTTPException(status_code=503, detail="MongoDB tidak tersedia. Menggunakan file storage.")
    return db


def _check_rate_limit(ip: str) -> bool:
    """Return True if request is allowed, False if rate limited."""
    now = time.time()
    # Evict old entries globally if store gets too large
    if len(_rate_limit_store) > 1000:
        stale = [k for k, v in _rate_limit_store.items() if not v or now - v[-1] > RATE_LIMIT_WINDOW * 2]
        for k in stale:
            _rate_limit_store.pop(k, None)
    if ip not in _rate_limit_store:
        _rate_limit_store[ip] = []
    timestamps = _rate_limit_store[ip]
    # Remove entries outside the window
    _rate_limit_store[ip] = [t for t in timestamps if now - t < RATE_LIMIT_WINDOW]
    if len(_rate_limit_store[ip]) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    _rate_limit_store[ip].append(now)
    return True


async def _get_cached_data(
    cache_key: str,
    file_loader,
    *file_args,
    **file_kwargs,
) -> Optional[Dict[str, Any]]:
    """Unified cache loading: MongoDB -> file -> None.

    file_loader: callable that returns cached dict or None.
    """
    if not using_file_fallback():
        mongo_cached = await get_cached(db, cache_key)
        if mongo_cached:
            return mongo_cached
    cached = file_loader(*file_args, **file_kwargs) if file_loader else None
    return cached


async def _periodic_lock_cleanup():
    """Periodic cleanup task untuk lock dictionaries setiap 5 menit.
    
    Mencegah memory leak dari _rec_locks dan _scoring_locks yang tumbuh tak terbatas.
    """
    await asyncio.sleep(60)  # Delay 1 menit pertama
    while True:
        try:
            async with _rec_locks_lock:
                if len(_rec_locks) > _MAX_LOCK_DICT_SIZE:
                    logger.info(f"Cleaning up _rec_locks: {len(_rec_locks)} -> {_MAX_LOCK_DICT_SIZE}")
                    _rec_locks.clear()
            
            async with _scoring_locks_lock:
                if len(_scoring_locks) > _MAX_LOCK_DICT_SIZE:
                    logger.info(f"Cleaning up _scoring_locks: {len(_scoring_locks)} -> {_MAX_LOCK_DICT_SIZE}")
                    _scoring_locks.clear()
            
            # Cleanup stale rate limit entries
            now = time.time()
            stale_ips = [
                ip for ip, timestamps in _rate_limit_store.items()
                if not timestamps or now - timestamps[-1] > RATE_LIMIT_WINDOW * 10
            ]
            if stale_ips:
                for ip in stale_ips:
                    _rate_limit_store.pop(ip, None)
                logger.info(f"Cleaned up {len(stale_ips)} stale rate limit entries")
            
        except Exception as e:
            logger.error(f"Lock cleanup error: {e}")
        
        await asyncio.sleep(300)  # Run every 5 minutes

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
async def create_feedback(
    payload: FeedbackCreate,
    request: Request,
) -> FeedbackResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Terlalu banyak request. Silakan coba lagi nanti.")
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
async def create_waitlist_entry(
    payload: WaitlistCreate,
    request: Request,
) -> WaitlistResponse:
    client_ip = request.client.host if request.client else "unknown"
    if not _check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Terlalu banyak request. Silakan coba lagi nanti.")
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


@api_router.post("/feedback/rating", response_model=RatingResponse)
async def create_rating(payload: RatingCreate) -> RatingResponse:
    rating_doc: Dict[str, Any] = {
        "id": str(uuid.uuid4()),
        "agent_type": payload.agent_type,
        "target_id": payload.target_id,
        "rating": payload.rating,
        "sector": payload.sector,
        "ticker": payload.ticker,
        "created_at": now_iso(),
    }
    if using_file_fallback():
        data = load_json_fallback(RATING_FILE)
        data.append(rating_doc)
        save_json_fallback(RATING_FILE, data)
    else:
        await require_db().agent_ratings.insert_one(dict(rating_doc))
    return RatingResponse(**rating_doc)


@api_router.get("/feedback/ratings")
async def get_ratings(agent_type: Optional[str] = Query(default=None)) -> Dict[str, Any]:
    try:
        if using_file_fallback():
            data = load_json_fallback(RATING_FILE)
        else:
            data = await require_db().agent_ratings.find({}, {"_id": 0}).to_list(10000)
        if agent_type:
            data = [r for r in data if r.get("agent_type") == agent_type]
        up = sum(1 for r in data if r.get("rating") == 1)
        down = sum(1 for r in data if r.get("rating") == -1)
        return {
            "success": True,
            "total": len(data),
            "upvotes": up,
            "downvotes": down,
            "ratings": data,
        }
    except Exception as e:
        logger.exception("Gagal membaca ratings")
        raise HTTPException(status_code=500, detail="Gagal membaca data rating") from e


@api_router.get("/feedback/ratings/stats")
async def get_rating_stats() -> Dict[str, Any]:
    try:
        if using_file_fallback():
            data = load_json_fallback(RATING_FILE)
        else:
            data = await require_db().agent_ratings.find({}, {"_id": 0}).to_list(10000)
        by_type: Dict[str, Dict[str, int]] = {}
        for r in data:
            at = r.get("agent_type", "unknown")
            if at not in by_type:
                by_type[at] = {"total": 0, "upvotes": 0, "downvotes": 0}
            by_type[at]["total"] += 1
            if r.get("rating") == 1:
                by_type[at]["upvotes"] += 1
            else:
                by_type[at]["downvotes"] += 1
        return {"success": True, "stats": by_type}
    except Exception as e:
        logger.exception("Gagal membaca statistik rating")
        raise HTTPException(status_code=500, detail="Gagal membaca statistik rating") from e


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
        if refresh:
            async with _tv_fetch_lock:
                # Check if another request already refreshed the cache
                if not using_file_fallback():
                    mongo_cached = await get_cached(db, "tradingview")
                    if mongo_cached and mongo_cached.get("cached_at"):
                        cached_time = datetime.fromisoformat(mongo_cached["cached_at"])
                        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
                        if age < 60:
                            data = mongo_cached.get("data", [])
                            if limit and limit < len(data):
                                data = data[:limit]
                            return {
                                "success": True,
                                "message": f"Data baru saja di-refresh ({len(data)} saham)",
                                "data": data,
                                "total": len(data),
                                "strong_buy_count": mongo_cached.get("strong_buy_count", 0),
                                "analysis_summary": mongo_cached.get("analysis_summary", {}),
                                "metadata": mongo_cached.get("metadata", {}),
                                "updated_at": mongo_cached.get("cached_at"),
                                "from_cache": True,
                            }

                from tradingview_agent import fetch_and_analyze_tradingview_screen

                loop = asyncio.get_event_loop()
                records, summary, metadata = await loop.run_in_executor(
                    None, lambda: fetch_and_analyze_tradingview_screen(limit=limit)
                )
                if records:
                    strong_buy_count = sum(
                        1 for item in records if item.get("Rekomendasi Analis") == "Pembelian kuat"
                    )
                    cache_entry = {
                        "data": records,
                        "total": len(records),
                        "strong_buy_count": strong_buy_count,
                        "analysis_summary": summary,
                        "metadata": metadata,
                    }
                    if not using_file_fallback():
                        await set_cached(db, "tradingview", cache_entry)
                    save_cached_data(records, strong_buy_count, summary, metadata)
                    if limit and limit < len(records):
                        records = records[:limit]
                    return {
                        "success": True,
                        "message": f"Data berhasil di-refresh ({len(records)} saham)",
                        "data": records,
                        "total": len(records),
                        "strong_buy_count": strong_buy_count,
                        "analysis_summary": summary,
                        "metadata": metadata,
                        "updated_at": metadata.get("fetchedAt"),
                        "from_cache": False,
                    }

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

        # No cache found — try a one-time fetch to populate data immediately
        # Use lock to prevent concurrent fetches from multiple users
        async with _tv_fetch_lock:
            # Double-check cache after acquiring lock (another request may have populated it)
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

            logger.info("Cache kosong, mencoba mengambil data langsung...")
            try:
                from tradingview_agent import fetch_and_analyze_tradingview_screen

                loop = asyncio.get_event_loop()
                records, summary, metadata = await loop.run_in_executor(
                    None, lambda: fetch_and_analyze_tradingview_screen(limit=limit)
                )
                if records:
                    strong_buy_count = sum(
                        1 for item in records if item.get("Rekomendasi Analis") == "Pembelian kuat"
                    )
                    cache_entry = {
                        "data": records,
                        "total": len(records),
                        "strong_buy_count": strong_buy_count,
                        "analysis_summary": summary,
                        "metadata": metadata,
                    }
                    if not using_file_fallback():
                        await set_cached(db, "tradingview", cache_entry)
                    save_cached_data(records, strong_buy_count, summary, metadata)
                    if limit and limit < len(records):
                        records = records[:limit]
                    return {
                        "success": True,
                        "message": f"Data berhasil diambil ({len(records)} saham)",
                        "data": records,
                        "total": len(records),
                        "strong_buy_count": strong_buy_count,
                        "analysis_summary": summary,
                        "metadata": metadata,
                        "updated_at": metadata.get("fetchedAt"),
                        "from_cache": False,
                    }
            except Exception as fetch_exc:
                logger.warning(f"Gagal mengambil data TradingView: {fetch_exc}")

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
async def get_news_flow(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from news_flow_agent import get_news_analysis as run_news_analysis, load_cached_news
        from scheduler import is_scheduler_running

        if refresh:
            if is_scheduler_running():
                logger.info("News: scheduler running, skip refresh, return cache")
                refresh = False
            else:
                try:
                    result = await asyncio.to_thread(run_news_analysis, refresh=True)
                    return {
                        "success": True,
                        "message": f"Berita diperbarui ({result.get('total_news', 0)} berita)",
                        "news": result.get("news", []),
                        "analysis": result.get("analysis", {}),
                        "total_news": result.get("total_news", 0),
                        "generated_at": result.get("generated_at"),
                        "model": result.get("model"),
                        "from_cache": False,
                    }
                except Exception as e:
                    logger.warning(f"News refresh gagal ({e}), fallback ke cache...")
                    refresh = False

        cached = await _get_cached_data("news_flow", load_cached_news)
        if cached:
            return {
                "success": True,
                "message": f"Berita dari cache ({cached.get('total_news', 0)} berita)",
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
ADMIN_JWT_SECRET = os.environ.get("ADMIN_JWT_SECRET", os.urandom(32).hex())
ADMIN_TOKEN_EXPIRE_SECONDS = 3600  # 1 hour


class AdminLoginPayload(BaseModel):
    username: str
    password: str


class PlaygroundPayload(BaseModel):
    agent_key: Optional[str] = None
    capability: Literal["premium_search", "code", "image", "search", "none"] = "none"
    model: str = "mistral-large-latest"
    tools: List[Dict[str, Any]] = []
    response_format: Optional[Dict[str, Any]] = None
    instructions: str = ""
    messages: List[Dict[str, str]] = []
    temperature: float = 0.3
    top_p: float = 0.9


def _create_admin_token() -> str:
    """Create a JWT-like admin token with expiry (HS256)."""
    import hmac, hashlib, base64, json
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    payload_data = {
        "sub": "admin",
        "exp": int(time.time()) + ADMIN_TOKEN_EXPIRE_SECONDS,
        "iat": int(time.time()),
    }
    payload = base64.urlsafe_b64encode(json.dumps(payload_data).encode()).rstrip(b"=").decode()
    signature = hmac.new(ADMIN_JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()
    return f"{header}.{payload}.{sig_b64}"


def _verify_admin_token(token: str) -> bool:
    """Verify JWT admin token with expiry check."""
    import hmac, hashlib, base64, json
    parts = token.split(".")
    if len(parts) != 3:
        return False
    header, payload, sig_b64 = parts
    expected_sig = hmac.new(ADMIN_JWT_SECRET.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    expected_b64 = base64.urlsafe_b64encode(expected_sig).rstrip(b"=").decode()
    if not hmac.compare_digest(sig_b64, expected_b64):
        return False
    try:
        padded = payload + "=" * (4 - len(payload) % 4)
        data = json.loads(base64.urlsafe_b64decode(padded))
        if data.get("exp", 0) < time.time():
            return False
        return True
    except Exception:
        return False


@api_router.post("/admin/login")
async def admin_login(payload: AdminLoginPayload) -> Dict[str, Any]:
    if payload.username == ADMIN_USERNAME and payload.password == ADMIN_PASSWORD:
        token = _create_admin_token()
        return {"success": True, "token": token, "expires_in": ADMIN_TOKEN_EXPIRE_SECONDS}
    raise HTTPException(status_code=401, detail="Username atau password salah")


def verify_admin(token: str = Query(default=None, alias="token")) -> None:
    # Support both query param and Authorization header
    if token and _verify_admin_token(token):
        return
    raise HTTPException(status_code=401, detail="Token admin tidak valid atau sudah kedaluwarsa")


@api_router.post("/admin/refresh-cache")
async def admin_refresh_cache(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    if _refresh_cache_lock.locked():
        return {
            "success": False,
            "message": "Refresh cache sedang berjalan. Silakan coba lagi dalam beberapa menit.",
        }
    async with _refresh_cache_lock:
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


@api_router.post("/admin/trigger-agent")
async def admin_trigger_agent(agent: str = Query(...), token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        from scheduler import (
            store_tradingview_to_mongo, store_macro_to_mongo, store_news_to_mongo,
            store_sector_predictions_to_mongo, store_stock_recommendations_to_mongo,
            store_order_book_to_mongo,
        )
        AGENTS = {
            "tradingview": store_tradingview_to_mongo,
            "macro": store_macro_to_mongo,
            "news_flow": store_news_to_mongo,
            "sector_predictions": store_sector_predictions_to_mongo,
            "stock_recommendations": store_stock_recommendations_to_mongo,
            "order_book": store_order_book_to_mongo,
        }
        func = AGENTS.get(agent)
        if not func:
            raise HTTPException(status_code=400, detail=f"Agent '{agent}' tidak dikenal")
        result = await func(require_db())
        return {"success": True, "agent": agent, "result": str(result)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gagal trigger agent '%s'", agent)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


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


@api_router.get("/admin/agent-status")
async def admin_get_agent_status(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    return {"success": True, "data": get_status_summary()}


@api_router.get("/admin/token")
async def admin_get_token() -> Dict[str, Any]:
    """Get a simple admin token for frontend use."""
    try:
        token = _create_admin_token()
        return {"success": True, "token": token}
    except Exception as e:
        logger.exception("Gagal membuat token admin")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/admin/cancel-scheduler")
async def admin_cancel_scheduler(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        from scheduler import cancel_scheduler
        cancelled = await cancel_scheduler()
        return {"success": True, "cancelled": cancelled}
    except Exception as e:
        logger.exception("Gagal membatalkan scheduler")
        raise HTTPException(status_code=500, detail=str(e)) from e


CACHE_DELETION_OPTIONS = ["tradingview", "macro", "news_flow", "sector_predictions", "stock_recommendations"]
ROOT_DIR = Path(__file__).parent
TV_CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
NEWS_CACHE_FILE = ROOT_DIR / "agent_cache" / "news_flow.json"
MACRO_CACHE_FILE = ROOT_DIR / "agent_cache" / "macro_data.json"
SECTOR_CACHE_FILE = ROOT_DIR / "agent_cache" / "sector_predictions.json"
STOCK_CACHE_FILE = ROOT_DIR / "agent_cache" / "stock_recommendations.json"


def _delete_file_cache(cache_key: str) -> bool:
    """Delete file cache for a given cache key. Returns True if successful."""
    file_map = {
        "tradingview": TV_CACHE_FILE,
        "news_flow": NEWS_CACHE_FILE,
        "macro": MACRO_CACHE_FILE,
        "sector_predictions": SECTOR_CACHE_FILE,
        "stock_recommendations": STOCK_CACHE_FILE,
    }
    file_path = file_map.get(cache_key)
    if file_path and file_path.exists():
        try:
            file_path.unlink()
            logger.info(f"Deleted file cache: {file_path}")
            return True
        except Exception as e:
            logger.warning(f"Failed to delete file cache {file_path}: {e}")
            return False
    return False


class CacheDeletionPayload(BaseModel):
    caches: List[str] = Field(default_factory=list)


@api_router.post("/admin/cache/delete")
async def admin_delete_cache(payload: CacheDeletionPayload, token: str = Query(...)) -> Dict[str, Any]:
    """Delete selected cache entries from MongoDB and file storage.
    
    Order book cache cannot be deleted via this endpoint.
    """
    verify_admin(token)
    
    invalid = [c for c in payload.caches if c not in CACHE_DELETION_OPTIONS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Cache tidak valid: {', '.join(invalid)}")
    
    if "order_book" in payload.caches:
        raise HTTPException(status_code=400, detail="Order book cache tidak dapat dihapus")
    
    results = {"mongo": [], "file": [], "errors": []}
    
    for cache_key in payload.caches:
        if cache_key == "stock_recommendations":
            mongo_ok = await delete_cached_sector_recommendations(db)
            if mongo_ok:
                results["mongo"].append(cache_key)
            else:
                results["errors"].append(f"{cache_key} (mongo)")
            
            file_ok = _delete_file_cache(cache_key)
            if file_ok:
                results["file"].append(cache_key)
            else:
                results["errors"].append(f"{cache_key} (file)")
        else:
            mongo_ok = await delete_cached(db, cache_key)
            if mongo_ok:
                results["mongo"].append(cache_key)
            else:
                results["errors"].append(f"{cache_key} (mongo)")
            
            file_ok = _delete_file_cache(cache_key)
            if file_ok:
                results["file"].append(cache_key)
            else:
                results["errors"].append(f"{cache_key} (file)")
        
        await cache_version_manager.reset_version(cache_key)
    
    return {
        "success": True,
        "message": f"Cache dihapus: {len(results['mongo'])} dari MongoDB, {len(results['file'])} dari file",
        "deleted_mongo": results["mongo"],
        "deleted_file": results["file"],
        "errors": results["errors"],
    }


@api_router.get("/processing-status")
async def processing_status() -> Dict[str, Any]:
    from scheduler import is_scheduler_running, current_run_id, check_and_release_stale_lock, get_scheduler_progress
    from agent_status import AGENT_STATUS

    await check_and_release_stale_lock()

    running = is_scheduler_running()
    progress = get_scheduler_progress() if running else {}
    return {
        "processing": running,
        "run_id": current_run_id() if running else None,
        "agents": {
            name: {"status": info["status"]}
            for name, info in AGENT_STATUS.items()
        },
        "scheduler_progress": progress if running else None,
    }


@api_router.get("/fine-tune/stats")
async def get_fine_tune_stats() -> Dict[str, Any]:
    try:
        raw_files = sorted(RAW_DIR.glob("*.jsonl"))
        raw_count = 0
        for f in raw_files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    raw_count += sum(1 for _ in fh)
            except Exception:
                pass

        prepared_files = sorted(PREPARED_DIR.glob("*_train.jsonl"))
        prepared_info = []
        for f in prepared_files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    cnt = sum(1 for _ in fh)
                prepared_info.append({"name": f.stem, "entries": cnt})
            except Exception:
                pass

        ratings_file = ROOT_DIR / "agent_cache" / "ratings.json"
        rating_count = 0
        up_count = 0
        if ratings_file.exists():
            try:
                with open(ratings_file, "r", encoding="utf-8") as f:
                    ratings_data = json.load(f)
                    rating_count = len(ratings_data)
                    up_count = sum(1 for r in ratings_data if r.get("rating") == 1)
            except Exception:
                pass

        return {
            "success": True,
            "stats": {
                "raw_log_files": len(raw_files),
                "raw_log_entries": raw_count,
                "prepared_datasets": prepared_info,
                "ratings_total": rating_count,
                "ratings_upvotes": up_count,
            },
            "model": {
                "base_model": os.environ.get("LLM_MODEL", "qwen/qwen3-32b"),
                "fine_tuned_model": FINETUNED_MODEL_ID or None,
                "fine_tune_enabled": FINETUNE_ENABLED,
                "traffic_percent": FINETUNE_TRAFFIC_PERCENT,
            },
        }
    except Exception as e:
        logger.exception("Gagal membaca fine-tune stats")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/admin/fine-tune/status")
async def admin_fine_tune_status(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        from fine_tuning.config import RAW_DIR, PREPARED_DIR
        raw_files = list(RAW_DIR.glob("*.jsonl"))
        total_raw = 0
        for f in raw_files:
            with open(f, "r", encoding="utf-8") as fh:
                total_raw += sum(1 for _ in fh)

        prepared = list(PREPARED_DIR.glob("*_train.jsonl"))
        latest_prepared = None
        if prepared:
            latest = max(prepared, key=lambda p: p.stat().st_mtime)
            with open(latest, "r", encoding="utf-8") as fh:
                latest_count = sum(1 for _ in fh)
            latest_prepared = {"name": latest.stem, "entries": latest_count}

        ratings_file = ROOT_DIR / "agent_cache" / "ratings.json"
        ratings_total = 0
        ratings_by_type: Dict[str, int] = {}
        if ratings_file.exists():
            with open(ratings_file, "r", encoding="utf-8") as f:
                ratings_data = json.load(f)
                ratings_total = len(ratings_data)
                for r in ratings_data:
                    at = r.get("agent_type", "unknown")
                    ratings_by_type[at] = ratings_by_type.get(at, 0) + 1

        return {
            "success": True,
            "raw_logs": {"files": len(raw_files), "total_entries": total_raw},
            "prepared_datasets": {
                "total": len(prepared),
                "latest": latest_prepared,
            },
            "ratings": {"total": ratings_total, "by_type": ratings_by_type},
            "model": {
                "base_model": os.environ.get("LLM_MODEL", "qwen/qwen3-32b"),
                "fine_tuned_model": FINETUNED_MODEL_ID or None,
                "fine_tune_enabled": FINETUNE_ENABLED,
                "traffic_percent": FINETUNE_TRAFFIC_PERCENT,
            },
        }
    except Exception as e:
        logger.exception("Gagal membaca status fine-tuning")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/admin/fine-tune/train")
async def admin_fine_tune_train(token: str = Query(...), dry_run: bool = Query(default=False)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        from fine_tuning.prepare_dataset import prepare
        from fine_tuning.train import train

        prep_result = prepare()
        if not prep_result.get("success"):
            return {"success": False, "error": prep_result.get("error", "Prepare dataset failed")}

        train_result = train(dataset_name=prep_result["dataset_name"], dry_run=dry_run)
        return {
            "success": True,
            "prepare_result": {
                "raw_entries": prep_result["total_raw"],
                "filtered": prep_result["total_filtered"],
                "train_count": prep_result["train_count"],
                "val_count": prep_result["val_count"],
            },
            "train_result": train_result,
            "dry_run": dry_run,
        }
    except Exception as e:
        logger.exception("Gagal menjalankan fine-tuning")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.post("/admin/playground")
async def admin_playground(payload: PlaygroundPayload, token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        # Mode 1: Agent-based (menggunakan pre-created Mistral agent)
        if payload.agent_key:
            from mistral_agent_manager import MistralAgentManager
            manager = MistralAgentManager()

            user_messages = payload.messages
            last_user_msg = user_messages[-1]["content"] if user_messages else ""
            inputs = {
                "message": last_user_msg,
                "instructions": payload.instructions or "",
                "response_format": payload.response_format,
            }

            result = manager.run(payload.agent_key, inputs=inputs)

            return {
                "success": True,
                "content": result.get("content", ""),
                "tool_calls": result.get("tool_calls", []),
                "conversation_id": result.get("conversation_id"),
                "mode": "agent",
            }

        # Mode 2: Chat completion langsung (playground bebas)
        from mistralai.client import Mistral

        api_key = os.environ.get("MISTRAL_API_KEY") or os.environ.get("LLM_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="MISTRAL_API_KEY tidak ditemukan")

        client = Mistral(api_key=api_key)

        tools = list(payload.tools)

        if payload.capability == "premium_search":
            tools.insert(0, {"type": "web_search_premium"})
        elif payload.capability == "search":
            tools.insert(0, {"type": "web_search"})
        elif payload.capability == "code":
            tools.insert(0, {"type": "code_interpreter"})
        elif payload.capability == "image":
            tools.insert(0, {"type": "image_generation"})

        messages = []
        if payload.instructions:
            messages.append({"role": "system", "content": payload.instructions})
        messages.extend(payload.messages)

        params = {
            "model": payload.model,
            "messages": messages,
            "temperature": payload.temperature,
            "top_p": payload.top_p,
        }

        if tools:
            params["tools"] = tools

        if payload.response_format:
            params["response_format"] = payload.response_format

        response = client.chat.complete(**params)
        choice = response.choices[0]
        msg = choice.message

        tool_calls = []
        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                })

        return {
            "success": True,
            "content": msg.content,
            "tool_calls": tool_calls,
            "finish_reason": choice.finish_reason,
            "mode": "chat",
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else None,
                "completion_tokens": response.usage.completion_tokens if response.usage else None,
                "total_tokens": response.usage.total_tokens if response.usage else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Gagal menjalankan playground")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/sector/predictions")
async def get_sector_predictions(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from sector_predictor_agent import load_cached_predictions, predict_sectors
        from scheduler import is_scheduler_running
        from llm_rate_limiter import global_llm_limiter

        if refresh:
            if is_scheduler_running():
                logger.info("Sector predictions: scheduler running, skip refresh, return cache")
                refresh = False
            else:
                llm_acquired = await global_llm_limiter.acquire()
                if not llm_acquired:
                    logger.warning("Sector predictions: LLM rate limit exceeded, skip refresh")
                    refresh = False
                else:
                    try:
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None, lambda: predict_sectors(refresh=True)
                        )
                        has_data = any(len(items) > 0 for items in result.get("predictions", {}).values())
                        if has_data:
                            await set_cached(db, "sector_predictions", result)
                            await cache_version_manager.increment_version("sector_predictions")
                            await global_llm_limiter.record_success()
                            logger.info("Sector predictions: refresh manual berhasil")
                            return {
                                "success": True,
                                "message": "Prediksi sektor berhasil diperbarui.",
                                "predictions": result.get("predictions", {}),
                                "generated_at": result.get("generated_at"),
                                "model": result.get("model"),
                                "from_cache": False,
                            }
                        else:
                            logger.warning("Sector predictions empty from Mistral, keeping old cache")
                            await global_llm_limiter.record_success()
                    except Exception as e:
                        logger.error(f"Sector predictions refresh gagal: {e}")
                        await global_llm_limiter.record_failure()
                    finally:
                        await global_llm_limiter.release()

        cached = await _get_cached_data("sector_predictions", load_cached_predictions)
        if cached:
            return {
                "success": True,
                "message": "Prediksi sektor dari cache.",
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


async def _fetch_current_price_async(ticker: str) -> Optional[float]:
    cache_key = f"price:{ticker}"
    cached = _stock_history_cache.get(cache_key)
    if cached:
        cached_time, cached_price = cached
        if time.time() - cached_time < 300:
            return cached_price
    try:
        tk = await asyncio.to_thread(yf.Ticker, f"{ticker}.JK")
        hist = await asyncio.to_thread(lambda: tk.history(period="1d"))
        if not hist.empty:
            price = round(float(hist["Close"].iloc[-1]), 2)
            _evict_stock_history_cache()
            _stock_history_cache[cache_key] = (time.time(), price)
            return price
        info = await asyncio.to_thread(lambda: tk.info)
        if info and "regularMarketPrice" in info:
            price = round(float(info["regularMarketPrice"]), 2)
            _evict_stock_history_cache()
            _stock_history_cache[cache_key] = (time.time(), price)
            return price
    except Exception:
        pass
    return None


async def _fetch_prices_parallel(tickers: List[str]) -> Dict[str, Optional[float]]:
    tasks = {t: _fetch_current_price_async(t) for t in tickers}
    results = await asyncio.gather(*tasks.values())
    return dict(zip(tasks.keys(), results))


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


async def _generate_order_book_snapshot() -> Dict[str, Any]:
    """Generate order book snapshot — append-only, buy_price never changes."""
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
        raise HTTPException(status_code=400, detail="Prediksi sektor belum tersedia.")

    existing_map = await _order_book_store.load_existing_order_map()

    all_new_tickers = set()
    timeframe_sectors = {}
    for tf in TIMEFRAME_DAYS:
        preds = predictions.get(tf, [])
        if not preds:
            continue
        top_sector = preds[0]
        sector_name = top_sector["sector"]

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

        for stock in stocks_data[:2]:
            key = (tf, stock["ticker"])
            if key not in existing_map:
                all_new_tickers.add(stock["ticker"])

        timeframe_sectors[tf] = {
            "sector": top_sector,
            "stocks": stocks_data[:2],
        }

    all_tickers = set(all_new_tickers)
    existing_tickers_to_update = set()
    for tf in TIMEFRAME_DAYS:
        for (ex_tf, ex_ticker), ex_stock in existing_map.items():
            if ex_tf == tf:
                existing_tickers_to_update.add(ex_ticker)
    all_tickers |= existing_tickers_to_update

    prices = await _fetch_prices_parallel(list(all_tickers))
    today = date.today()

    simulations = []
    for tf in TIMEFRAME_DAYS:
        existing_stocks = []
        new_stocks = []

        if tf in timeframe_sectors:
            info = timeframe_sectors[tf]
            top_sector = info["sector"]
            sector_name = top_sector["sector"]
            predicted_return = top_sector.get("predicted_return", 0)
            stocks_data = info["stocks"]
            buy_date = today.isoformat()
            sell_date = (today + timedelta(days=TIMEFRAME_DAYS[tf])).isoformat()
            pred_stock_tickers = {s["ticker"] for s in stocks_data[:2]}

            for stock in stocks_data[:2]:
                ticker = stock["ticker"]
                key = (tf, ticker)
                if key in existing_map:
                    frozen = dict(existing_map[key])
                    frozen_bp = frozen.get("buy_price")
                    if frozen_bp is not None:
                        live_price = prices.get(ticker)
                        if live_price is not None:
                            frozen["current_price"] = live_price
                            if frozen.get("status") == "open":
                                frozen["actual_return_pct"] = round(
                                    (live_price - frozen_bp) / frozen_bp * 100, 2
                                )

                        frozen_sell_date = frozen.get("sell_date", "")
                        if frozen_sell_date and date.today() > date.fromisoformat(frozen_sell_date):
                            if not frozen.get("actual_sell_price"):
                                actual = _fetch_price_at_date(ticker, frozen_sell_date)
                                if actual is not None:
                                    frozen["actual_sell_price"] = actual
                                    frozen["actual_return_pct"] = round(
                                        (actual - frozen_bp) / frozen_bp * 100, 2
                                    )
                                    frozen["status"] = "closed"

                        logger.debug(
                            "Order book [%s %s]: buy_price=Rp%s (frozen), current_price=Rp%s",
                            tf, ticker, frozen_bp, frozen.get("current_price"),
                        )
                    existing_stocks.append(frozen)
                else:
                    price = prices.get(ticker)
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

                    new_stocks.append({
                        "ticker": ticker,
                        "company_name": stock.get("company_name", ""),
                        "sector": sector_name,
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

            for ex_key, ex_stock in existing_map.items():
                if ex_key[0] == tf and ex_key[1] not in pred_stock_tickers:
                    existing_ticker = ex_key[1]
                    if ex_stock not in existing_stocks:
                        ex_frozen = dict(ex_stock)
                        ex_bp = ex_frozen.get("buy_price")
                        if ex_bp is not None:
                            live_price = prices.get(existing_ticker)
                            if live_price is not None:
                                ex_frozen["current_price"] = live_price
                                if ex_frozen.get("status") == "open":
                                    ex_frozen["actual_return_pct"] = round(
                                        (live_price - ex_bp) / ex_bp * 100, 2
                                    )
                            ex_sell_date = ex_frozen.get("sell_date", "")
                            if ex_sell_date and date.today() > date.fromisoformat(ex_sell_date):
                                if not ex_frozen.get("actual_sell_price"):
                                    actual = _fetch_price_at_date(existing_ticker, ex_sell_date)
                                    if actual is not None:
                                        ex_frozen["actual_sell_price"] = actual
                                        ex_frozen["actual_return_pct"] = round(
                                            (actual - ex_bp) / ex_bp * 100, 2
                                        )
                                        ex_frozen["status"] = "closed"
                        existing_stocks.append(ex_frozen)

            sector_block = {
                "name": sector_name,
                "rank": 1,
                "predicted_return": predicted_return,
                "confidence": top_sector.get("confidence"),
                "rationale": top_sector.get("rationale", ""),
            }
        else:
            sector_block = {
                "name": "N/A — Tidak ada prediksi",
                "rank": None,
                "predicted_return": 0,
                "confidence": None,
                "rationale": None,
            }
            for ex_key, ex_stock in existing_map.items():
                if ex_key[0] == tf:
                    ex_ticker = ex_key[1]
                    ex_frozen = dict(ex_stock)
                    ex_bp = ex_frozen.get("buy_price")
                    if ex_bp is not None:
                        live_price = prices.get(ex_ticker)
                        if live_price is not None:
                            ex_frozen["current_price"] = live_price
                            if ex_frozen.get("status") == "open":
                                ex_frozen["actual_return_pct"] = round(
                                    (live_price - ex_bp) / ex_bp * 100, 2
                                )
                        ex_sell_date = ex_frozen.get("sell_date", "")
                        if ex_sell_date and date.today() > date.fromisoformat(ex_sell_date):
                            if not ex_frozen.get("actual_sell_price"):
                                actual = _fetch_price_at_date(ex_ticker, ex_sell_date)
                                if actual is not None:
                                    ex_frozen["actual_sell_price"] = actual
                                    ex_frozen["actual_return_pct"] = round(
                                        (actual - ex_bp) / ex_bp * 100, 2
                                    )
                                    ex_frozen["status"] = "closed"
                    existing_stocks.append(ex_frozen)

        combined = existing_stocks + new_stocks
        combined.sort(key=lambda s: s.get("buy_date", ""), reverse=True)

        simulations.append({
            "timeframe": tf,
            "sector": sector_block,
            "stocks": combined,
        })

    # Snapshot of macro indicators
    macro_snapshot = {}
    try:
        from macro_agent import get_macro_indicators
        macro_data = get_macro_indicators()
        for ind in macro_data.get("indicators", []):
            macro_snapshot[ind["id"]] = ind.get("liveValue") or ind.get("value")
    except Exception:
        pass

    predictions_meta = predictions_data or {}
    snapshot = {
        "id": str(uuid.uuid4()),
        "generated_at": now_iso(),
        "snapshot_date": today.isoformat(),
        "predictions_used": {
            "generated_at": predictions_meta.get("generated_at"),
            "model": predictions_meta.get("model", "qwen/qwen3-32b"),
            "timeframes": list(predictions.keys()),
        },
        "simulations": simulations,
        "macro_snapshot": macro_snapshot,
        "model": predictions_meta.get("model", "qwen/qwen3-32b"),
        "version": 2,
    }
    return snapshot


_IDN_HOLIDAYS = {
    (1, 1),   # Tahun Baru Masehi
    (2, 17),  # Tahun Baru Imlek 2577
    (3, 20), (3, 21), (3, 22),  # Idul Fitri 1447 H (estimasi)
    (3, 28),  # Nyepi 1948 Saka
    (4, 3),   # Wafat Yesus Kristus / Good Friday
    (4, 5),   # Paskah
    (5, 1),   # Hari Buruh Internasional
    (5, 14),  # Kenaikan Yesus Kristus
    (5, 27),  # Idul Adha 1447 H (estimasi)
    (6, 1),   # Hari Lahir Pancasila
    (6, 16),  # Tahun Baru Islam 1449 H (estimasi)
    (8, 17),  # Hari Kemerdekaan RI
    (8, 25),  # Maulid Nabi Muhammad SAW (estimasi)
    (12, 25), # Hari Natal
}

def _is_idn_holiday(d: date) -> bool:
    return (d.month, d.day) in _IDN_HOLIDAYS

def _is_market_open() -> bool:
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    if _is_idn_holiday(now.date()):
        return False
    open_start = now.replace(hour=9, minute=0, second=0, microsecond=0)
    open_end = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return open_start <= now <= open_end

def _next_market_day_after(d: date) -> date:
    next_day = d + timedelta(days=1)
    while next_day.weekday() >= 5 or _is_idn_holiday(next_day):
        next_day += timedelta(days=1)
    return next_day

def _get_next_schedule_time() -> datetime:
    tz = pytz.timezone("Asia/Jakarta")
    now = datetime.now(tz)
    today = now.date()

    if now.weekday() >= 5 or _is_idn_holiday(today):
        next_day = _next_market_day_after(today)
        return tz.localize(datetime(next_day.year, next_day.month, next_day.day, 9, 0))

    today_0900 = tz.localize(datetime(today.year, today.month, today.day, 9, 0))
    today_1300 = tz.localize(datetime(today.year, today.month, today.day, 13, 0))
    today_1600 = tz.localize(datetime(today.year, today.month, today.day, 16, 0))

    if now < today_0900:
        return today_0900
    elif now < today_1300:
        return today_1300
    elif now < today_1600:
        next_day = _next_market_day_after(today)
        return tz.localize(datetime(next_day.year, next_day.month, next_day.day, 9, 0))
    else:
        next_day = _next_market_day_after(today)
        return tz.localize(datetime(next_day.year, next_day.month, next_day.day, 9, 0))


@api_router.get("/order-book/simulation")
async def get_order_book_simulation(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    market_open = _is_market_open()
    try:
        async with _order_book_lock:
            if refresh and not market_open:
                refresh = False

            if not refresh:
                latest = await _order_book_store.get_latest_snapshot()
                if latest:
                    return {
                        "success": True,
                        "simulations": latest.get("simulations", []),
                        "snapshot_id": latest["id"],
                        "generated_at": latest["generated_at"],
                        "market_open": market_open,
                        "from_cache": True,
                    }

            snapshot = await _generate_order_book_snapshot()
            await _order_book_store.append_snapshot(snapshot)

            return {
                "success": True,
                "simulations": snapshot["simulations"],
                "snapshot_id": snapshot["id"],
                "generated_at": snapshot["generated_at"],
                "market_open": market_open,
                "from_cache": False,
            }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gagal generate order book simulation")
        raise HTTPException(status_code=500, detail=f"Gagal: {str(exc)}") from exc


@api_router.get("/order-book/history")
async def get_order_book_history(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    try:
        result = await _order_book_store.get_history(limit=limit, offset=offset)
        return {
            "success": True,
            "data": result["data"],
            "total": result["total"],
            "offset": offset,
            "limit": limit,
        }
    except Exception as exc:
        logger.exception("Gagal mengambil riwayat order book")
        raise HTTPException(status_code=500, detail=f"Gagal: {str(exc)}") from exc


@api_router.get("/order-book/history/{snapshot_id}")
async def get_order_book_snapshot(snapshot_id: str) -> Dict[str, Any]:
    try:
        snapshot = await _order_book_store.get_snapshot_by_id(snapshot_id)
        if snapshot:
            return {"success": True, "data": snapshot}
        raise HTTPException(status_code=404, detail="Snapshot tidak ditemukan")
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Gagal mengambil snapshot order book")
        raise HTTPException(status_code=500, detail=f"Gagal: {str(exc)}") from exc


@api_router.get("/order-book/accuracy")
async def get_order_book_accuracy() -> Dict[str, Any]:
    try:
        closed_snapshots = await _order_book_store.get_all_snapshots()

        # Collect all closed positions across all snapshots
        closed_positions = []
        for snap in closed_snapshots:
            for sim in snap.get("simulations", []):
                for stock in sim.get("stocks", []):
                    if stock.get("status") == "closed" and stock.get("actual_return_pct") is not None:
                        closed_positions.append({
                            "snapshot_id": snap["id"],
                            "snapshot_date": snap.get("snapshot_date"),
                            "timeframe": sim["timeframe"],
                            "sector": sim["sector"]["name"],
                            "ticker": stock["ticker"],
                            "predicted_return_pct": stock["predicted_return_pct"],
                            "actual_return_pct": stock["actual_return_pct"],
                            "error_pct": round(stock["predicted_return_pct"] - stock["actual_return_pct"], 2),
                            "buy_date": stock["buy_date"],
                            "sell_date": stock["sell_date"],
                        })

        if not closed_positions:
            return {
                "success": True,
                "total_closed": 0,
                "message": "Belum ada posisi yang closed. Data akan terakumulasi seiring waktu.",
                "positions": [],
            }

        avg_error = round(sum(abs(p["error_pct"]) for p in closed_positions) / len(closed_positions), 2)
        avg_abs_predicted = round(sum(abs(p["predicted_return_pct"]) for p in closed_positions) / len(closed_positions), 2)
        avg_abs_actual = round(sum(abs(p["actual_return_pct"]) for p in closed_positions) / len(closed_positions), 2)

        return {
            "success": True,
            "total_closed": len(closed_positions),
            "total_snapshots": len(closed_snapshots),
            "average_error_pct": avg_error,
            "average_predicted_return_pct": avg_abs_predicted,
            "average_actual_return_pct": avg_abs_actual,
            "positions": closed_positions,
        }
    except Exception as exc:
        logger.exception("Gagal menghitung akurasi order book")
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

        cache_key = f"{ticker}:{period}"
        now = time.time()

        # Check in-memory cache first
        cached_entry = _stock_history_cache.get(cache_key)
        if cached_entry:
            cached_time, cached_data = cached_entry
            if now - cached_time < STOCK_HISTORY_CACHE_TTL:
                return cached_data

        async with _history_fetch_lock:
            # Double-check cache after lock
            cached_entry = _stock_history_cache.get(cache_key)
            if cached_entry:
                cached_time, cached_data = cached_entry
                if now - cached_time < STOCK_HISTORY_CACHE_TTL:
                    return cached_data

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

            result = {"success": True, "ticker": ticker, "prices": prices}
            _evict_stock_history_cache()
            _stock_history_cache[cache_key] = (time.time(), result)
            return result
    except Exception as exc:
        logger.warning(f"Gagal fetch history {ticker}: {exc}")
        return {"success": False, "ticker": ticker, "prices": []}


@api_router.get("/stocks/{ticker}/news")
async def get_stock_news(
    ticker: str,
    max_articles: int = Query(default=5, ge=1, le=20),
) -> Dict[str, Any]:
    try:
        from stock_recommender_agent import fetch_news_batch
        dummy_stock = {"ticker": ticker}
        news_map = await asyncio.to_thread(fetch_news_batch, [dummy_stock], 1, max_articles)
        articles = news_map.get(ticker, [])
        return {"success": True, "ticker": ticker, "news": articles}
    except Exception as exc:
        logger.warning(f"Gagal fetch news {ticker}: {exc}")
        return {"success": False, "ticker": ticker, "news": [], "error": str(exc)}


@api_router.get("/sector/{sector_name}/stocks")
async def get_sector_stock_recommendations(
    sector_name: str,
    limit: int = Query(default=10, ge=1, le=20),
) -> Dict[str, Any]:
    # Normalize legacy sector names
    from sector_constants import SECTOR_ALIASES
    sector_name = SECTOR_ALIASES.get(sector_name, sector_name)
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

        # No cache — cek apakah batch scheduler sedang berjalan
        from scheduler import get_scheduler_progress, AGENT_TIMEOUT
        from agent_status import AGENT_STATUS

        progress = get_scheduler_progress()
        stock_rec_status = AGENT_STATUS.get("stock_recommendations", {}).get("status", "unknown")

        if progress.get("running") or stock_rec_status == "running":
            estimated = progress.get("estimated_seconds_remaining", AGENT_TIMEOUT * 2)
            return {
                "success": False,
                "processing": True,
                "sector": sector_name,
                "run_id": progress.get("run_id"),
                "estimated_seconds_remaining": estimated,
                "recommendations": [],
                "message": (
                    f"Batch agent sedang menyusun rekomendasi saham untuk semua sektor. "
                    f"Estimasi selesai dalam ~{max(1, estimated // 60)} menit. "
                    f"Halaman akan merefresh otomatis."
                ),
            }

        return {
            "success": False,
            "processing": False,
            "sector": sector_name,
            "recommendations": [],
            "message": (
                "Rekomendasi saham belum tersedia. "
                "Sistem akan memperbarui secara otomatis sesuai jadwal. "
                "Admin dapat memicu generate manual melalui panel Admin."
            ),
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
    # Normalize legacy sector names
    from sector_constants import SECTOR_ALIASES
    sector_name = SECTOR_ALIASES.get(sector_name, sector_name)

    # Per-sector lock to prevent concurrent yfinance calls for same sector
    async with _scoring_locks_lock:
        if len(_scoring_locks) > _MAX_LOCK_DICT_SIZE:
            _scoring_locks.clear()
        if sector_name not in _scoring_locks:
            _scoring_locks[sector_name] = asyncio.Lock()

    async with _scoring_locks[sector_name]:
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
        from sector_predictor_agent import fetch_sector_data, compute_sector_averages
        from sector_constants import TV_TO_IDX_SECTOR
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
        cached = await _get_cached_data("tradingview", load_cached_data)
        records = cached.get("data", []) if cached else []

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
async def get_macro_indicators_endpoint(
    refresh: bool = Query(default=False),
) -> Dict[str, Any]:
    try:
        from macro_agent import (
            fetch_live_data_async, BASE_MACRO_DATA, now_iso, load_cache, save_cache as macro_save_cache,
        )
        from scheduler import is_scheduler_running

        if refresh:
            if is_scheduler_running():
                logger.info("Macro: scheduler running, skip refresh, return cache")
                refresh = False
            else:
                try:
                    live = await asyncio.wait_for(
                        fetch_live_data_async(),
                        timeout=120,
                    )
                    timestamp = now_iso()
                    indicators = []
                    for item in BASE_MACRO_DATA:
                        indicator = dict(item)
                        ind_id = indicator["id"]
                        if ind_id in live and live[ind_id] is not None:
                            live_val = live[ind_id]
                            indicator["liveValue"] = live_val
                            default_val = float(indicator["defaultValue"].replace(",", ""))
                            if default_val != 0:
                                indicator["change"] = round(
                                    ((live_val - default_val) / default_val) * 100, 2
                                )
                            if ind_id in ("usd_idr",):
                                indicator["value"] = f"{live_val:,.0f}"
                            elif ind_id in ("ihsg", "sp500"):
                                indicator["value"] = f"{live_val:,.1f}"
                            elif ind_id in ("nikkei", "hsi"):
                                indicator["value"] = f"{live_val:,.0f}"
                            elif ind_id == "oil_price":
                                indicator["value"] = f"${live_val:.2f}"
                            else:
                                indicator["value"] = str(live_val)
                        else:
                            indicator["value"] = indicator["defaultValue"]
                        indicator["updated_at"] = timestamp
                        indicators.append(indicator)

                    result = {
                        "indicators": indicators,
                        "total": len(indicators),
                    }
                    await set_cached(db, "macro", result)
                    macro_save_cache(indicators)
                    await cache_version_manager.increment_version("macro")
                    logger.info("Macro: refresh manual berhasil")
                    return {
                        "success": True,
                        "indicators": indicators,
                        "total": len(indicators),
                        "cached_at": timestamp,
                        "from_cache": False,
                    }
                except (asyncio.TimeoutError, Exception) as e:
                    logger.warning(f"Macro refresh gagal: {e}")

        cached = await _get_cached_data("macro", load_cache)
        if cached:
            return {
                "success": True,
                "indicators": cached.get("indicators", []),
                "total": cached.get("total", len(cached.get("indicators", []))),
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


# ===== Health Check & Monitoring Endpoints =====

@api_router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint untuk monitoring status sistem."""
    try:
        # Get circuit breaker status
        cb_status = await circuit_breaker_registry.get_all_status()
        
        # Get LLM limiter stats
        llm_stats = await global_llm_limiter.get_stats()
        
        # Get cache versions
        cache_versions = await cache_version_manager.get_all_versions()
        
        # Get yfinance cache stats
        yf_stats = yfinance_session_manager.get_cache_stats()
        
        # Get agent status
        agent_status = get_status_summary()
        
        return {
            "success": True,
            "timestamp": now_iso(),
            "system": {
                "circuit_breakers": cb_status,
                "llm_rate_limiter": llm_stats,
                "cache_versions": cache_versions,
                "yfinance_cache": yf_stats,
                "agents": agent_status,
            },
        }
    except Exception as e:
        logger.exception("Health check failed")
        raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}") from e


# ===== Admin Monitoring Endpoints =====

@api_router.get("/admin/metrics")
async def admin_get_metrics(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        all_metrics = await agent_metrics.get_all_metrics()
        agents = {}
        for agent_name in all_metrics:
            stats = await agent_metrics.get_agent_stats(agent_name)
            agents[agent_name] = stats
        return {"success": True, "agents": agents}
    except Exception as e:
        logger.exception("Gagal membaca metrics")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/admin/circuit-breakers")
async def admin_get_circuit_breakers(token: str = Query(...)) -> Dict[str, Any]:
    verify_admin(token)
    try:
        status = await circuit_breaker_registry.get_all_status()
        return {"success": True, "circuit_breakers": status}
    except Exception as e:
        logger.exception("Gagal membaca circuit breaker status")
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/admin/logs")
async def admin_get_logs(
    token: str = Query(...),
    lines: int = Query(default=100, ge=10, le=1000),
    level: str = Query(default=None, description="Filter: ERROR, WARNING, INFO, DEBUG"),
) -> Dict[str, Any]:
    verify_admin(token)
    try:
        if not LOG_FILE.exists():
            return {"success": True, "lines": [], "total_lines": 0}

        raw = LOG_FILE.read_text(encoding="utf-8")
        all_lines = raw.splitlines()
        total = len(all_lines)

        result = all_lines[-lines:] if lines > 0 else all_lines

        if level:
            level_upper = level.upper()
            result = [l for l in result if level_upper in l]

        return {
            "success": True,
            "lines": result,
            "total_lines": total,
            "returned": len(result),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@api_router.get("/admin/llm-audit")
async def admin_get_llm_audit(
    token: str = Query(...),
    limit: int = Query(default=50, ge=1, le=500),
) -> Dict[str, Any]:
    verify_admin(token)
    from llm_audit_log import llm_audit_log

    try:
        calls = await llm_audit_log.get_recent_calls(limit=limit)
        stats = await llm_audit_log.get_stats()
        return {
            "success": True,
            "calls": calls,
            "stats": stats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Include router — HARUS setelah semua @api_router.get/post definitions
app.include_router(api_router)

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting server on port {port}...")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=False)
