"""Tests for response validation and fallback logic.

We cover:
- Successful validation for each agent schema.
- Failure cases (missing required keys, too few items).
- Integration test for ``stock_recommender_agent.recommend_stocks`` ensuring that an invalid
  Mistral payload triggers the fallback path (empty recommendations).
"""

import json
from unittest import mock

import pytest

from backend.response_validator import (
    validate_response,
)

# ---------------------------------------------------------------------------
# Helper payloads
# ---------------------------------------------------------------------------
VALID_NEWS_PAYLOAD = {
    "ringkasan_1hari": "summary",
    "ringkasan_terbaru": "latest",
    "sektor_diuntungkan": [{"sektor": "Keuangan", "alasan": "...", "sentimen": "positif", "subsektor": ""}],
    "sektor_digdaya_waspada": [{"sektor": "Energi", "alasan": "..."}],
    "indikator_kunci": [
        {"nama": "Inflasi", "kondisi": "Terkendali", "dampak": "positif"},
        {"nama": "BI Rate", "kondisi": "Turun", "dampak": "positif"},
        {"nama": "USD/IDR", "kondisi": "Melemah", "dampak": "positif"},
    ],
    "rekomendasi_umum": "Diversify",
}

VALID_SINGLE_PAYLOAD = {"recommendations": [{"ticker": "BBCA", "companyName": "Bank BCA"}]}

VALID_BATCH_PAYLOAD = {
    "recommendations": {
        "Finance": {"recommendations": [{"ticker": "BBCA"}]},
        "Energy": {"recommendations": []},
    }
}

# ---------------------------------------------------------------------------
# Validation tests
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "payload, agent_name",
    [
        (VALID_NEWS_PAYLOAD, "ihsg-news-analyst"),
        (VALID_SINGLE_PAYLOAD, "ihsg-stock-recommender"),
        (VALID_BATCH_PAYLOAD, "ihsg-stock-recommender-batch"),
    ],
)
def test_validate_success(payload, agent_name):
    """All valid payloads must pass validation."""
    assert validate_response(agent_name, payload) is True


def test_validate_missing_key_news():
    bad = VALID_NEWS_PAYLOAD.copy()
    del bad["ringkasan_1hari"]  # required key missing
    assert validate_response("ihsg-news-analyst", bad) is False


def test_validate_too_few_items_news():
    bad = VALID_NEWS_PAYLOAD.copy()
    bad["sektor_diuntungkan"] = []  # minItems = 1
    assert validate_response("ihsg-news-analyst", bad) is False


def test_validate_missing_top_key_single():
    # Empty dict fails because required top‑level key "recommendations" is missing
    assert validate_response("ihsg-stock-recommender", {}) is False

# ---------------------------------------------------------------------------
# Integration test – stock_recommender_agent fallback on invalid Mistral response
# ---------------------------------------------------------------------------
def test_stock_recommender_fallback_on_invalid_mistral(monkeypatch):
    """When Mistral returns malformed JSON, the agent should fall back to empty result."""
    from backend import stock_recommender_agent as agent

    # Mock Mistral manager to return an invalid JSON string
    mock_manager = mock.Mock()
    mock_manager.run.return_value = {"content": "{invalid json"}
    monkeypatch.setitem(agent.__dict__, "MistralAgentManager", lambda *args, **kwargs: mock_manager)

    # Stub out external helpers to avoid network calls
    monkeypatch.setattr(agent, "get_stocks_in_sector", lambda sector: [{"ticker": "BBCA"}])
    monkeypatch.setattr(agent, "fetch_news_batch", lambda stocks: {"BBCA": []})

    # Force parse_llm_response to raise on the malformed content
    monkeypatch.setattr(agent, "parse_llm_response", lambda content: json.loads(content))

    result = agent.recommend_stocks(sector_name="Finance", limit=1, refresh=True, use_mistral=True)
    assert result["recommendations"] == []
    assert result["sector"] == "Finance"
    assert result["model"] == agent.LLM_MODEL
