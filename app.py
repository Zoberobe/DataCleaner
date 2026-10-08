"""Small synchronous FastAPI demo for DataCleaner."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response

from datacleaner import InputError, ProcessResult, process_file
from datacleaner.engine import MAX_BYTES


app = FastAPI(title="DataCleaner", version="1.0.0")
_jobs: dict[str, tuple[datetime, ProcessResult]] = {}
_ttl = timedelta(hours=1)
_page = Path(__file__).parent / "static" / "index.html"
_examples = Path(__file__).parent / "examples"


def _prune_jobs() -> None:
    now = datetime.now(timezone.utc)
    for job_id, (created, _) in list(_jobs.items()):
        if now - created >= _ttl:
            del _jobs[job_id]
    if len(_jobs) > 20:
        oldest = sorted(_jobs, key=lambda key: _jobs[key][0])[: len(_jobs) - 20]
        for job_id in oldest:
            del _jobs[job_id]


@app.get("/", response_class=HTMLResponse)
def home() -> str:
    return _page.read_text(encoding="utf-8")


@app.get("/api/sample/{kind}")
def sample(kind: Literal["csv", "xlsx"]) -> Response:
    filename = f"sample_customers.{kind}"
    return Response(
        content=(_examples / filename).read_bytes(),
        media_type="text/csv; charset=utf-8" if kind == "csv" else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

@app.post("/api/process")
async def process(request: Request, filename: str) -> dict:
    _prune_jobs()
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > MAX_BYTES:
            raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "message": "File exceeds 5 MB"})
    try:
        result = process_file(bytes(content), filename)
    except InputError as exc:
        status = 413 if exc.code in {"FILE_TOO_LARGE", "TOO_MANY_ROWS"} else 400
        raise HTTPException(status_code=status, detail={"code": exc.code, "message": str(exc)}) from exc
    job_id = uuid4().hex
    _jobs[job_id] = (datetime.now(timezone.utc), result)
    _prune_jobs()
    return {
        "job_id": job_id,
        "summary": result.summary,
        "downloads": {
            "clean": f"/api/result/{job_id}/clean",
            "errors": f"/api/result/{job_id}/errors",
        },
    }


@app.get("/api/result/{job_id}/{kind}")
def download(job_id: str, kind: Literal["clean", "errors"]) -> Response:
    _prune_jobs()
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Result expired or not found")
    result = job[1]
    if kind == "clean":
        content, filename = result.clean_csv, "clean_customers.csv"
    else:
        content, filename = result.errors_csv, "errors.csv"
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
