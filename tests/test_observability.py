#!/usr/bin/env python3
"""Tests for observability helpers."""

import unittest

from src.observability import METRICS, MetricsRegistry


class TestObservability(unittest.TestCase):
    def test_metrics_render(self) -> None:
        registry = MetricsRegistry()
        registry.inc("edge_test_total", 2)
        registry.set_gauge("edge_test_gauge", 1)
        rendered = registry.render_prometheus()
        self.assertIn("edge_test_total 2.0", rendered)
        self.assertIn("edge_test_gauge 1", rendered)

    def test_global_metrics_singleton(self) -> None:
        METRICS.inc("edge_singleton_total")
        self.assertIn("edge_singleton_total", METRICS.render_prometheus())


if __name__ == "__main__":
    unittest.main()
