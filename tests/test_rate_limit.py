#!/usr/bin/env python3
"""Tests for HTTP rate limiting."""

from __future__ import annotations

import unittest

from src.rate_limit import RateLimiter, build_rate_limiter


class TestRateLimiter(unittest.TestCase):
    """Rate limiter unit tests."""

    def test_allows_requests_within_window(self) -> None:
        limiter = RateLimiter(max_requests=2, window_seconds=60)
        self.assertTrue(limiter.allow("client-a", now=100.0))
        self.assertTrue(limiter.allow("client-a", now=101.0))
        self.assertFalse(limiter.allow("client-a", now=102.0))

    def test_build_returns_none_when_disabled(self) -> None:
        self.assertIsNone(build_rate_limiter(None))
        self.assertIsNone(build_rate_limiter({"enabled": False}))


if __name__ == "__main__":
    unittest.main()
