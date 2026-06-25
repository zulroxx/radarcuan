import os
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).parent
DATASET_DIR = ROOT_DIR / "dataset"
RAW_DIR = DATASET_DIR / "raw"
PREPARED_DIR = DATASET_DIR / "prepared"
SEED_DIR = DATASET_DIR / "seed"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PREPARED_DIR.mkdir(parents=True, exist_ok=True)
SEED_DIR.mkdir(parents=True, exist_ok=True)

LOG_ENABLED = os.environ.get("FINETUNE_LOG_ENABLED", "true").lower() == "true"
LOG_BATCH_SIZE = int(os.environ.get("FINETUNE_LOG_BATCH_SIZE", "10"))

FINETUNE_ENABLED = os.environ.get("FINETUNE_ENABLED", "false").lower() == "true"
FINETUNED_MODEL_ID = os.environ.get("FINETUNED_MODEL_ID", "")
FINETUNE_TRAFFIC_PERCENT = int(os.environ.get("FINETUNE_TRAFFIC_PERCENT", "0"))


def today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def current_log_path() -> Path:
    return RAW_DIR / f"train_{today_str()}.jsonl"
