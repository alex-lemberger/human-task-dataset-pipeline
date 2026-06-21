from pathlib import Path

import typer

app = typer.Typer(help="Human-task dataset pipeline (v0.1 synthetic spine)", no_args_is_help=True)


@app.command()
def synth(out: Path = typer.Option(..., "--out"), seed: int = 0, force: bool = False) -> None:
    """Generate a synthetic session."""
    from htdp.synth.generate import generate_session

    try:
        d = generate_session(out, seed=seed, force=force)
    except FileExistsError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {d}")


@app.command()
def ingest(
    xdf_file: Path,
    sidecar: Path,
    out: Path = typer.Option(..., "--out"),
    force: bool = False,
) -> None:
    """Ingest an LSL .xdf recording into a raw session folder."""
    from pydantic import ValidationError

    from htdp.ingest.mapping import MappingError
    from htdp.ingest.reader import IngestUnavailable
    from htdp.ingest.session import ingest_xdf

    try:
        d = ingest_xdf(xdf_file, sidecar, out, force=force)
    except (IngestUnavailable, MappingError, ValidationError, FileExistsError, KeyError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {d}")


@app.command()
def validate(raw_dir: Path) -> None:
    """Validate a raw session folder."""
    from htdp.validate import validate_session

    problems = validate_session(raw_dir)
    if problems:
        for p in problems:
            typer.echo(f"FAIL: {p}", err=True)
        raise typer.Exit(1)
    typer.echo("OK")


@app.command()
def process(raw_dir: Path) -> None:
    """Process a raw session into Parquet."""
    from htdp.processing.extract import process_session

    try:
        out = process_session(raw_dir, Path("data/processed"))
    except ValueError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {out}")


@app.command()
def qc(processed_dir: Path) -> None:
    """Generate a QC report."""
    from htdp.qc.checks import run_qc

    report = run_qc(processed_dir)
    typer.echo(f"overall: {report['overall']}")


@app.command()
def package(
    session_ids: list[str],
    release: str = typer.Option(...),
    profile: str = typer.Option(...),
) -> None:
    """Package a dataset release (consent-gated)."""
    from htdp.release.package import package_release, ConsentError
    from htdp.schemas.enums import ReleaseProfile

    try:
        out = package_release(
            session_ids,
            release,
            ReleaseProfile(profile),
            Path("data/raw"),
            Path("data/releases"),
        )
    except ConsentError as exc:
        typer.echo(f"CONSENT BLOCK: {exc}", err=True)
        raise typer.Exit(2) from exc
    typer.echo(f"wrote {out}")


@app.command()
def replay(release_dir: Path) -> None:
    """Replay a packaged release in MuJoCo."""
    from htdp.replay.player import replay_release, ReplayUnavailable

    try:
        frames = replay_release(release_dir)
    except ReplayUnavailable as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"stepped {frames} frames")
