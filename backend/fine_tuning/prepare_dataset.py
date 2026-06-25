import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fine_tuning.config import RAW_DIR, PREPARED_DIR

logger = logging.getLogger(__name__)

RATINGS_FILE = Path(__file__).parent.parent / "agent_cache" / "ratings.json"


def load_ratings() -> Dict[str, int]:
    if not RATINGS_FILE.exists():
        return {}
    try:
        with open(RATINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        result: Dict[str, int] = {}
        for r in data:
            key = f"{r.get('agent_type', '')}:{r.get('target_id', '')}"
            if key not in result:
                result[key] = r.get("rating", 0)
        return result
    except (json.JSONDecodeError, Exception) as e:
        logger.warning(f"Gagal load ratings: {e}")
        return {}


def load_raw_logs() -> List[Dict[str, Any]]:
    records = []
    for path in sorted(RAW_DIR.glob("*.jsonl")):
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception as e:
            logger.warning(f"Gagal membaca {path}: {e}")
    return records


def filter_with_ratings(
    records: List[Dict[str, Any]], ratings: Dict[str, int], min_rating: int = 1
) -> List[Dict[str, Any]]:
    selected = []
    for rec in records:
        agent_type = rec.get("agent_type", "")
        target_id = rec.get("metadata", {}).get("sector", "")
        if not target_id:
            if agent_type == "news_analysis":
                target_id = "ringkasan"
            else:
                continue
        key = f"{agent_type}:{target_id}"
        rating = ratings.get(key, 0)
        if rating >= min_rating:
            selected.append(rec)
    return selected


def to_mistral_format(
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    result = []
    for rec in records:
        prompt = rec.get("prompt", "").strip()
        response = rec.get("response", "").strip()
        if not prompt or not response:
            continue
        result.append({
            "messages": [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        })
    return result


def split_dataset(
    data: List[Dict[str, Any]], train_ratio: float = 0.8, seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    shuffled = list(data)
    random.seed(seed)
    random.shuffle(shuffled)
    split = int(len(shuffled) * train_ratio)
    return shuffled[:split], shuffled[split:]


def prepare(
    min_rating: int = 1,
    train_ratio: float = 0.8,
    output_name: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    name = output_name or f"ft_dataset_{timestamp}"

    raw_logs = load_raw_logs()
    logger.info(f"Loaded {len(raw_logs)} raw log entries")

    ratings = load_ratings()
    logger.info(f"Loaded {len(ratings)} ratings")

    filtered = filter_with_ratings(raw_logs, ratings, min_rating)
    logger.info(f"Filtered to {len(filtered)} positively-rated entries")

    if not filtered:
        logger.warning("No entries with positive ratings. Using all raw logs as fallback.")
        filtered = raw_logs

    formatted = to_mistral_format(filtered)
    logger.info(f"Formatted {len(formatted)} entries for Mistral")

    if len(formatted) < 2:
        logger.error(f"Too few samples ({len(formatted)}) for training")
        return {"success": False, "error": "Insufficient training data", "total": len(formatted)}

    train_data, val_data = split_dataset(formatted, train_ratio)
    logger.info(f"Split: {len(train_data)} train + {len(val_data)} validation")

    train_path = PREPARED_DIR / f"{name}_train.jsonl"
    val_path = PREPARED_DIR / f"{name}_val.jsonl"

    with open(train_path, "w", encoding="utf-8") as f:
        for entry in train_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    with open(val_path, "w", encoding="utf-8") as f:
        for entry in val_data:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    logger.info(f"Saved train: {train_path} ({len(train_data)} entries)")
    logger.info(f"Saved val: {val_path} ({len(val_data)} entries)")

    return {
        "success": True,
        "dataset_name": name,
        "total_raw": len(raw_logs),
        "total_filtered": len(filtered),
        "total_formatted": len(formatted),
        "train_count": len(train_data),
        "val_count": len(val_data),
        "train_path": str(train_path),
        "val_path": str(val_path),
        "ratings_used": len(ratings),
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = prepare()
    print(json.dumps(result, indent=2, ensure_ascii=False))
