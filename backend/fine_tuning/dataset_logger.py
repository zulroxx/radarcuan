import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fine_tuning.config import LOG_ENABLED, LOG_BATCH_SIZE, current_log_path

logger = logging.getLogger(__name__)

_local = threading.local()


def _get_buffer() -> List[Dict[str, Any]]:
    if not hasattr(_local, "log_buffer"):
        _local.log_buffer = []
    return _local.log_buffer


def _flush_buffer(log_path) -> None:
    buffer = _get_buffer()
    if not buffer:
        return
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as f:
            for entry in buffer:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        logger.debug(f"Flushed {len(buffer)} log entries to {log_path}")
        buffer.clear()
    except Exception as e:
        logger.warning(f"Gagal flush log buffer: {e}")


def log_llm_call(
    agent_type: str,
    prompt: str,
    response: str,
    model: str,
    metadata: Optional[Dict[str, Any]] = None,
    flush: bool = False,
) -> None:
    if not LOG_ENABLED:
        return

    entry = {
        "prompt": prompt,
        "response": response,
        "agent_type": agent_type,
        "model": model,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
    }

    buffer = _get_buffer()
    buffer.append(entry)

    if flush or len(buffer) >= LOG_BATCH_SIZE:
        _flush_buffer(current_log_path())


def flush_log() -> None:
    _flush_buffer(current_log_path())
