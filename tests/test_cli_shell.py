from typer.testing import CliRunner
from htdp.cli import app

runner = CliRunner()


def test_cli_lists_all_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("synth", "validate", "process", "qc", "package", "replay"):
        assert cmd in result.stdout


def test_ingest_unavailable_exits_1(tmp_path, monkeypatch):
    import sys

    from typer.testing import CliRunner

    from htdp.cli import app

    (tmp_path / "s.xdf").write_bytes(b"XDF:")
    sc = tmp_path / "ingest.json"
    sc.write_text(
        '{"session":{"session_id":"r","participant_id":"p","protocol_id":"reach-grasp-place",'
        '"consent_form_version":"v1","device_config_id":"d","start_time_s":0.0},'
        '"consent":{"consent_form_version":"v1"},"device_config":{"device_config_id":"d"},'
        '"ingest_map":{"w":{"role":"motion","tracker_id":"right_wrist","channels":'
        '{"x_m":0,"y_m":1,"z_m":2,"qw":3,"qx":4,"qy":5,"qz":6,"quality":7}},'
        '"m":{"role":"events"}}}',
        encoding="utf-8",
    )
    monkeypatch.setitem(sys.modules, "pyxdf", None)  # force IngestUnavailable
    result = CliRunner().invoke(
        app, ["ingest", str(tmp_path / "s.xdf"), str(sc), "--out", str(tmp_path / "out")]
    )
    assert result.exit_code == 1
    assert "error:" in result.output


def test_ingest_roundtrip_cli(tmp_path):
    import json

    import pytest as _pytest

    _pytest.importorskip("pyxdf")
    from typer.testing import CliRunner

    from htdp.cli import app
    from htdp.synth.generate import generate_session
    from tests._xdf_writer import build_sidecar, write_xdf

    raw = generate_session(tmp_path / "raw", seed=1)
    write_xdf(raw, tmp_path / "s.xdf")
    sc = tmp_path / "ingest.json"
    sc.write_text(json.dumps(build_sidecar(raw)), encoding="utf-8")
    out = tmp_path / "ingested"
    result = CliRunner().invoke(
        app, ["ingest", str(tmp_path / "s.xdf"), str(sc), "--out", str(out)]
    )
    assert result.exit_code == 0, result.output
    assert (out / "session.json").exists()
