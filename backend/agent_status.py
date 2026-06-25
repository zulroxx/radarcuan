import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

AGENT_NAMES = [
    "scheduler",
    "tradingview",
    "macro",
    "news_flow",
    "sector_predictions",
    "stock_recommendations",
    "order_book",
]

AGENT_STATUS: Dict[str, Dict[str, Any]] = {
    name: {
        "status": "unknown",
        "last_run": None,
        "last_error": None,
        "last_error_at": None,
    }
    for name in AGENT_NAMES
}


def update_agent_status(agent: str, status: str, error: Optional[str] = None) -> None:
    if agent not in AGENT_STATUS:
        logger.warning(f"Unknown agent: {agent}")
        return
    AGENT_STATUS[agent]["status"] = status
    AGENT_STATUS[agent]["last_run"] = datetime.now(timezone.utc).isoformat()
    if error:
        AGENT_STATUS[agent]["last_error"] = error
        AGENT_STATUS[agent]["last_error_at"] = datetime.now(timezone.utc).isoformat()


def get_cache_age(path: Optional[Path]) -> Optional[int]:
    if path is None or not path.exists():
        return None
    try:
        mtime = os.path.getmtime(path)
        age_seconds = time.time() - mtime
        return int(age_seconds)
    except OSError:
        return None


def get_status_summary() -> Dict[str, Any]:
    from pathlib import Path
    ROOT_DIR = Path(__file__).parent

    cache_paths = {
        "tradingview": ROOT_DIR / "tradingview_cache.json",
        "macro": ROOT_DIR / "agent_cache" / "macro_data.json",
        "news_flow": ROOT_DIR / "agent_cache" / "news_flow.json",
        "sector_predictions": ROOT_DIR / "agent_cache" / "sector_predictions.json",
        "stock_recommendations": ROOT_DIR / "agent_cache" / "stock_recommendations.json",
        "order_book": ROOT_DIR / "agent_cache" / "order_book_history.json",
    }

    result = {}
    for agent_name in AGENT_NAMES:
        entry = dict(AGENT_STATUS[agent_name])
        entry["cache_age_seconds"] = get_cache_age(cache_paths.get(agent_name))
        result[agent_name] = entry
    return result
