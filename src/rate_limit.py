#!/usr/bin/env python3
"""Simple in-memory rate limiting for HTTP endpoints."""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Deque, Dict, Optional


class RateLimiter:
    """Fixed-window request limiter keyed by client identifier."""

    def __init__(self, max_requests: int, window_seconds: int) -> None:
        if max_requests < 1:
            raise ValueError("max_requests must be at least 1")
        if window_seconds < 1:
            raise ValueError("window_seconds must be at least 1")

        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: Optional[float] = None) -> bool:
        current = now if now is not None else time.time()
        cutoff = current - self._window_seconds

        with self._lock:
            bucket = self._events.setdefault(key, deque())
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self._max_requests:
                return False

            bucket.append(current)
            return True


def build_rate_limiter(config: Optional[Dict[str, Any]]) -> Optional[RateLimiter]:
    """Create a rate limiter when enabled in configuration."""
    if not config or not config.get("enabled", False):
        return None

    return RateLimiter(
        int(config.get("max_requests", 10)),
        int(config.get("window_seconds", 60)),
    )
