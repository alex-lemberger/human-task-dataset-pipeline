from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

from htdp.consent.modalities import MODALITY_GLOBS, resolve_absent
from htdp.consent.profiles import check_consent
from htdp.io.canonical import dump_json, write_csv
from htdp.io.checksums import sha256_bytes, sha256_file, write_checksums
from htdp.schemas.enums import ReleaseProfile
from htdp.schemas.models import Consent, DatasetRelease, Session


def _present_modalities(session_ids: list[str], raw_root: Path) -> set[str]:
    present: set[str] = set()
    for modality, globs in MODALITY_GLOBS.items():
        for sid in session_ids:
            session_dir = raw_root / sid
            if any(p.is_file() for pattern in globs for p in session_dir.glob(pattern)):
                present.add(modality)
                break
    return present


class ConsentError(RuntimeError):
    """Raised when a session's consent does not permit the requested release profile."""


_LICENSE = "Synthetic data. CC-BY-4.0 for v0.1 demonstration release.\n"


def _manifest_sha(staging_data: Path) -> str:
    files = sorted(p for p in staging_data.rglob("*") if p.is_file())
    # Hash is INTENTIONALLY scoped to data/ files only; README, LICENSE, manifest,
    # tool_versions, and timestamps are excluded so the digest is reproducible across machines.
    digest_map = {p.relative_to(staging_data).as_posix(): sha256_file(p) for p in files}
    canonical = json.dumps(digest_map, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return sha256_bytes(canonical)


def package_release(
    session_ids: list[str],
    release_name: str,
    profile: ReleaseProfile,
    raw_root: Path,
    releases_root: Path,
) -> Path:
    final = releases_root / release_name
    if final.exists():
        raise FileExistsError(f"release already exists: {final}")

    # Consent gate FIRST — fail before any output.
    consents: list[Consent] = []
    for sid in session_ids:
        consent = Consent.model_validate_json(
            (raw_root / sid / "consent.json").read_text(encoding="utf-8")
        )
        missing = check_consent(consent, profile)
        if missing:
            raise ConsentError(f"{sid}: profile {profile.value} requires {missing}")
        consents.append(consent)

    # Modality filtering: a modality is absent if any session forbids it (consent)
    # or it is not present on disk. drop_globs lists files to omit from staging.
    present = _present_modalities(session_ids, raw_root)
    absent, drop_globs = resolve_absent(consents, present)

    releases_root.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{release_name}.", dir=releases_root))
    try:
        data_dir = staging / "data"
        participants: list[dict[str, object]] = []
        sessions: list[dict[str, object]] = []
        for sid in session_ids:
            dest = data_dir / sid
            shutil.copytree(raw_root / sid, dest)
            for pattern in drop_globs:
                for p in sorted(dest.glob(pattern)):
                    if p.is_file():
                        p.unlink()
            session = Session.model_validate_json(
                (raw_root / sid / "session.json").read_text(encoding="utf-8")
            )
            participants.append({"participant_id": session.participant_id, "cohort": "synthetic"})
            sessions.append(
                {
                    "session_id": sid,
                    "participant_id": session.participant_id,
                    "protocol_id": session.protocol_id,
                }
            )

        write_csv(
            participants,
            ["participant_id", "cohort"],
            staging / "participants.csv",
        )
        write_csv(
            sessions,
            ["session_id", "participant_id", "protocol_id"],
            staging / "sessions.csv",
        )
        (staging / "README.md").write_text(
            f"# {release_name}\nSynthetic reach-grasp-place release (v0.1).\n",
            encoding="utf-8",
            newline="\n",
        )
        (staging / "LICENSE").write_text(_LICENSE, encoding="utf-8", newline="\n")
        (staging / "protocol.md").write_text(
            "# reach-grasp-place\nReach, grasp, transport, place.\n",
            encoding="utf-8",
            newline="\n",
        )

        manifest_sha = _manifest_sha(data_dir)
        release = DatasetRelease(
            release_name=release_name,
            profile=profile.value,
            session_ids=session_ids,
            absent_modalities=sorted(absent),
            manifest_sha256=manifest_sha,
        )
        dump_json(release, staging / "manifest.json")
        write_checksums(staging)
        os.replace(staging, final)  # atomic rename
        return final
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
