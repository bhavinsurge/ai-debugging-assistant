import os
import sys
from pathlib import Path
from uuid import UUID

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.core.config import get_settings
from app.db.session import assert_safe_database, get_conn
from app.services import investigation as inv_service
from app.tools import search_logs, get_recent_deployments


@pytest.fixture(scope="module")
def database_url():
    settings = get_settings()
    url = settings.database_url_test
    assert_safe_database(url)
    # Prefer test DB; fall back to main if test empty (seed --with-test)
    with get_conn(url) as conn:
        n = conn.execute("SELECT COUNT(*) AS n FROM document_chunks").fetchone()["n"]
    if n == 0:
        pytest.skip("rootcause_test not seeded; run seed.py --with-test")
    return url


def test_search_logs_returns_evidence(database_url):
    rows = search_logs(
        query="NullPointerException PaymentClient",
        service="checkout-api",
        limit=5,
        database_url=database_url,
    )
    assert rows
    assert all("id" in r and r["tool"] == "search_logs" for r in rows)


def test_deployments_include_v214(database_url):
    rows = get_recent_deployments(service="checkout-api", limit=5, database_url=database_url)
    assert any("v2.14.0" in r["summary"] for r in rows)


def test_investigation_flow_evidence_bound(database_url):
    settings = get_settings()
    with get_conn(database_url) as conn:
        user = conn.execute("SELECT id FROM users LIMIT 1").fetchone()
    assert user
    row = inv_service.create_investigation_row(
        user_id=user["id"],
        title="Integration checkout incident",
        symptom="checkout-api 500 NullPointerException PaymentClient after deploy v2.14.0",
        service="checkout-api",
        environment="production",
        time_window_minutes=60,
        database_url=database_url,
    )
    report = inv_service.run_investigation(
        investigation_id=row["id"],
        title=row["title"],
        symptom=row["symptom"],
        service=row["service"],
        environment=row["environment"],
        database_url=database_url,
        llm_provider="mock",
    )
    assert report.status == "completed"
    assert report.primary_hypothesis is not None
    assert report.primary_hypothesis.confidence >= 0.7
    allowed = {e.id for e in report.evidence}
    assert set(report.primary_hypothesis.evidence_ids).issubset(allowed)
    assert "search_logs" in report.tools_invoked
    assert report.recommended_investigation
