from pathlib import Path

import polars as pl
import pytest

from htdp.catalog import CatalogError, build_catalog, scan_sessions
from htdp.synth.generate import generate_session

_COLUMNS = [
    "session_id",
    "participant_id",
    "protocol_id",
    "device_config_id",
    "consent_form_version",
    "qc_status",
    "processing_status",
    "start_time_s",
    "modalities",
]


def test_build_catalog(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    out = build_catalog(tmp_path / "raw", tmp_path / "catalog.parquet")
    df = pl.read_parquet(out)
    assert df.columns == _COLUMNS
    assert df.height == 2
    assert df["session_id"].to_list() == ["synth-0001", "synth-0002"]
    assert df["modalities"].to_list() == ["events,motion", "events,motion"]
    assert df["qc_status"].to_list() == ["pass", "pass"]
    assert df["processing_status"].to_list() == ["raw", "raw"]


def test_deterministic(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    a = build_catalog(tmp_path / "raw", tmp_path / "a.parquet")
    b = build_catalog(tmp_path / "raw", tmp_path / "b.parquet")
    assert a.read_bytes() == b.read_bytes()


def test_missing_dir_raises(tmp_path: Path):
    with pytest.raises(CatalogError):
        scan_sessions(tmp_path / "nope")


def test_empty_dir_raises(tmp_path: Path):
    (tmp_path / "empty").mkdir()
    with pytest.raises(CatalogError):
        scan_sessions(tmp_path / "empty")


def test_malformed_session_raises(tmp_path: Path):
    session_dir = tmp_path / "raw" / "bad-session"
    session_dir.mkdir(parents=True)
    (session_dir / "session.json").write_text("not-json", encoding="utf-8")
    (session_dir / "device_config.json").write_text("{}", encoding="utf-8")
    with pytest.raises(CatalogError):
        scan_sessions(tmp_path / "raw")


def test_cli_catalog(tmp_path: Path):
    from typer.testing import CliRunner

    from htdp.cli import app

    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    runner = CliRunner()
    ok = runner.invoke(app, ["catalog", str(tmp_path / "raw"), str(tmp_path / "c.parquet")])
    assert ok.exit_code == 0, ok.output
    assert "2 sessions" in ok.output
    assert (tmp_path / "c.parquet").exists()

    bad = runner.invoke(app, ["catalog", str(tmp_path / "nope"), str(tmp_path / "c2.parquet")])
    assert bad.exit_code == 1
    assert "error:" in bad.output
