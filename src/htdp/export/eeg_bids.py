from __future__ import annotations

import struct


def estimate_fs(timestamps: list[float]) -> float:
    if len(timestamps) < 2:
        raise ValueError("need at least two samples to estimate sampling frequency")
    span = timestamps[-1] - timestamps[0]
    if span <= 0:
        raise ValueError("zero or negative time span")
    return (len(timestamps) - 1) / span


def eeg_binary(samples: list[list[float]]) -> bytes:
    return b"".join(struct.pack("<f", v) for row in samples for v in row)
