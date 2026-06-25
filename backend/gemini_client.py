import logging
import os
import time
from typing import Optional

from dotenv import load_dotenv
from pathlib import Path
from openai import OpenAI

load_dotenv(Path(__file__).parent / '.env')

logger = logging.getLogger(__name__)

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
GITHUB_MODEL = os.environ.get("GITHUB_MODEL", "microsoft/Phi-4-mini-reasoning")
GITHUB_BASE_URL = "https://models.github.ai/inference"

_client = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        if not GITHUB_TOKEN:
            raise ValueError("GITHUB_TOKEN tidak diset")
        _client = OpenAI(api_key=GITHUB_TOKEN, base_url=GITHUB_BASE_URL)
    return _client


def reset_client():
    global _client
    _client = None


def generate_content(system_prompt: str, user_text: str, max_retries: int = 3) -> Optional[str]:
    for attempt in range(max_retries):
        try:
            client = get_client()
            resp = client.chat.completions.create(
                model=GITHUB_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                temperature=0.2,
                max_tokens=4096,
            )
            return resp.choices[0].message.content
        except Exception as e:
            err = str(e)
            is_quota = "429" in err or "rate" in err.lower()
            if is_quota and attempt < max_retries - 1:
                delay = 10.0 * (2 ** attempt)
                logger.warning(
                    f"github-models rate limited (attempt {attempt+1}/{max_retries}), "
                    f"retry in {delay:.0f}s"
                )
                time.sleep(delay)
            else:
                logger.error(f"github-models API error: {e}")
                return None
    return None


def is_available() -> bool:
    return bool(GITHUB_TOKEN)
