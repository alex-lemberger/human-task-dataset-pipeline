"""Job kind allowlist + argv builder. Security boundary: only known htdp subcommands,
typed/validated args, server-controlled output paths."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class JobKindError(ValueError):
    """Raised for an unknown job kind or invalid job args."""


class _GenDemosArgs(BaseModel):
    n_train: int = Field(100, ge=1, le=2000)
    n_test: int = Field(25, ge=1, le=500)


class _SynthArgs(BaseModel):
    seed: int = Field(0, ge=0)


class _TrainArgs(BaseModel):
    steps: int = Field(3000, ge=1, le=50000)


class _EmptyArgs(BaseModel):
    pass


# kind -> (args model, argv builder). Output paths are hardcoded here, never from request.
def _synth_argv(a: _SynthArgs, data_dir: Path) -> list[str]:
    return ["synth", "--out", f"data/raw/serve-{a.seed:04d}", "--seed", str(a.seed), "--force"]


def _gen_demos_argv(a: _GenDemosArgs, data_dir: Path) -> list[str]:
    return ["gen-demos", "--out", "demos", "--n-train", str(a.n_train), "--n-test", str(a.n_test)]


def _train_argv(a: _TrainArgs, data_dir: Path) -> list[str]:
    return ["train-policy", "--demos", "demos", "--out", "policy.pt", "--steps", str(a.steps)]


def _eval_argv(a: _EmptyArgs, data_dir: Path) -> list[str]:
    return ["eval-policy", "--demos", "demos", "--policy", "policy.pt"]


_SPECS: dict[str, tuple[type[BaseModel], Callable[[Any, Path], list[str]]]] = {
    "synth": (_SynthArgs, _synth_argv),
    "gen-demos": (_GenDemosArgs, _gen_demos_argv),
    "train-policy": (_TrainArgs, _train_argv),
    "eval-policy": (_EmptyArgs, _eval_argv),
}

ALLOWED_KINDS = frozenset(_SPECS)


def build_argv(kind: str, args: dict[str, object], data_dir: Path) -> list[str]:
    spec = _SPECS.get(kind)
    if spec is None:
        raise JobKindError(f"unknown job kind: {kind!r}")
    model_cls, builder = spec
    try:
        parsed = model_cls.model_validate(args or {})
    except ValidationError as exc:
        raise JobKindError(f"invalid args for {kind!r}: {exc}") from exc
    return builder(parsed, data_dir)
