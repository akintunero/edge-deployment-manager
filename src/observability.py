#!/usr/bin/env python3
"""Structured logging and lightweight metrics for edge services."""

from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any, Dict


class JsonLogFormatter(logging.Formatter):
    """Emit single-line JSON log records."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


class MetricsRegistry:
    """Thread-safe counters exposed in Prometheus text format."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}

    def inc(self, name: str, value: float = 1.0) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0.0) + value

    def set_gauge(self, name: str, value: float) -> None:
        with self._lock:
            self._gauges[name] = value

    def render_prometheus(self) -> str:
        lines = []
        with self._lock:
            for name, value in sorted(self._counters.items()):
                lines.append(f"# TYPE {name} counter")
                lines.append(f"{name} {value}")
            for name, value in sorted(self._gauges.items()):
                lines.append(f"# TYPE {name} gauge")
                lines.append(f"{name} {value}")
        return "\n".join(lines) + "\n"


METRICS = MetricsRegistry()


def configure_logging(config: Dict[str, Any]) -> None:
    """Apply logging configuration from YAML settings."""
    level_name = config.get("level", "INFO")
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    use_json = bool(config.get("json", False))

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    if use_json:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                config.get(
                    "format",
                    "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                )
            )
        )
    root.addHandler(handler)
    root.setLevel(level)
