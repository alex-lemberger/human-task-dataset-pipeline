from __future__ import annotations


def estimate_fs(timestamps: list[float]) -> float:
    if len(timestamps) < 2:
        raise ValueError("need at least two samples to estimate sampling frequency")
    span = timestamps[-1] - timestamps[0]
    if span <= 0:
        raise ValueError("zero or negative time span")
    return (len(timestamps) - 1) / span
