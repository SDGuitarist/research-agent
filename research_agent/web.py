"""FastAPI service for submitting jobs and reading saved research."""

from __future__ import annotations

import os
import uuid
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Literal

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from psycopg import OperationalError
from psycopg_pool import PoolTimeout
from pydantic import BaseModel

from research_agent import list_modes
from research_agent.db import close_pool, open_pool, pooled_connection
from research_agent.errors import ConfigError, StateError, VagueQueryError
from research_agent.query_validation import check_query_vagueness
from research_agent.report_store import get_report, get_reports


class ResearchRequest(BaseModel):
    """A research job submitted by the web client."""

    query: str
    mode: Literal["quick", "standard", "deep"] = "quick"


class NotFoundError(Exception):
    """Requested web resource does not exist."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Own the process-wide database pool for the app lifetime."""
    app.state.pool = open_pool()
    try:
        yield
    finally:
        close_pool()
        app.state.pool = None


app = FastAPI(title="Research Agent", lifespan=lifespan)


def get_conn():
    """Borrow one connection for the duration of a request."""
    with pooled_connection() as conn:
        yield conn


def validate_research_request(payload: ResearchRequest) -> ResearchRequest:
    """Reject vague input before FastAPI borrows a database connection."""
    validation = check_query_vagueness(payload.query)
    if not validation.is_valid:
        raise VagueQueryError(validation.message)
    return payload


@app.exception_handler(VagueQueryError)
def vague_query_handler(_request: Request, exc: VagueQueryError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(NotFoundError)
def not_found_handler(_request: Request, exc: NotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


def database_unavailable_handler(_request: Request, _exc: Exception) -> JSONResponse:
    """Return a stable response without exposing database details."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable."},
    )


for database_error in (OperationalError, PoolTimeout, StateError, ConfigError):
    app.add_exception_handler(database_error, database_unavailable_handler)


@app.post("/research", status_code=202)
def create_research_job(
    payload: ResearchRequest = Depends(validate_research_request),
    conn=Depends(get_conn),
):
    row = conn.execute(
        """INSERT INTO jobs (query, mode, status)
           VALUES (%s, %s, 'queued')
           RETURNING id""",
        (payload.query, payload.mode),
    ).fetchone()
    job_id = row["id"]
    return JSONResponse(
        status_code=202,
        content={"job_id": str(job_id), "status": "queued"},
        headers={"Location": f"/jobs/{job_id}"},
    )


@app.get("/jobs/{job_id}")
def get_job(job_id: uuid.UUID, conn=Depends(get_conn)):
    row = conn.execute(
        """SELECT jobs.status, jobs.error, reports.report_key, reports.content
           FROM jobs
           LEFT JOIN reports ON reports.job_id = jobs.id
           WHERE jobs.id = %s""",
        (job_id,),
    ).fetchone()
    if row is None:
        raise NotFoundError("Job not found.")

    response = {"job_id": str(job_id), "status": row["status"]}
    if row["status"] == "done":
        response.update(report_key=row["report_key"], content=row["content"])
    elif row["status"] == "failed":
        response["error"] = row["error"]
    return response


@app.get("/reports")
def list_reports(conn=Depends(get_conn)):
    return {
        "reports": [
            {
                "report_key": report.filename,
                "date": report.date,
                "query": report.query_name,
            }
            for report in get_reports(conn)
        ]
    }


@app.get("/reports/{report_key}")
def read_report(report_key: str, conn=Depends(get_conn)):
    content = get_report(conn, report_key)
    if content is None:
        raise NotFoundError("Report not found.")
    return {"report_key": report_key, "content": content}


@app.get("/health")
def health():
    """Liveness only: intentionally does not touch the database."""
    return {"status": "ok"}


@app.get("/health/ready")
def ready(conn=Depends(get_conn)):
    conn.execute("SELECT 1").fetchone()
    return {"status": "ready"}


@app.get("/modes")
def modes():
    return {"modes": [asdict(mode) for mode in list_modes()]}


def main() -> None:
    """Run the web service from the research-agent-web entry point."""
    import uvicorn

    uvicorn.run(
        "research_agent.web:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
    )
