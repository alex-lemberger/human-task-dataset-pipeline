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


def test_query_no_filters_returns_all(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    cat = build_catalog(tmp_path / "raw", tmp_path / "c.parquet")
    from htdp.catalog import query_catalog

    assert query_catalog(cat) == ["synth-0001", "synth-0002"]


def test_query_protocol_filter(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    cat = build_catalog(tmp_path / "raw", tmp_path / "c.parquet")
    from htdp.catalog import query_catalog

    assert query_catalog(cat, protocol="reach-grasp-place") == ["synth-0001"]
    assert query_catalog(cat, protocol="nope") == []


def test_query_modality_membership(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    cat = build_catalog(tmp_path / "raw", tmp_path / "c.parquet")
    from htdp.catalog import query_catalog

    assert query_catalog(cat, modality="motion") == ["synth-0001", "synth-0002"]
    assert query_catalog(cat, modality="eeg") == []


def test_query_and_semantics(tmp_path: Path):
    generate_session(tmp_path / "raw", seed=1)
    cat = build_catalog(tmp_path / "raw", tmp_path / "c.parquet")
    from htdp.catalog import query_catalog

    assert query_catalog(cat, protocol="reach-grasp-place", qc_status="pass") == ["synth-0001"]
    assert query_catalog(cat, protocol="reach-grasp-place", qc_status="fail") == []


def test_query_missing_catalog_raises(tmp_path: Path):
    from htdp.catalog import CatalogError, query_catalog

    with pytest.raises(CatalogError):
        query_catalog(tmp_path / "nope.parquet")


def test_cli_catalog_query(tmp_path: Path):
    from typer.testing import CliRunner

    from htdp.cli import app

    generate_session(tmp_path / "raw", seed=1)
    generate_session(tmp_path / "raw", seed=2)
    build_catalog(tmp_path / "raw", tmp_path / "c.parquet")
    runner = CliRunner()
    ok = runner.invoke(app, ["catalog-query", str(tmp_path / "c.parquet"), "--modality", "motion"])
    assert ok.exit_code == 0, ok.output
    assert ok.output.split() == ["synth-0001", "synth-0002"]

    bad = runner.invoke(app, ["catalog-query", str(tmp_path / "missing.parquet")])
    assert bad.exit_code == 1
    assert "error:" in bad.output


def _write_catalog(path: Path) -> Path:
    """Write a controlled 2-row catalog Parquet with distinct start_time_s.

    Synth hardcodes start_time_s=0.0, so range tests build the Parquet directly.
    """
    df = pl.DataFrame(
        {
            "session_id": ["session-a", "session-b"],
            "participant_id": ["p01", "p02"],
            "protocol_id": ["p", "p"],
            "device_config_id": ["d", "d"],
            "consent_form_version": ["v1", "v1"],
            "qc_status": ["pass", "pass"],
            "processing_status": ["raw", "raw"],
            "start_time_s": [100.0, 200.0],
            "modalities": ["events,motion", "events,motion"],
        }
    ).select(_COLUMNS)
    df.write_parquet(path)
    return path


def test_query_start_after(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_after=150.0) == ["session-b"]


def test_query_start_before(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_before=150.0) == ["session-a"]


def test_query_range_inclusive_both_ends(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_after=100.0, start_before=200.0) == [
        "session-a",
        "session-b",
    ]


def test_query_start_after_inclusive_boundary(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_after=200.0) == ["session-b"]


def test_query_inverted_range_empty(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_after=200.0, start_before=100.0) == []


def test_query_range_and_existing_filter(tmp_path: Path):
    from htdp.catalog import query_catalog

    cat = _write_catalog(tmp_path / "c.parquet")
    assert query_catalog(cat, start_after=100.0, protocol="p") == [
        "session-a",
        "session-b",
    ]
