"""Cache versioning system untuk memastikan konsistensi antar AI Agent."""
import asyncio
import time
from typing import Dict, Optional, Any

class CacheVersionManager:
    """Manages cache versions to ensure consistency between AI agents."""
    
    def __init__(self):
        self._versions: Dict[str, int] = {}
        self._last_update: Dict[str, float] = {}
        self._lock = asyncio.Lock()
        # Default versions
        self._versions["tradingview"] = 0
        self._versions["macro"] = 0
        self._versions["news_flow"] = 0
        self._versions["sector_predictions"] = 0
        self._versions["stock_recommendations"] = 0
        self._versions["order_book"] = 0
    
    async def increment_version(self, cache_key: str) -> int:
        """Increment version for a cache key and return new version."""
        async with self._lock:
            self._versions[cache_key] = self._versions.get(cache_key, 0) + 1
            self._last_update[cache_key] = time.time()
            return self._versions[cache_key]
    
    async def get_version(self, cache_key: str) -> int:
        """Get current version for a cache key."""
        async with self._lock:
            return self._versions.get(cache_key, 0)
    
    async def get_all_versions(self) -> Dict[str, int]:
        """Get all current versions."""
        async with self._lock:
            return dict(self._versions)
    
    async def is_fresh(self, cache_key: str, expected_version: int, ttl_seconds: float = 3600.0) -> bool:
        """Check if cache version still valid (not expired)."""
        async with self._lock:
            current_version = self._versions.get(cache_key, 0)
            if current_version != expected_version:
                return False
            last_upd = self._last_update.get(cache_key, 0)
            return (time.time() - last_upd) < ttl_seconds
    
    async def reset_version(self, cache_key: str) -> None:
        """Reset version for a cache key."""
        async with self._lock:
            self._versions[cache_key] = 0
            self._last_update[cache_key] = time.time()


# Global instance
cache_version_manager = CacheVersionManager()