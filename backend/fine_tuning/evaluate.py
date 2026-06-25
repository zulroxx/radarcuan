import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from mistralai.client import Mistral

from fine_tuning.config import PREPARED_DIR

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-medium-latest")
FINETUNED_MODEL_ID = os.environ.get("FINETUNED_MODEL_ID", "")

IDX_SECTORS = {
    "Energi", "Bahan Baku", "Industri", "Konsumer Non-Primer", "Konsumer",
    "Kesehatan", "Keuangan", "Teknologi", "Infrastruktur", "Transportasi & Logistik",
    "Telekomunikasi", "Jasa & Perdagangan", "Distribusi", "Lainnya",
}

RECOMMENDATIONS = {"Strong Buy", "Buy", "Hold", "Sell", "Strong Sell"}


def get_client() -> Mistral:
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise ValueError("LLM_API_KEY not set")
    return Mistral(api_key=api_key, server_url=os.environ.get("LLM_BASE_URL", "https://api.mistral.ai"))


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(line for line in lines if not line.startswith("```"))
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        return None
    json_str = text[start : end + 1]
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        json_str = re.sub(r",\s*}", "}", json_str)
        json_str = re.sub(r",\s*]", "]", json_str)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return None


def evaluate_json_validity(content: str) -> bool:
    return extract_json(content) is not None


def evaluate_sector_names(prediction: Dict[str, Any]) -> Tuple[int, int]:
    valid = 0
    total = 0
    predictions = prediction.get("predictions", {})
    for timeframe in predictions:
        for entry in predictions[timeframe]:
            total += 1
            if entry.get("sector") in IDX_SECTORS:
                valid += 1
    return valid, total


def evaluate_recommendations(
    recs: Dict[str, Any],
) -> Tuple[int, int, int]:
    valid_rec = 0
    valid_score = 0
    total = 0
    for r in recs.get("recommendations", []):
        total += 1
        if r.get("recommendation") in RECOMMENDATIONS:
            valid_rec += 1
        score = r.get("score")
        if isinstance(score, (int, float)) and 0 <= score <= 100:
            valid_score += 1
    return valid_rec, valid_score, total


def evaluate_model(
    model: str,
    test_prompts: List[Dict[str, Any]],
    sample_size: int = 10,
) -> Dict[str, Any]:
    client = get_client()
    prompts = test_prompts[:sample_size]

    results = []
    valid_json_count = 0
    valid_sector_count = 0
    total_sector_count = 0
    valid_rec_count = 0
    valid_score_count = 0
    total_rec_count = 0
    total_tokens = 0

    for i, item in enumerate(prompts):
        prompt = item["messages"][0]["content"]
        try:
            response = client.chat.complete(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=16000,
                response_format={"type": "json_object"},
            )
            content = response.choices[0].message.content
            usage = response.usage
            tokens = (usage.prompt_tokens if usage else 0) + (usage.completion_tokens if usage else 0)
            total_tokens += tokens

            is_valid_json = evaluate_json_validity(content)
            if is_valid_json:
                valid_json_count += 1

            parsed = extract_json(content)
            if parsed:
                if "predictions" in parsed:
                    v, t = evaluate_sector_names(parsed)
                    valid_sector_count += v
                    total_sector_count += t
                if "recommendations" in parsed:
                    vr, vs, tr = evaluate_recommendations(parsed)
                    valid_rec_count += vr
                    valid_score_count += vs
                    total_rec_count += tr

            results.append(
                {
                    "index": i,
                    "valid_json": is_valid_json,
                    "tokens": tokens,
                    "valid_sectors": v if parsed and "predictions" in parsed else None,
                    "total_sectors": t if parsed and "predictions" in parsed else None,
                    "content_preview": content[:100],
                }
            )
        except Exception as e:
            results.append({"index": i, "error": str(e)})

    json_rate = valid_json_count / len(prompts) * 100 if prompts else 0
    sector_accuracy = valid_sector_count / total_sector_count * 100 if total_sector_count else 0
    rec_valid_rate = valid_rec_count / total_rec_count * 100 if total_rec_count else 0
    avg_tokens = total_tokens / len(prompts) if prompts else 0

    return {
        "model": model,
        "samples": len(prompts),
        "json_validity_rate": round(json_rate, 1),
        "sector_name_accuracy": round(sector_accuracy, 1),
        "recommendation_valid_rate": round(rec_valid_rate, 1),
        "avg_tokens_per_call": round(avg_tokens, 0),
        "valid_json_count": valid_json_count,
        "valid_sector_count": valid_sector_count,
        "total_sector_count": total_sector_count,
        "valid_rec_count": valid_rec_count,
        "total_rec_count": total_rec_count,
        "details": results,
    }


def compare(
    test_prompts: Optional[List[Dict[str, Any]]] = None,
    sample_size: int = 10,
    base_model: str = LLM_MODEL,
    finetuned_model: str = FINETUNED_MODEL_ID,
) -> Dict[str, Any]:
    if not test_prompts:
        prepared = sorted(PREPARED_DIR.glob("*_val.jsonl"))
        if not prepared:
            raise FileNotFoundError("No validation dataset found. Run prepare_dataset.py first.")
        test_prompts = []
        with open(prepared[-1], "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    test_prompts.append(json.loads(line))
        logger.info(f"Loaded {len(test_prompts)} test samples from {prepared[-1]}")

    base_result = evaluate_model(base_model, test_prompts, sample_size)
    logger.info(f"Base model {base_model} evaluation complete")

    ft_result = None
    if finetuned_model:
        try:
            ft_result = evaluate_model(finetuned_model, test_prompts, sample_size)
            logger.info(f"Fine-tuned model {finetuned_model} evaluation complete")
        except Exception as e:
            logger.warning(f"Fine-tuned model evaluation failed: {e}")
            ft_result = {"model": finetuned_model, "error": str(e)}

    comparison = {
        "base_model": base_result,
        "finetuned_model": ft_result,
        "sample_size": sample_size,
        "improvement": None,
    }

    if ft_result and "error" not in ft_result:
        comparison["improvement"] = {
            "json_validity_rate": round(ft_result["json_validity_rate"] - base_result["json_validity_rate"], 1),
            "sector_name_accuracy": round(ft_result["sector_name_accuracy"] - base_result["sector_name_accuracy"], 1),
            "avg_tokens_per_call": round(base_result["avg_tokens_per_call"] - ft_result["avg_tokens_per_call"], 0),
        }

    return comparison


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    result = compare(sample_size=5)
    print(json.dumps(result, indent=2, ensure_ascii=False))
