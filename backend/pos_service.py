from __future__ import annotations

import json
import os
from typing import Annotated

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .pos_core import (
    answer_query,
    commit_import,
    connect,
    create_analysis_run,
    default_window,
    get_job,
    latest_analytics,
    preview_import,
    templates,
)


INTERNAL_SECRET = os.getenv("POS_INTERNAL_SECRET", "local-dev-pos-secret")
app = FastAPI(title="RetailPulse POS Analytics", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def require_internal(x_pos_internal_secret: Annotated[str | None, Header()] = None) -> None:
    if x_pos_internal_secret != INTERNAL_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized POS service request")


async def uploaded(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    return [(file.filename or "upload.csv", await file.read()) for file in files]


def metadata_from_form(metadata: str | None, source: str | None, coverage_from: str | None, coverage_to: str | None, complete: bool | None) -> dict:
    data = json.loads(metadata) if metadata else {}
    if source is not None:
        data["source"] = source
    if coverage_from is not None:
        data["coverage_from"] = coverage_from
    if coverage_to is not None:
        data["coverage_to"] = coverage_to
    if complete is not None:
        data["complete"] = complete
    return data


@app.get("/health")
def health() -> dict:
    return {"ok": True}


@app.get("/templates", dependencies=[Depends(require_internal)])
def get_templates() -> dict:
    return templates()


@app.post("/import/preview", dependencies=[Depends(require_internal)])
async def import_preview(
    files: Annotated[list[UploadFile], File()],
    metadata: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = None,
    coverage_from: Annotated[str | None, Form()] = None,
    coverage_to: Annotated[str | None, Form()] = None,
    complete: Annotated[bool | None, Form()] = None,
) -> dict:
    return preview_import(await uploaded(files), metadata_from_form(metadata, source, coverage_from, coverage_to, complete))


@app.post("/import/commit", dependencies=[Depends(require_internal)])
async def import_commit(
    files: Annotated[list[UploadFile], File()],
    metadata: Annotated[str | None, Form()] = None,
    source: Annotated[str | None, Form()] = None,
    coverage_from: Annotated[str | None, Form()] = None,
    coverage_to: Annotated[str | None, Form()] = None,
    complete: Annotated[bool | None, Form()] = None,
) -> dict:
    with connect() as conn:
        return commit_import(conn, await uploaded(files), metadata_from_form(metadata, source, coverage_from, coverage_to, complete))


@app.post("/analysis", dependencies=[Depends(require_internal)])
async def analysis(body: dict) -> dict:
    with connect() as conn:
        date_from = body.get("from")
        date_to = body.get("to")
        if not date_from or not date_to:
            date_from, date_to = default_window(conn)
        horizon = int(body.get("horizon") or 7)
        if horizon not in {7, 30}:
            raise HTTPException(status_code=400, detail="horizon must be 7 or 30")
        return create_analysis_run(conn, date_from, date_to, horizon)


@app.get("/jobs/{job_id}", dependencies=[Depends(require_internal)])
def job(job_id: str) -> dict:
    with connect() as conn:
        try:
            return get_job(conn, job_id)
        except KeyError:
            raise HTTPException(status_code=404, detail="Job not found") from None


@app.get("/analytics", dependencies=[Depends(require_internal)])
def analytics(from_: str | None = Query(default=None, alias="from"), to: str | None = None, horizon: int = 7) -> dict:
    with connect() as conn:
        date_from = from_
        date_to = to
        if not date_from or not date_to:
            date_from, date_to = default_window(conn)
        if horizon not in {7, 30}:
            raise HTTPException(status_code=400, detail="horizon must be 7 or 30")
        return latest_analytics(conn, date_from, date_to, horizon)


@app.post("/query", dependencies=[Depends(require_internal)])
async def query(body: dict) -> dict:
    question = str(body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")
    with connect() as conn:
        return answer_query(conn, question, body.get("filters") or {})
