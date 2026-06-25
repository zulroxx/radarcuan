"""Simple JSON‑schema validation for LLM responses.

We keep the schemas minimal – only the required top‑level keys that the
frontend expects.  If a response fails validation we log the error and let the
caller decide the fallback strategy.
"""
import json
import logging
from typing import Any, Dict

try:
    from jsonschema import Draft7Validator, ValidationError
except ImportError:  # pragma: no cover
    # jsonschema is declared in requirements.txt; this guard is only for safety.
    raise RuntimeError("jsonschema library is required for response validation")

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Schemas (as plain Python dicts).  They mirror the "OUTPUT FORMAT RULES"
# sections used by the three agents.
# ---------------------------------------------------------------------------
NEWS_ANALYST_SCHEMA = {
    "type": "object",
    "required": [
        "ringkasan_1hari",
        "ringkasan_terbaru",
        "sektor_diuntungkan",
        "sektor_digdaya_waspada",
        "indikator_kunci",
        "rekomendasi_umum",
    ],
    "properties": {
        "ringkasan_1hari": {"type": "string"},
        "ringkasan_terbaru": {"type": "string"},
        "sektor_diuntungkan": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
        },
        "sektor_digdaya_waspada": {
            "type": "array",
            "minItems": 1,
            "items": {"type": "object"},
        },
        "indikator_kunci": {
            "type": "array",
            "minItems": 3,
            "items": {"type": "object"},
        },
        "rekomendasi_umum": {"type": "string"},
    },
    "additionalProperties": True,
}

STOCK_RECOMMENDER_SINGLE_SCHEMA = {
    "type": "object",
    "required": ["recommendations"],
    "properties": {
        "recommendations": {
            "type": "array",
            "items": {"type": "object"},
        }
    },
    "additionalProperties": True,
}

STOCK_RECOMMENDER_BATCH_SCHEMA = {
    "type": "object",
    "required": ["recommendations"],
    "properties": {
        "recommendations": {
            "type": "object",
            "additionalProperties": {
                "type": "object",
                "required": ["recommendations"],
                "properties": {
                    "recommendations": {
                        "type": "array",
                        "items": {"type": "object"},
                    }
                },
                "additionalProperties": True,
            },
        }
    },
    "additionalProperties": True,
}

_VALIDATORS = {
    "ihsg-news-analyst": Draft7Validator(NEWS_ANALYST_SCHEMA),
    "ihsg-stock-recommender": Draft7Validator(STOCK_RECOMMENDER_SINGLE_SCHEMA),
    "ihsg-stock-recommender-batch": Draft7Validator(STOCK_RECOMMENDER_BATCH_SCHEMA),
}


def validate_response(agent_name: str, payload: Dict[str, Any]) -> bool:
    """Validate *payload* for the given *agent_name*.

    Returns ``True`` if validation passes, otherwise logs the first error and
    returns ``False``.
    """
    validator = _VALIDATORS.get(agent_name)
    if not validator:
        logger.warning("No validator configured for %s – skipping validation", agent_name)
        return True
    errors = list(validator.iter_errors(payload))
    if errors:
        err: ValidationError = errors[0]
        logger.error(
            "Validation failed for %s – %s (at %s)",
            agent_name,
            err.message,
            ".".join(str(p) for p in err.path),
        )
        return False
    return True
