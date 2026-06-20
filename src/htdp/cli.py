from pathlib import Path

import typer

app = typer.Typer(help="Human-task dataset pipeline (v0.1 synthetic spine)", no_args_is_help=True)


@app.command()
def synth(out: Path = typer.Option(..., "--out"), seed: int = 0, force: bool = False) -> None:
    """Generate a synthetic session."""
    raise typer.Exit(0)


@app.command()
def validate(raw_dir: Path) -> None:
    """Validate a raw session folder."""
    raise typer.Exit(0)


@app.command()
def process(raw_dir: Path) -> None:
    """Process a raw session into Parquet."""
    raise typer.Exit(0)


@app.command()
def qc(processed_dir: Path) -> None:
    """Generate a QC report."""
    raise typer.Exit(0)


@app.command()
def package(
    session_ids: list[str],
    release: str = typer.Option(...),
    profile: str = typer.Option(...),
) -> None:
    """Package a dataset release (consent-gated)."""
    raise typer.Exit(0)


@app.command()
def replay(release_dir: Path) -> None:
    """Replay a packaged release in MuJoCo."""
    raise typer.Exit(0)
