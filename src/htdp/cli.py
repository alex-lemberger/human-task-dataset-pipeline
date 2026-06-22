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
def ingest_video(
    session_dir: Path,
    mp4_file: Path,
    sidecar: Path,
    force: bool = False,
) -> None:
    """Augment a raw session with a video file (registers it in device_config)."""
    from pydantic import ValidationError

    from htdp.ingest.video import VideoIngestError, ingest_video as _ingest_video

    try:
        d = _ingest_video(session_dir, mp4_file, sidecar, force=force)
    except (VideoIngestError, ValidationError, FileNotFoundError) as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {d}")


@app.command()
def export_bids(raw_dir: Path, out_dir: Path, force: bool = False) -> None:
    """Export a raw session to a BIDS dataset tree (Motion-BIDS + BrainVision EEG-BIDS)."""
    from htdp.export.bids import BidsExportError, export_motion_bids

    try:
        d = export_motion_bids(raw_dir, out_dir, force=force)
    except BidsExportError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {d}")


@app.command()
def export_release_bids(release_dir: Path, out_dir: Path, force: bool = False) -> None:
    """Export a packaged release to a multi-subject BIDS dataset."""
    from htdp.export.bids import BidsExportError, export_release_bids as _export_release_bids

    try:
        d = _export_release_bids(release_dir, out_dir, force=force)
    except BidsExportError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(f"wrote {d}")


@app.command()
def export_release_rosbag(release_dir: Path, out_dir: Path, force: bool = False) -> None:
    """Export a packaged release to one rosbag2 (mcap) bag per session."""
    from htdp.export.rosbag import RosbagExportError, export_release_rosbag as _export

    try:
        d = _export(release_dir, out_dir, force=force)
    except RosbagExportError as exc:
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


@app.command()
def replay_ik(
    release_dir: Path,
    max_steps: int = 50,
    out: Path | None = typer.Option(None, "--out"),
    force: bool = typer.Option(False, "--force"),
) -> None:
    """Drive a robot arm along a release's wrist path via IK (headless)."""
    from htdp.replay.ik import IkUnavailable, replay_release_ik, write_ik_trajectory

    try:
        result = replay_release_ik(release_dir, max_steps=max_steps)
    except IkUnavailable as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    typer.echo(
        f"stepped {len(result.joint_trajectory)} steps, max tracking error {result.max_error:.4f} m"
    )
    if out is not None:
        try:
            written = write_ik_trajectory(result, out, force=force)
        except FileExistsError as exc:
            typer.echo(f"error: {exc}", err=True)
            raise typer.Exit(1) from exc
        typer.echo(f"wrote {written} ({len(result.joint_trajectory)} steps)")


@app.command()
def catalog(sessions_dir: Path, out_path: Path) -> None:
    """Build a multi-session Parquet catalog from a raw sessions directory."""
    import polars as pl

    from htdp.catalog import CatalogError, build_catalog

    try:
        out = build_catalog(sessions_dir, out_path)
    except CatalogError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    n = pl.read_parquet(out).height
    typer.echo(f"wrote {out} ({n} sessions)")


@app.command()
def catalog_query(
    catalog_path: Path,
    protocol: str | None = typer.Option(None, "--protocol"),
    qc: str | None = typer.Option(None, "--qc"),
    participant: str | None = typer.Option(None, "--participant"),
    processing_status: str | None = typer.Option(None, "--processing-status"),
    modality: str | None = typer.Option(None, "--modality"),
    start_after: float | None = typer.Option(None, "--start-after"),
    start_before: float | None = typer.Option(None, "--start-before"),
) -> None:
    """Print session_ids from a catalog matching the given filters (AND)."""
    from htdp.catalog import CatalogError, query_catalog

    try:
        ids = query_catalog(
            catalog_path,
            protocol=protocol,
            qc_status=qc,
            participant=participant,
            processing_status=processing_status,
            modality=modality,
            start_after=start_after,
            start_before=start_before,
        )
    except CatalogError as exc:
        typer.echo(f"error: {exc}", err=True)
        raise typer.Exit(1) from exc
    for session_id in ids:
        typer.echo(session_id)
