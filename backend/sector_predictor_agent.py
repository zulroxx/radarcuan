import json
import logging
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from agent_status import update_agent_status
from fine_tuning.dataset_logger import log_llm_call

from sector_constants import TV_TO_IDX_SECTOR, IDX_SECTORS, SECTOR_ALIASES

logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("requests").setLevel(logging.ERROR)

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

ROOT_DIR = Path(__file__).parent
CACHE_DIR = ROOT_DIR / "agent_cache"
CACHE_DIR.mkdir(exist_ok=True)
SECTOR_CACHE_FILE = CACHE_DIR / "sector_predictions.json"
CACHE_TTL_SECONDS = 3600
TV_CACHE_FILE = ROOT_DIR / "tradingview_cache.json"
TV_CACHE_USABLE_SECONDS = 3600

LLM_MODEL = os.environ.get("LLM_MODEL", "qwen/qwen3-32b")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_idn_market_open() -> bool:
    now = datetime.now(timezone(timedelta(hours=7)))
    if now.weekday() >= 5:
        return False
    return 9 <= now.hour < 15


def load_cached_predictions() -> Optional[Dict[str, Any]]:
    if not SECTOR_CACHE_FILE.exists():
        return None
    try:
        with open(SECTOR_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        cached_time = datetime.fromisoformat(cached.get('cached_at', ''))
        age = (datetime.now(timezone.utc) - cached_time).total_seconds()
        if is_idn_market_open():
            if age < CACHE_TTL_SECONDS:
                _normalize_timeframe_keys(cached)
                return cached
        else:
            _normalize_timeframe_keys(cached)
            return cached
    except (json.JSONDecodeError, ValueError, KeyError):
        pass
    return None


def _normalize_timeframe_keys(data: Dict[str, Any]) -> None:
    """Normalize timeframe keys in-place (1_month -> 1M, etc.)."""
    predictions = data.get("predictions", {})
    TIMEFRAME_ALIASES = {
        "1_month": "1M", "1_bulan": "1M",
        "3_months": "3M", "3_bulan": "3M",
        "6_months": "6M", "6_bulan": "6M",
        "12_months": "12M", "12_bulan": "12M",
    }
    for old_key, new_key in TIMEFRAME_ALIASES.items():
        if old_key in predictions:
            predictions[new_key] = predictions.pop(old_key)


def save_cache(data: Dict[str, Any]) -> None:
    cache = {'cached_at': now_iso(), **data}
    with open(SECTOR_CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def load_tv_data_from_cache() -> Optional[List[Dict[str, Any]]]:
    if not TV_CACHE_FILE.exists():
        return None
    try:
        with open(TV_CACHE_FILE, 'r', encoding='utf-8') as f:
            cached = json.load(f)
        records = cached.get('data', [])
        if not records:
            return None
        return records
    except (json.JSONDecodeError, ValueError, KeyError):
        return None


def compute_sector_averages(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    sector_data: Dict[str, Dict[str, Any]] = {}
    for r in records:
        sec = r.get("sector", "Lainnya")
        if sec not in sector_data:
            sector_data[sec] = {
                "count": 0, "avg_per": [], "avg_pbv": [], "avg_roe": [],
                "avg_revenue_growth": [], "avg_eps_growth": [], "avg_dividend_yield": [],
                "avg_debt_to_equity": [], "avg_score": [],
            }
        sd = sector_data[sec]
        sd["count"] += 1
        for k, v in [("avg_per", r.get("per")), ("avg_pbv", r.get("pbv")), ("avg_roe", r.get("roe")),
                     ("avg_revenue_growth", r.get("revenue_growth")), ("avg_eps_growth", r.get("eps_growth")),
                     ("avg_dividend_yield", r.get("dividend_yield")), ("avg_debt_to_equity", r.get("debt_to_equity"))]:
            if v is not None:
                sd[k].append(v)
        score_val = (r.get("analysis") or {}).get("investmentScore")
        if score_val is not None:
            sd["avg_score"].append(score_val)
    result = {}
    for sec, sd in sector_data.items():
        result[sec] = {
            key: round(sum(vals) / len(vals), 1) if vals else None
            for key, vals in [
                ("count", [sd["count"]]), ("avg_per", sd["avg_per"]), ("avg_pbv", sd["avg_pbv"]),
                ("avg_roe", sd["avg_roe"]), ("avg_revenue_growth", sd["avg_revenue_growth"]),
                ("avg_eps_growth", sd["avg_eps_growth"]), ("avg_dividend_yield", sd["avg_dividend_yield"]),
                ("avg_debt_to_equity", sd["avg_debt_to_equity"]), ("avg_score", sd["avg_score"]),
            ]
        }
        result[sec]["count"] = sd["count"]
    return result


def fetch_sector_data() -> Dict[str, Any]:
    records = load_tv_data_from_cache()
    if records:
        logger.info("TV data loaded from cache")
        return compute_sector_averages(records)
    logger.info("TV cache miss, fetching fresh...")
    try:
        backend_dir = Path(__file__).parent
        import sys
        if str(backend_dir) not in sys.path:
            sys.path.insert(0, str(backend_dir))
        from tradingview_agent import fetch_and_analyze_tradingview_screen
        records, _, _ = fetch_and_analyze_tradingview_screen(limit=500)
        if records:
            return compute_sector_averages(records)
    except Exception as e:
        logger.warning(f"TV fetch failed: {e}")
    return {}


_json_decoder = json.JSONDecoder(strict=False)


def _extract_first_json(text: str) -> str:
    """Extract first complete JSON object/array from text, handling nested brackets."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(line for line in lines if not line.startswith("```"))
    text = text.strip()

    try:
        obj, end = _json_decoder.raw_decode(text)
        return text[:end]
    except json.JSONDecodeError:
        pass

    start = text.find("{")
    if start == -1:
        start = text.find("[")
    if start == -1:
        return text

    depth = 0
    in_str = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == '\\':
            escape = True
            continue
        if ch == '"':
            in_str = not in_str
            continue
        if in_str:
            continue
        if ch == '{' or ch == '[':
            depth += 1
        elif ch == '}' or ch == ']':
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return text[start:]


def _repair_json(json_str: str) -> str:
    """Fix common JSON truncation: unterminated strings + missing closing brackets."""
    if json_str.count('"') % 2 != 0:
        json_str += '"'
    ob = json_str.count('{') - json_str.count('}')
    ab = json_str.count('[') - json_str.count(']')
    if ob > 0:
        json_str += '}' * ob
    if ab > 0:
        json_str += ']' * ab
    return json_str


def parse_llm_response(content: str) -> Dict[str, Any]:
    json_str = _extract_first_json(content)
    for attempt in range(5):
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            if attempt == 0:
                try:
                    return _json_decoder.decode(json_str)
                except json.JSONDecodeError:
                    import re
                    json_str = re.sub(r',\s*\}', '}', json_str)
                    json_str = re.sub(r',\s*\]', ']', json_str)
            elif attempt in (1, 2):
                json_str = _repair_json(json_str)
            elif attempt == 3:
                try:
                    obj, end = _json_decoder.raw_decode(json_str)
                    logger.info("raw_decode recovered valid JSON prefix (len=%d)", end)
                    return obj
                except json.JSONDecodeError:
                    raise


def predict_sectors(refresh: bool = False) -> Dict[str, Any]:
    if not refresh:
        cached = load_cached_predictions()
        if cached:
            update_agent_status("sector_predictions", "ok")
            return cached

    logger.info("Generating sector predictions...")
    tv_data = fetch_sector_data()

    content = None
    used_mistral = False

    # Try Mistral agent, then fallback LLM if needed
    try:
        from mistral_agent_manager import MistralAgentManager
        manager = MistralAgentManager()
        inputs = {
            "sector_data": tv_data,
            "valid_sectors": IDX_SECTORS,
            "sector_mapping": TV_TO_IDX_SECTOR,
            "task": "Prediksi 10 sektor IDX terbaik per timeframe (1M, 3M, 6M, 12M) dengan urutan berbeda setiap timeframe. Gunakan nama sektor dari valid_sectors, bukan dari sector_data.",
        }
        response = manager.run(
            "sector_predictor",
            inputs=inputs,
            max_function_calls=5,
            timeout_ms=120000,
        )
        content = response.get("content")
        if content:
            try:
                # Parse the response; on failure we treat it as invalid and fall back to cache/LLM
                parsed = parse_llm_response(content)
                used_mistral = True
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.error(
                    "Mistral agent returned invalid JSON: %s\nlen=%d last_200=%s",
                    e, len(content), content[-200:]
                )
                # Invalidate content so fallback logic runs and clear parsed
                content = None
                parsed = {}
    except Exception as e:
        logger.warning(f"Mistral agent gagal ({e}), fallback ke LLM client...")

    # Mistral agent gagal, gunakan cache atau kosong
    if not content:
        logger.warning("Mistral agent gagal untuk sector prediction, fallback ke cache")
        update_agent_status("sector_predictions", "error", "Mistral agent failed")
        cached = load_cached_predictions()
        if cached:
            return cached
        return {
            "predictions": {},
            "generated_at": now_iso(),
            "model": LLM_MODEL,
            "method": "enhanced_fundamental_macro",
            "error": "Mistral agent failed",
        }

    if not isinstance(parsed, dict):
        logger.warning("LLM returned non-dict JSON (type=%s), predictions empty", type(parsed).__name__)
        predictions = {}
    else:
        predictions = parsed.get("predictions", {})
        if not predictions:
            _known_tf = ["1_month", "3_months", "6_months", "12_months",
                         "1_bulan", "3_bulan", "6_bulan", "12_bulan",
                         "1M", "3M", "6M", "12M"]
            if any(k in parsed for k in _known_tf):
                predictions = {k: parsed[k] for k in _known_tf if k in parsed}
    _normalize_timeframe_keys({"predictions": predictions})

    parsed_keys = list(parsed.keys()) if isinstance(parsed, dict) else []
    logger.info("Mistral sector response type=%s, predictions keys=%s, parsed keys=%s",
                type(content).__name__, list(predictions.keys()), parsed_keys)

    log_llm_call(
        agent_type="sector_prediction",
        prompt=content[:500] + "...",
        response=content,
        model="mistral-agent-sector" if used_mistral else LLM_MODEL,
        metadata={
            "n_sectors": len(tv_data),
        },
    )

    # Normalize and validate sector names
    for timeframe in predictions:
        for entry in predictions[timeframe]:
            old = entry.get("sector")
            if old in SECTOR_ALIASES:
                entry["sector"] = SECTOR_ALIASES[old]
            elif old in TV_TO_IDX_SECTOR:
                entry["sector"] = TV_TO_IDX_SECTOR[old]
            elif old not in IDX_SECTORS:
                logger.warning(f"Sector '{old}' tidak dikenal, mapping ke 'Lainnya'")
                entry["sector"] = "Lainnya"

    # Enforce top-3 uniqueness across timeframes
    pred_keys = list(predictions.keys())
    for i in range(len(pred_keys)):
        for j in range(i + 1, len(pred_keys)):
            secs_i = [p.get("sector") for p in predictions.get(pred_keys[i], [])[:3]]
            secs_j = [p.get("sector") for p in predictions.get(pred_keys[j], [])[:3]]
            if secs_i == secs_j:
                logger.warning(
                    f"Top 3 sama antara {pred_keys[i]} dan {pred_keys[j]}: {secs_i}. "
                    f"Menggeser sektor di {pred_keys[j]}..."
                )
                seen = set(secs_i)
                shifted = predictions.get(pred_keys[j], [])
                for k, sec in enumerate(shifted):
                    if k < 3:
                        continue
                    if sec.get("sector") not in seen:
                        shifted.insert(0, shifted.pop(k))
                        break

    result = {
        "predictions": predictions,
        "generated_at": now_iso(),
        "model": LLM_MODEL,
        "method": "enhanced_fundamental_macro",
    }

    # Only cache non-empty predictions
    has_data = any(len(items) > 0 for items in predictions.values())
    if has_data:
        save_cache(result)
        update_agent_status("sector_predictions", "ok")
    else:
        logger.warning("predict_sectors: predictions empty, NOT saving to cache")
        update_agent_status("sector_predictions", "error", "Empty predictions")
    return result


def get_predictions_by_timeframe(timeframe: str = None, refresh: bool = False) -> Dict[str, Any]:
    valid = ["1M", "3M", "6M", "12M"]
    result = predict_sectors(refresh=refresh)
    predictions = result.get("predictions", {})
    if timeframe and timeframe in valid:
        result["predictions"] = {timeframe: predictions.get(timeframe, [])}
    return result
