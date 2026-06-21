from __future__ import annotations

from htdp.schemas.models import Consent

MODALITY_FLAG: dict[str, str] = {
    "video": "distribute_raw_video",
    "eeg": "distribute_raw_eeg",
}
MODALITY_GLOBS: dict[str, tuple[str, ...]] = {
    "video": ("video/**/*",),
    "eeg": ("streams/eeg_*.csv",),
}
MODALITIES: tuple[str, ...] = ("eeg", "video")


def resolve_absent(
    consents: list[Consent],
    present: set[str],
) -> tuple[list[str], list[str]]:
    """Decide which modalities are absent from a release and which file globs to drop.

    A modality is absent if any session forbids it (consent flag False) or it is not
    present in any session. Only modalities that are both forbidden AND present
    contribute file globs to drop (a not-present modality has no files to remove).
    """
    absent: list[str] = []
    drop_globs: list[str] = []
    for m in MODALITIES:
        flag = MODALITY_FLAG[m]
        forbidden = any(not getattr(c, flag) for c in consents)
        is_present = m in present
        if forbidden or not is_present:
            absent.append(m)
        if forbidden and is_present:
            drop_globs.extend(MODALITY_GLOBS[m])
    return sorted(absent), sorted(drop_globs)
