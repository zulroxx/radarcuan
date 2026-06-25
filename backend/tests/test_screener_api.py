import os
from typing import Any, Dict, Optional

import pytest
import requests
from dotenv import load_dotenv


_frontend_env = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", ".env")
if os.path.exists(_frontend_env):
    load_dotenv(_frontend_env)
BASE_URL: Optional[str] = os.environ.get("REACT_APP_BACKEND_URL")


@pytest.fixture(scope="session")
def api_client() -> requests.Session:
    """Shared API client for screener backend endpoint validation."""
    if not BASE_URL:
        pytest.skip("REACT_APP_BACKEND_URL is missing in environment")

    session = requests.Session()
    session.headers.update({"Content-Type": "application/json"})
    return session


# Module coverage: health/root, collection summary.
# Tests that write to DB (feedback/waitlist) are excluded — they insert real data
# when run against a live backend. Only read-only tests are included here.

def test_api_root_returns_active_message(api_client):
    response = api_client.get(f"{BASE_URL}/api/")

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert data["message"] == "IHSG Smart Screener API aktif"


def test_collection_summary_has_expected_shape(api_client: requests.Session) -> None:
    response = api_client.get(f"{BASE_URL}/api/collections/summary")

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert "feedback_count" in data and isinstance(data["feedback_count"], int)
    assert "waitlist_count" in data and isinstance(data["waitlist_count"], int)
    assert data["feedback_count"] >= 0
    assert data["waitlist_count"] >= 0