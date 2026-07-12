"""FastAPI app factory for `htdp serve`: read-only status/jobs endpoints (Task 3).
Read endpoints touch the filesystem only for counts; they never mutate `data/`."""

from __future__ import annotations

from importlib.metadata import version as _pkg_version
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from htdp.serve.jobs import JobManager
from htdp.serve.status import read_status


def create_app(data_dir: Path, manager: JobManager | None = None) -> FastAPI:
    app = FastAPI(title="htdp serve", version="0.2.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:4200"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.data_dir = data_dir
    app.state.manager = manager or JobManager(data_dir)

    @app.get("/health")
    def health() -> dict[str, object]:
        try:
            v = _pkg_version("htdp")
        except Exception:  # noqa: BLE001
            v = "unknown"
        return {"ok": True, "version": v}

    @app.get("/status")
    def status() -> dict[str, object]:
        return read_status(app.state.data_dir, app.state.manager).model_dump()

    @app.get("/jobs")
    def jobs() -> dict[str, object]:
        return {"jobs": [j.model_dump() for j in app.state.manager.list_jobs()]}

    @app.get("/jobs/{job_id}")
    def job(job_id: str) -> dict[str, object]:
        got = app.state.manager.get(job_id)
        if got is None:
            raise HTTPException(status_code=404, detail="job not found")
        dumped: dict[str, object] = got.model_dump()
        return dumped

    return app
