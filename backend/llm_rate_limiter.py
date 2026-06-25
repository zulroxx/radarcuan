"""Global LLM rate limiter untuk mencegah overload ke LLM provider."""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class GlobalLLMLimiter:
    """Global rate limiter untuk semua LLM calls.
    
    Membatasi max concurrent LLM calls ke provider (default: 3).
    Mencegah rate limit errors dan memastikan fair usage.
    """
    
    def __init__(self, max_concurrent: int = 3):
        self.max_concurrent = max_concurrent
        self._current = 0
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._lock = asyncio.Lock()
        self._total_calls = 0
        self._failed_calls = 0
        self._last_request_time: Optional[float] = None
        self._request_times: list = []
        self._max_requests_per_minute = 20  # Soft limit
    
    async def acquire(self) -> bool:
        """Acquire semaphore untuk LLM call."""
        await self._semaphore.acquire()
        async with self._lock:
            self._current += 1
            self._total_calls += 1
            now = time.time()
            self._request_times.append(now)
            # Clean old requests (> 1 menit)
            self._request_times = [t for t in self._request_times if now - t < 60]
            self._last_request_time = now
        return True
    
    async def release(self) -> None:
        """Release semaphore after LLM call."""
        async with self._lock:
            self._current = max(0, self._current - 1)
    
    async def record_success(self) -> None:
        """Record successful LLM call."""
        async with self._lock:
            self._failed_calls = max(0, self._failed_calls - 1)
    
    async def record_failure(self) -> None:
        """Record failed LLM call."""
        async with self._lock:
            self._failed_calls += 1
    
    async def is_rate_limited(self) -> bool:
        """Check jika melebihi rate limit per minute."""
        async with self._lock:
            now = time.time()
            recent = [t for t in self._request_times if now - t < 60]
            return len(recent) >= self._max_requests_per_minute
    
    @property
    def current_concurrent(self) -> int:
        return self._current
    
    @property
    def total_calls(self) -> int:
        return self._total_calls
    
    @property
    def failed_calls(self) -> int:
        return self._failed_calls
    
    @property
    def success_rate(self) -> float:
        if self._total_calls == 0:
            return 100.0
        return ((self._total_calls - self._failed_calls) / self._total_calls) * 100
    
    async def get_stats(self) -> dict:
        """Get statistics untuk monitoring."""
        async with self._lock:
            return {
                "current_concurrent": self._current,
                "max_concurrent": self.max_concurrent,
                "total_calls": self._total_calls,
                "failed_calls": self._failed_calls,
                "success_rate": self.success_rate,
                "requests_last_minute": len(self._request_times),
                "max_requests_per_minute": self._max_requests_per_minute,
            }


# Global instance
global_llm_limiter = GlobalLLMLimiter(max_concurrent=3)
