from __future__ import annotations


class LearnUnavailable(RuntimeError):
    """Raised when an optional learning dependency (torch) is not installed."""
