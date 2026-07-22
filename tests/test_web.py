"""Session 5 FastAPI web-service tests against real Postgres."""

import inspect
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from research_agent.errors import StateError
from research_agent.report_store import save_report
from research_agent.web import app, get_conn


@pytest.fixture
def web_client(db):
    def override_conn():
        yield db

    app.dependency_overrides[get_conn] = override_conn
    with patch("research_agent.web.open_pool", return_value=object()), \
         patch("research_agent.web.close_pool"):
        with TestClient(app) as client:
            yield client
    app.dependency_overrides.clear()


def test_routes_are_sync_functions():
    route_functions = {
        route.path: route.endpoint
        for route in app.routes
        if route.path in {
            "/research", "/jobs/{job_id}", "/reports",
            "/reports/{report_key}", "/health", "/health/ready", "/modes",
        }
    }
    assert route_functions
    assert all(not inspect.iscoroutinefunction(endpoint) for endpoint in route_functions.values())


def test_post_valid_query_creates_queued_job(web_client, db):
    response = web_client.post(
        "/research",
        json={"query": "Pacific Flow competitors", "mode": "quick"},
    )

    assert response.status_code == 202
    job_id = uuid.UUID(response.json()["job_id"])
    assert response.json()["status"] == "queued"
    assert response.headers["location"] == f"/jobs/{job_id}"
    row = db.execute("SELECT query, mode, status FROM jobs WHERE id = %s", (job_id,)).fetchone()
    assert row == {
        "query": "Pacific Flow competitors",
        "mode": "quick",
        "status": "queued",
    }


def test_vague_query_returns_400_without_creating_job(web_client, db):
    before = db.execute("SELECT count(*) AS count FROM jobs").fetchone()["count"]

    response = web_client.post("/research", json={"query": "stuff", "mode": "quick"})

    assert response.status_code == 400
    after = db.execute("SELECT count(*) AS count FROM jobs").fetchone()["count"]
    assert after == before


def test_get_job_status_shapes(web_client, db):
    job_id = db.execute(
        "INSERT INTO jobs (query, mode) VALUES ('specific market analysis', 'quick') RETURNING id"
    ).fetchone()["id"]

    queued = web_client.get(f"/jobs/{job_id}")
    assert queued.status_code == 200
    assert queued.json() == {"job_id": str(job_id), "status": "queued"}

    report_key = save_report(
        db,
        query="specific market analysis",
        mode="quick",
        content="# Finished report",
        job_id=job_id,
    )
    db.execute("UPDATE jobs SET status = 'done' WHERE id = %s", (job_id,))

    done = web_client.get(f"/jobs/{job_id}")
    assert done.json() == {
        "job_id": str(job_id),
        "status": "done",
        "report_key": report_key,
        "content": "# Finished report",
    }


def test_unknown_and_malformed_job_ids(web_client):
    assert web_client.get(f"/jobs/{uuid.uuid4()}").status_code == 404
    assert web_client.get("/jobs/not-a-uuid").status_code == 422


def test_reports_list_and_lookup(web_client, db):
    report_key = save_report(
        db,
        query="San Diego musician network",
        mode="standard",
        content="# Network report",
    )

    listed = web_client.get("/reports")
    assert listed.status_code == 200
    assert listed.json()["reports"][0]["report_key"] == report_key
    assert listed.json()["reports"][0]["query"] == "San Diego musician network"

    report = web_client.get(f"/reports/{report_key}")
    assert report.json() == {"report_key": report_key, "content": "# Network report"}
    assert web_client.get("/reports/missing-deadbeef").status_code == 404


def test_verbatim_at_rest_is_non_executable_json(web_client, db):
    query = "market analysis <script>alert(1)</script> & venues"
    content = "# Report\n\n<script>alert(2)</script> & < >"
    created = web_client.post("/research", json={"query": query, "mode": "standard"})
    job_id = uuid.UUID(created.json()["job_id"])
    stored = db.execute("SELECT query FROM jobs WHERE id = %s", (job_id,)).fetchone()
    assert stored["query"] == query

    report_key = save_report(db, query=query, mode="standard", content=content, job_id=job_id)
    db.execute("UPDATE jobs SET status = 'done' WHERE id = %s", (job_id,))

    job_response = web_client.get(f"/jobs/{job_id}")
    report_response = web_client.get(f"/reports/{report_key}")
    list_response = web_client.get("/reports")
    for response in (job_response, report_response, list_response):
        assert response.headers["content-type"].startswith("application/json")
        assert not response.headers["content-type"].startswith("text/html")
    assert job_response.json()["content"] == content
    assert report_response.json()["content"] == content
    assert list_response.json()["reports"][0]["query"] == query


def test_database_failure_is_503_and_liveness_does_not_ping_db(web_client):
    def broken_conn():
        raise StateError("secret database detail")
        yield

    app.dependency_overrides[get_conn] = broken_conn

    vague = web_client.post("/research", json={"query": "stuff", "mode": "quick"})
    assert vague.status_code == 400

    failed = web_client.post(
        "/research",
        json={"query": "specific market analysis", "mode": "quick"},
    )
    assert failed.status_code == 503
    assert failed.json() == {"detail": "Database temporarily unavailable."}
    assert "secret" not in failed.text
    assert web_client.get("/health").json() == {"status": "ok"}
    assert web_client.get("/health/ready").status_code == 503


def test_modes_reuses_public_mode_listing(web_client):
    response = web_client.get("/modes")
    assert response.status_code == 200
    assert [mode["name"] for mode in response.json()["modes"]] == ["quick", "standard", "deep"]
