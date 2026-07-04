import json

import pytest

pytest.importorskip("torch")
pytest.importorskip("mujoco")
pytest.importorskip("mink")

from typer.testing import CliRunner

from htdp.cli import app

runner = CliRunner()


def test_cli_gen_train_eval(tmp_path):
    demos = tmp_path / "demos"
    r1 = runner.invoke(app, ["gen-demos", "--out", str(demos),
                             "--n-train", "2", "--n-test", "2", "--seed", "0"])
    assert r1.exit_code == 0, r1.output
    assert (demos / "meta" / "info.json").exists()

    policy = tmp_path / "policy.pt"
    r2 = runner.invoke(app, ["train-policy", "--demos", str(demos),
                             "--out", str(policy), "--steps", "20"])
    assert r2.exit_code == 0, r2.output
    assert policy.exists()

    report = tmp_path / "report.json"
    r3 = runner.invoke(app, ["eval-policy", "--demos", str(demos),
                             "--policy", str(policy), "--out", str(report)])
    assert r3.exit_code == 0, r3.output
    assert report.exists()
    rep = json.loads(report.read_text())
    assert "policy" in rep and "baseline" in rep

    # --n-positions: fresh eval positions instead of test_positions.json (E1)
    report_n = tmp_path / "report_n.json"
    r4 = runner.invoke(app, ["eval-policy", "--demos", str(demos),
                             "--policy", str(policy), "--out", str(report_n),
                             "--n-positions", "1"])
    assert r4.exit_code == 0, r4.output
    rep_n = json.loads(report_n.read_text())
    assert rep_n["policy"]["n"] == 1  # dataset test split has 2 -> proves fresh-sample path
    assert "ci95" in rep_n["policy"]
