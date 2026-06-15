import os
import uuid
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


# Module coverage: health/root, feedback persistence, waitlist upsert, collection summary.
def test_api_root_returns_active_message(api_client):
    response = api_client.get(f"{BASE_URL}/api/")

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert data["message"] == "IHSG Smart Screener API aktif"


def test_feedback_create_returns_expected_payload(api_client: requests.Session) -> None:
    payload: Dict[str, str] = {
        "name": "QA Agent",
        "email": f"qa-{uuid.uuid4().hex[:8]}@example.com",
        "message": "Aplikasi beta ini sangat membantu screening fundamental.",
    }

    response = api_client.post(f"{BASE_URL}/api/feedback", json=payload)

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert isinstance(data["id"], str) and len(data["id"]) > 0
    assert data["name"] == payload["name"]
    assert data["email"] == payload["email"]
    assert data["message"] == payload["message"]
    assert isinstance(data["created_at"], str) and len(data["created_at"]) > 0


def test_feedback_rejects_too_short_message(api_client: requests.Session) -> None:
    payload: Dict[str, str] = {
        "name": "QA Agent",
        "email": f"qa-{uuid.uuid4().hex[:8]}@example.com",
        "message": "abc",
    }

    response = api_client.post(f"{BASE_URL}/api/feedback", json=payload)

    assert response.status_code == 422
    detail: Any = response.json().get("detail", [])
    assert isinstance(detail, list) and len(detail) > 0


def test_waitlist_create_then_update_same_email(api_client: requests.Session) -> None:
    unique_email = f"waitlist-{uuid.uuid4().hex[:8]}@example.com"

    create_response = api_client.post(
        f"{BASE_URL}/api/waitlist",
        json={"email": unique_email, "note": "Tertarik sektor perbankan"},
    )
    assert create_response.status_code == 200
    created: Dict[str, Any] = create_response.json()
    assert created["email"] == unique_email
    assert created["note"] == "Tertarik sektor perbankan"
    assert created["status"] == "created"
    assert isinstance(created["id"], str) and len(created["id"]) > 0

    update_response = api_client.post(
        f"{BASE_URL}/api/waitlist",
        json={"email": unique_email, "note": "Fokus dividen dan value investing"},
    )
    assert update_response.status_code == 200
    updated: Dict[str, Any] = update_response.json()
    assert updated["email"] == unique_email
    assert updated["status"] == "updated"
    assert updated["id"] == created["id"]
    assert updated["created_at"] == created["created_at"]
    assert updated["note"] == "Fokus dividen dan value investing"


def test_collection_summary_has_expected_shape(api_client: requests.Session) -> None:
    response = api_client.get(f"{BASE_URL}/api/collections/summary")

    assert response.status_code == 200
    data: Dict[str, Any] = response.json()
    assert "feedback_count" in data and isinstance(data["feedback_count"], int)
    assert "waitlist_count" in data and isinstance(data["waitlist_count"], int)
    assert data["feedback_count"] >= 0
    assert data["waitlist_count"] >= 0