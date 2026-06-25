import asyncio
import logging
import re
import time
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_RETRIES = 3
DEFAULT_BASE_DELAY = 1.0

NON_RETRYABLE_PATTERNS = [
    re.compile(r"\b40[1347]\b"),
    re.compile(r"413"),
    re.compile(r"service_tier_capacity_exceeded"),
    re.compile(r"invalid_api_key", re.IGNORECASE),
    re.compile(r"insufficient_quota", re.IGNORECASE),
]


def _is_retryable(e: Exception) -> bool:
    msg = str(e)
    if any(p.search(msg) for p in NON_RETRYABLE_PATTERNS):
        return False
    return True


def _get_retry_delay(attempt: int, base_delay: float, e: Exception) -> float:
    msg = str(e)
    # 429 rate limit — wait longer
    if re.search(r"\b429\b", msg) or re.search(r"too many requests", msg, re.IGNORECASE):
        return base_delay * (4 ** attempt)
    return base_delay * (2 ** attempt)


def sync_rate_delay(seconds: float = 1.0) -> None:
    if seconds > 0:
        time.sleep(seconds)


async def async_rate_delay(seconds: float = 1.0) -> None:
    if seconds > 0:
        await asyncio.sleep(seconds)


def call_with_retry(
    func: Callable[..., T],
    *args: Any,
    max_retries: int = DEFAULT_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    **kwargs: Any,
) -> T:
    last_exc = None
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                if not _is_retryable(e):
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed with non-retryable error: {e}. "
                        f"Skipping remaining retries."
                    )
                    raise
                delay = _get_retry_delay(attempt, base_delay, e)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
    raise last_exc


async def async_call_with_retry(
    func: Callable[..., Any],
    *args: Any,
    max_retries: int = DEFAULT_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    **kwargs: Any,
) -> Any:
    last_exc = None
    for attempt in range(max_retries):
        try:
            result = func(*args, **kwargs)
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            last_exc = e
            if attempt < max_retries - 1:
                if not _is_retryable(e):
                    logger.warning(
                        f"Attempt {attempt + 1}/{max_retries} failed with non-retryable error: {e}. "
                        f"Skipping remaining retries."
                    )
                    raise
                delay = _get_retry_delay(attempt, base_delay, e)
                logger.warning(
                    f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay:.1f}s..."
                )
                await asyncio.sleep(delay)
    raise last_exc
