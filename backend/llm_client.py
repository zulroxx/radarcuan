import json
import os
import logging
from typing import Any, Dict, List, Optional

from openai import OpenAI

logger = logging.getLogger(__name__)

INPUT_LIMIT = 16000


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val else default


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    return int(val) if val else default


def _env_str(key: str, default: Optional[str]) -> Optional[str]:
    val = os.environ.get(key)
    return val if val else default


def _env_json(key: str, default: Any = None) -> Any:
    val = os.environ.get(key)
    return json.loads(val) if val else default


def _truncate_prompt(messages: List[Dict[str, str]], max_output: int):
    limit = _env_int("LLM_INPUT_LIMIT", INPUT_LIMIT)
    MIN_FOOTER = 600
    MIN_HEADER = 200
    for _ in range(10):
        total = sum(len(m.get("content", "")) for m in messages) // 3 + max_output
        if total <= limit:
            return
        excess = (total - limit) * 3
        last = messages[-1]
        content = last.get("content", "")
        if len(content) <= excess + MIN_FOOTER:
            for m in reversed(messages):
                c = m.get("content", "")
                if len(c) > excess + MIN_FOOTER:
                    last = m
                    content = c
                    break
            else:
                last = messages[-1]
                content = last.get("content", "")
                excess = max(0, len(content) - 400)
                MIN_FOOTER = 0
        cut_end = max(0, len(content) - MIN_FOOTER)
        cut_start = max(MIN_HEADER, len(content) - excess - MIN_FOOTER)
        if cut_start >= cut_end:
            last["content"] = content[:max(200, len(content) - excess)] + "\n[DATA TRUNCATED]"
            continue
        newline = content.find("\n", cut_start)
        if newline > MIN_HEADER and newline < cut_end:
            cut_start = newline + 1
        last["content"] = content[:cut_start] + "\n[DATA TRUNCATED]\n" + content[cut_end:]


def get_llm_client() -> OpenAI:
    api_key = (
        os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("GROQ_API_KEY")
    )
    if not api_key:
        raise ValueError(
            "LLM_API_KEY / OPENROUTER_API_KEY / GROQ_API_KEY tidak ditemukan"
        )
    base_url = os.environ.get("LLM_BASE_URL")
    if base_url:
        return OpenAI(api_key=api_key, base_url=base_url)
    return OpenAI(api_key=api_key)


def llm_chat_complete(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.3,
    max_tokens: int = 16000,
) -> Any:
    output_tokens = _env_int("LLM_MAX_TOKENS", max_tokens)
    _truncate_prompt(messages, output_tokens)
    params: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": _env_float("LLM_TEMPERATURE", temperature),
        "max_tokens": output_tokens,
        "top_p": _env_float("LLM_TOP_P", 1.0),
        "stream": False,
    }
    stop = _env_json("LLM_STOP", None)
    if stop is not None:
        params["stop"] = stop
    response_format = _env_json("LLM_RESPONSE_FORMAT", None)
    if response_format is not None:
        params["response_format"] = response_format
    try:
        return client.chat.completions.create(**params)
    except Exception as e:
        error_str = str(e).lower()
        if response_format is not None and "response_format" in error_str:
            logger.warning("response_format didukung, fallback polos: %s", e)
            params.pop("response_format", None)
            return client.chat.completions.create(**params)
        raise
