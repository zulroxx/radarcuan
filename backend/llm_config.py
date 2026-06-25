"""Central configuration for LLM model selection and max token limits.

All agents should call ``get_model(agent_name)`` to obtain the model name and the
max_tokens that must be passed to the Mistral console (or any other provider).
"""
import os

DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "qwen/qwen3-32b")

# Max tokens required by each agent (as documented in the change‑request).
MAX_TOKENS = {
    "ihsg-news-analyst": 32000,
    "ihsg-stock-recommender": 32000,
    "ihsg-stock-recommender-batch": 32000,
}

def get_model(agent_name: str) -> dict:
    """Return a dict with ``model`` and ``max_tokens`` for the given agent.

    If the agent is unknown, fallback to ``DEFAULT_LLM_MODEL`` and a safe
    token value (4096).
    """
    return {
        "model": DEFAULT_LLM_MODEL,
        "max_tokens": MAX_TOKENS.get(agent_name, 4096),
    }
