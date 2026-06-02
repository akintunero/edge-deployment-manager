#!/usr/bin/env python3
"""HTTP health, readiness, and metrics endpoints."""

from __future__ import annotations

import json
import logging
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Tuple

from .observability import METRICS

logger = logging.getLogger(__name__)

ReadinessCheck = Callable[[], Dict[str, Any]]


class HealthHttpHandler(BaseHTTPRequestHandler):
    """Serve /health, /ready, and /metrics."""

    server: "HealthHttpServer"

    def log_message(self, format: str, *args: Any) -> None:
        logger.debug("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(HTTPStatus.OK, {"status": "ok"})
            return

        if self.path == "/ready":
            payload = self.server.readiness_check()
            status = HTTPStatus.OK if payload.get("ready") else HTTPStatus.SERVICE_UNAVAILABLE
            self._json(status, payload)
            return

        if self.path == "/metrics":
            body = METRICS.render_prometheus().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _json(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class HealthHttpServer(ThreadingHTTPServer):
    """Background health/metrics server."""

    def __init__(
        self,
        server_address: Tuple[str, int],
        readiness_check: ReadinessCheck,
    ) -> None:
        self.readiness_check = readiness_check
        super().__init__(server_address, HealthHttpHandler)


class HealthServer:
    """Runs health endpoints in a daemon thread."""

    def __init__(
        self,
        host: str,
        port: int,
        readiness_check: ReadinessCheck,
    ) -> None:
        self._httpd = HealthHttpServer((host, port), readiness_check)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._host = host
        self._port = port

    def start(self) -> None:
        self._thread.start()
        logger.info("Health server listening on http://%s:%s", self._host, self._port)

    def stop(self) -> None:
        self._httpd.shutdown()
        self._thread.join(timeout=3)
