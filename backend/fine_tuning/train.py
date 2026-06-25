import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from mistralai.client import Mistral

from fine_tuning.config import PREPARED_DIR

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

FINETUNE_MODEL = os.environ.get("FINETUNE_BASE_MODEL", "mistral-medium-latest")
FINETUNE_STEPS = int(os.environ.get("FINETUNE_STEPS", "100"))
FINETUNE_LEARNING_RATE = float(os.environ.get("FINETUNE_LEARNING_RATE", "0.0001"))


def get_client() -> Mistral:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY not set")
    return Mistral(api_key=api_key, server_url=os.environ.get("LLM_BASE_URL", "https://api.mistral.ai"))


def upload_file(client: Mistral, file_path: Path, purpose: str = "fine-tune") -> str:
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    logger.info(f"Uploading {file_path}...")
    with open(file_path, "rb") as f:
        uploaded = client.files.upload(file={"file": f, "purpose": purpose})
    file_id = uploaded.id
    logger.info(f"Uploaded file ID: {file_id}")
    return file_id


def wait_file_ready(client: Mistral, file_id: str, timeout_sec: int = 120) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        file_info = client.files.retrieve(file_id=file_id)
        if file_info.status == "ready":
            return True
        time.sleep(5)
    return False


def start_fine_tuning(
    train_file_id: str,
    val_file_id: Optional[str] = None,
    model: str = FINETUNE_MODEL,
    steps: int = FINETUNE_STEPS,
    learning_rate: float = FINETUNE_LEARNING_RATE,
    suffix: Optional[str] = None,
) -> str:
    client = get_client()
    params: Dict[str, Any] = {
        "model": model,
        "training_files": [train_file_id],
        "hyperparameters": {
            "training_steps": steps,
            "learning_rate": learning_rate,
        },
    }
    if val_file_id:
        params["validation_files"] = [val_file_id]
    if suffix:
        params["suffix"] = suffix

    logger.info(f"Starting fine-tuning job with params: {json.dumps(params, default=str)}")
    job = client.fine_tuning.jobs.create(**params)
    job_id = job.id
    logger.info(f"Fine-tuning job created: {job_id}")
    return job_id


def monitor_job(client: Mistral, job_id: str, poll_interval: int = 30) -> Dict[str, Any]:
    logger.info(f"Monitoring job {job_id}...")
    while True:
        job = client.fine_tuning.jobs.get(job_id=job_id)
        status = job.status
        logger.info(f"Job status: {status}")
        if status in ("SUCCESS", "FAILED", "CANCELLED"):
            result = {
                "id": job_id,
                "status": status,
                "model": getattr(job, "fine_tuned_model", None),
                "error": getattr(job, "error", None),
            }
            if status == "SUCCESS":
                logger.info(f"Fine-tuning complete! Model: {result['model']}")
            else:
                logger.error(f"Fine-tuning failed: {result.get('error')}")
            return result
        time.sleep(poll_interval)


def train(
    train_file: Optional[str] = None,
    val_file: Optional[str] = None,
    dataset_name: Optional[str] = None,
    suffix: Optional[str] = None,
    monitor: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if dry_run:
        suffix = suffix or "ihsg-dry-run"
        logger.info(f"DRY RUN: Would fine-tune {FINETUNE_MODEL} with suffix '{suffix}'")
        logger.info(f"  train_file: {train_file}")
        logger.info(f"  val_file: {val_file}")
        logger.info(f"  steps: {FINETUNE_STEPS}, lr: {FINETUNE_LEARNING_RATE}")
        return {"success": True, "dry_run": True, "model": FINETUNE_MODEL, "suffix": suffix}

    client = get_client()

    _train_file = train_file
    _val_file = val_file

    if not _train_file:
        if dataset_name:
            _train_file = str(PREPARED_DIR / f"{dataset_name}_train.jsonl")
            _val_file = _val_file or str(PREPARED_DIR / f"{dataset_name}_val.jsonl")
        else:
            prepared = sorted(PREPARED_DIR.glob("*_train.jsonl"))
            if not prepared:
                raise FileNotFoundError("No prepared dataset found. Run prepare_dataset.py first.")
            latest = prepared[-1]
            _train_file = str(latest)
            val_name = latest.stem.replace("_train", "_val")
            _val_file = str(PREPARED_DIR / f"{val_name}.jsonl")

    logger.info(f"Using train: {_train_file}")
    logger.info(f"Using val: {_val_file}")

    train_id = upload_file(client, Path(_train_file))
    val_id = upload_file(client, Path(_val_file)) if _val_file and Path(_val_file).exists() else None

    if not wait_file_ready(client, train_id):
        raise TimeoutError("Training file not ready within timeout")
    if val_id and not wait_file_ready(client, val_id):
        raise TimeoutError("Validation file not ready within timeout")

    default_suffix = suffix or f"ihsg-{dataset_name}" if dataset_name else "ihsg"
    job_id = start_fine_tuning(train_id, val_id, suffix=default_suffix)

    if monitor:
        result = monitor_job(client, job_id)
        return result

    return {"success": True, "job_id": job_id}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys

    if "--dry-run" in sys.argv:
        result = train(dry_run=True)
    else:
        result = train()
    print(json.dumps(result, indent=2, ensure_ascii=False))
