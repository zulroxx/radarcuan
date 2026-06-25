import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

CEREBRAS_API_KEY = os.environ.get("CEREBRAS_API_KEY", "")
CEREBRAS_MODEL = os.environ.get("CEREBRAS_MODEL", "gpt-oss-120b")
CEREBRAS_MAX_TOKENS = int(os.environ.get("CEREBRAS_MAX_TOKENS", "32000"))
CEREBRAS_BASE_URL = "https://api.cerebras.ai/v1"

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not CEREBRAS_API_KEY:
            raise ValueError("CEREBRAS_API_KEY tidak diset di .env")
        _client = OpenAI(api_key=CEREBRAS_API_KEY, base_url=CEREBRAS_BASE_URL)
    return _client


def reset_client():
    global _client
    _client = None


def is_available() -> bool:
    return bool(CEREBRAS_API_KEY)


def generate_batch(
    system_prompt: str,
    user_text: str,
    temperature: float = 0.3,
    max_retries: int = 2,
) -> Optional[str]:
    """Call Cerebras chat completions API with rate limit handling.

    Args:
        system_prompt: System instructions for the model.
        user_text: User message content (JSON data, etc.).
        temperature: Sampling temperature.
        max_retries: Number of retries on 429 before returning None.

    Returns:
        Response content string on success.
        None if rate limited after all retries — caller should fallback.
        Raises on non-rate-limit errors.
    """
    for attempt in range(max_retries):
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=CEREBRAS_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=temperature,
                max_tokens=CEREBRAS_MAX_TOKENS,
            )
            return resp.choices[0].message.content

        except Exception as e:
            err = str(e)
            is_rate_limit = (
                "429" in err
                or "rate limit" in err.lower()
                or "too many requests" in err.lower()
                or "rate_limit" in err.lower()
            )

            if is_rate_limit:
                if attempt < max_retries - 1:
                    delay = 5.0 * (2 ** attempt)
                    logger.warning(
                        "Cerebras rate limited (attempt %d/%d), retry in %.0fs",
                        attempt + 1, max_retries, delay,
                    )
                    time.sleep(delay)
                else:
                    logger.warning(
                        "Cerebras rate limited after %d retries — falling back to Mistral",
                        max_retries,
                    )
                    return None
            else:
                logger.error("Cerebras API error (non-rate-limit): %s", e)
                raise

    return None
