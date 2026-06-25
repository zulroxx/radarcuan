import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 14400  # 4 hours

COLLECTIONS = {
    "tradingview": "cache_tradingview",
    "macro": "cache_macro",
    "news": "cache_news",
    "news_flow": "cache_news",
    "sector_predictions": "cache_sector_predictions",
    "stock_recommendations": "cache_stock_recommendations",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def get_cached(db, cache_key: str) -> Optional[Dict[str, Any]]:
    """Get cached data from MongoDB. Returns None if not found or stale."""
    collection_name = COLLECTIONS.get(cache_key)
    if not collection_name or db is None:
        return None
    try:
        doc = await db[collection_name].find_one({"_id": "main"})
        if not doc:
            return None
        cached_at = doc.get("cached_at", "")
        if cached_at:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)).total_seconds()
            if age < CACHE_TTL_SECONDS:
                doc.pop("_id", None)
                doc["from_cache"] = True
                return doc
    except Exception as e:
        logger.warning(f"MongoDB cache read error for {cache_key}: {e}")
    return None


async def set_cached(db, cache_key: str, data: Dict[str, Any]) -> None:
    """Store data in MongoDB cache."""
    collection_name = COLLECTIONS.get(cache_key)
    if not collection_name or db is None:
        return
    try:
        data["cached_at"] = now_iso()
        await db[collection_name].replace_one(
            {"_id": "main"},
            data,
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"MongoDB cache write error for {cache_key}: {e}")


async def get_cached_sector_recommendations(db, sector_name: str) -> Optional[Dict[str, Any]]:
    """Get cached stock recommendations for a specific sector."""
    if db is None:
        return None
    try:
        doc = await db["cache_stock_recommendations"].find_one({"_id": sector_name.lower()})
        if not doc:
            return None
        cached_at = doc.get("cached_at", "")
        if cached_at:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(cached_at)).total_seconds()
            if age < CACHE_TTL_SECONDS:
                doc.pop("_id", None)
                doc["from_cache"] = True
                return doc
    except Exception as e:
        logger.warning(f"MongoDB cache read error for sector {sector_name}: {e}")
    return None


async def set_cached_sector_recommendations(db, sector_name: str, data: Dict[str, Any]) -> None:
    """Store stock recommendations for a sector in MongoDB."""
    if db is None:
        return
    try:
        data["_id"] = sector_name.lower()
        data["cached_at"] = now_iso()
        await db["cache_stock_recommendations"].replace_one(
            {"_id": sector_name.lower()},
            data,
            upsert=True,
        )
    except Exception as e:
        logger.warning(f"MongoDB cache write error for sector {sector_name}: {e}")


async def delete_cached(db, cache_key: str) -> bool:
    """Delete cached data from MongoDB. Returns True if successful."""
    collection_name = COLLECTIONS.get(cache_key)
    if not collection_name or db is None:
        return False
    try:
        result = await db[collection_name].delete_many({})
        logger.info(f"Deleted {result.deleted_count} entries from MongoDB cache '{cache_key}'")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete MongoDB cache for {cache_key}: {e}")
        return False


async def delete_cached_sector_recommendations(db) -> bool:
    """Delete all sector stock recommendations from MongoDB."""
    if db is None:
        return False
    try:
        result = await db["cache_stock_recommendations"].delete_many({})
        logger.info(f"Deleted {result.deleted_count} entries from MongoDB cache 'stock_recommendations'")
        return True
    except Exception as e:
        logger.warning(f"Failed to delete MongoDB stock recommendations cache: {e}")
        return False
