#!/usr/bin/env python3
"""HTTP API for the edge deployment control plane."""

from __future__ import annotations

import json
import logging
import re
import secrets
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional, Tuple
from urllib.parse import urlparse

from ..command_envelope import CommandValidationError
from ..observability import METRICS
from ..rate_limit import RateLimiter
from .audit import AuditLog
from .bootstrap import BootstrapError, BootstrapService
from .leader_election import LeaderElector
from .registry import RegistryError
from .registry_factory import RegistryBackend
from .service import ControlPlaneError, ControlPlaneNotLeaderError, ControlPlaneService

logger = logging.getLogger(__name__)

DEVICE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,63}$")


class ControlPlaneApiHandler(BaseHTTPRequestHandler):
    """REST handler for device registry and command issuance."""

    server: "ControlPlaneHttpServer"

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), format % args)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._json_response(HTTPStatus.OK, {"status": "ok"})
            return

        if path == "/ready":
            payload = self.server.readiness_check()
            status = HTTPStatus.OK if payload.get("ready") else HTTPStatus.SERVICE_UNAVAILABLE
            self._json_response(status, payload)
            return

        if path == "/metrics":
            body = METRICS.render_prometheus().encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if not self._authorize():
            return
        if not self._check_api_rate_limit():
            return

        if path == "/v1/leader":
            elector = self.server.leader_elector
            payload = {
                "ha_enabled": elector is not None,
                "is_leader": elector.is_leader if elector is not None else True,
                "holder_id": elector.holder_id if elector is not None else None,
            }
            self._json_response(HTTPStatus.OK, payload)
            return

        if path == "/v1/devices":
            devices = self.server.registry.list_devices()
            self._json_response(HTTPStatus.OK, {"devices": devices})
            return

        device_match = re.fullmatch(r"/v1/devices/([^/]+)", path)
        if device_match:
            device_id = device_match.group(1)
            device = self.server.registry.get_device(device_id)
            if device is None:
                self._json_response(HTTPStatus.NOT_FOUND, {"error": "device not found"})
                return
            self._json_response(HTTPStatus.OK, device)
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        body = self._read_json_body()
        if body is None:
            return

        if path == "/v1/bootstrap/enroll":
            self._bootstrap_enroll(body)
            return

        if not self._authorize():
            return
        if not self._check_api_rate_limit():
            return

        if path == "/v1/devices":
            self._register_device(body)
            return

        rotate_match = re.fullmatch(r"/v1/devices/([^/]+)/certificates/rotate", path)
        if rotate_match:
            self._rotate_certificate(rotate_match.group(1), body)
            return

        command_match = re.fullmatch(r"/v1/devices/([^/]+)/commands", path)
        if command_match:
            self._issue_command(command_match.group(1), body)
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_PUT(self) -> None:
        if not self._authorize():
            return
        if not self._check_api_rate_limit():
            return

        path = urlparse(self.path).path
        body = self._read_json_body()
        if body is None:
            return

        policy_match = re.fullmatch(r"/v1/devices/([^/]+)/policy", path)
        if policy_match:
            self._update_policy(policy_match.group(1), body)
            return

        self._json_response(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def _bootstrap_enroll(self, body: Dict[str, Any]) -> None:
        if self.server.bootstrap_service is None:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "bootstrap is not enabled"})
            return

        if self.server.bootstrap_rate_limiter is not None:
            client_key = self.client_address[0]
            if not self.server.bootstrap_rate_limiter.allow(client_key):
                self._json_response(
                    HTTPStatus.TOO_MANY_REQUESTS,
                    {"error": "rate limit exceeded"},
                )
                return

        unknown = set(body.keys()) - {"device_id", "csr_pem"}
        if unknown:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": f"unknown fields: {', '.join(sorted(unknown))}"},
            )
            return

        device_id = body.get("device_id")
        csr_pem = body.get("csr_pem")
        if not isinstance(device_id, str) or not DEVICE_ID_PATTERN.match(device_id):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid device_id"})
            return
        if not isinstance(csr_pem, str) or "BEGIN CERTIFICATE REQUEST" not in csr_pem:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid csr_pem"})
            return

        bootstrap_token = self.headers.get("X-Bootstrap-Token", "").strip()
        try:
            result = self.server.bootstrap_service.enroll(
                device_id=device_id,
                csr_pem=csr_pem,
                bootstrap_token=bootstrap_token,
            )
            self._json_response(HTTPStatus.CREATED, result)
        except BootstrapError as exc:
            message = str(exc)
            if "already enrolled" in message:
                status = HTTPStatus.CONFLICT
            elif message == "bootstrap enrollment denied":
                status = HTTPStatus.UNAUTHORIZED
            else:
                status = HTTPStatus.BAD_REQUEST
            self._json_response(status, {"error": message})

    def _rotate_certificate(self, device_id: str, body: Dict[str, Any]) -> None:
        if self.server.bootstrap_service is None:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": "bootstrap is not enabled"})
            return

        unknown = set(body.keys()) - {"csr_pem"}
        if unknown:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": f"unknown fields: {', '.join(sorted(unknown))}"},
            )
            return

        csr_pem = body.get("csr_pem")
        if not isinstance(csr_pem, str) or "BEGIN CERTIFICATE REQUEST" not in csr_pem:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid csr_pem"})
            return

        try:
            result = self.server.bootstrap_service.rotate_certificate(
                device_id=device_id,
                csr_pem=csr_pem,
            )
            self._json_response(HTTPStatus.OK, result)
        except BootstrapError as exc:
            message = str(exc)
            status = HTTPStatus.NOT_FOUND if "not enrolled" in message else HTTPStatus.BAD_REQUEST
            self._json_response(status, {"error": message})

    def _register_device(self, body: Dict[str, Any]) -> None:
        unknown = set(body.keys()) - {"device_id", "policy"}
        if unknown:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": f"unknown fields: {', '.join(sorted(unknown))}"},
            )
            return

        device_id = body.get("device_id")
        if not isinstance(device_id, str) or not DEVICE_ID_PATTERN.match(device_id):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid device_id"})
            return

        policy = body.get("policy", {})
        if not isinstance(policy, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "policy must be an object"})
            return

        try:
            device = self.server.registry.register_device(device_id, policy)
            self.server.audit.record("device_registered", {"device_id": device_id})
            self._json_response(HTTPStatus.CREATED, device)
        except RegistryError as exc:
            self._json_response(HTTPStatus.CONFLICT, {"error": str(exc)})

    def _update_policy(self, device_id: str, body: Dict[str, Any]) -> None:
        unknown = set(body.keys()) - {"policy"}
        if unknown:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": f"unknown fields: {', '.join(sorted(unknown))}"},
            )
            return

        policy = body.get("policy")
        if not isinstance(policy, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "policy must be an object"})
            return

        try:
            device = self.server.registry.update_policy(device_id, policy)
            self.server.audit.record("policy_updated", {"device_id": device_id})
            self._json_response(HTTPStatus.OK, device)
        except RegistryError as exc:
            self._json_response(HTTPStatus.NOT_FOUND, {"error": str(exc)})

    def _issue_command(self, device_id: str, body: Dict[str, Any]) -> None:
        unknown = set(body.keys()) - {"action", "params"}
        if unknown:
            self._json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": f"unknown fields: {', '.join(sorted(unknown))}"},
            )
            return

        action = body.get("action")
        params = body.get("params")
        if not isinstance(action, str) or not action.strip():
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "action is required"})
            return
        if not isinstance(params, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "params must be an object"})
            return

        try:
            result = self.server.service.issue_command(device_id, action.strip(), params)
            self._json_response(HTTPStatus.ACCEPTED, result)
        except ControlPlaneNotLeaderError as exc:
            self._json_response(HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)})
        except ControlPlaneError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except CommandValidationError as exc:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            logger.exception("command publish failed")
            self._json_response(HTTPStatus.BAD_GATEWAY, {"error": str(exc)})

    def _check_api_rate_limit(self) -> bool:
        if self.server.api_rate_limiter is None:
            return True

        client_key = self.client_address[0]
        if self.server.api_rate_limiter.allow(client_key):
            return True

        self._json_response(
            HTTPStatus.TOO_MANY_REQUESTS,
            {"error": "rate limit exceeded"},
        )
        return False

    def _authorize(self) -> bool:
        expected = self.server.api_token
        if not expected:
            self._json_response(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": "control plane API token is not configured"},
            )
            return False

        header = self.headers.get("Authorization", "")
        token = self._parse_bearer_token(header)
        if token is None or not secrets.compare_digest(token, expected):
            self._json_response(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False
        return True

    @staticmethod
    def _parse_bearer_token(header: str) -> Optional[str]:
        if not header.startswith("Bearer "):
            return None
        return header[7:].strip()

    def _read_json_body(self) -> Optional[Dict[str, Any]]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "request body required"})
            return None

        raw = self.rfile.read(length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "invalid JSON body"})
            return None

        if not isinstance(parsed, dict):
            self._json_response(HTTPStatus.BAD_REQUEST, {"error": "JSON body must be an object"})
            return None
        return parsed

    def _json_response(self, status: HTTPStatus, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ControlPlaneHttpServer(ThreadingHTTPServer):
    """HTTP server with injected control plane dependencies."""

    def __init__(
        self,
        server_address: Tuple[str, int],
        registry: RegistryBackend,
        service: ControlPlaneService,
        audit: AuditLog,
        api_token: str,
        bootstrap_service: Optional[BootstrapService] = None,
        bootstrap_rate_limiter: Optional[RateLimiter] = None,
        api_rate_limiter: Optional[RateLimiter] = None,
        leader_elector: Optional[LeaderElector] = None,
        readiness_check: Optional[Callable[[], Dict[str, Any]]] = None,
    ) -> None:
        self.registry = registry
        self.service = service
        self.audit = audit
        self.api_token = api_token
        self.bootstrap_service = bootstrap_service
        self.bootstrap_rate_limiter = bootstrap_rate_limiter
        self.api_rate_limiter = api_rate_limiter
        self.leader_elector = leader_elector
        self.readiness_check = readiness_check or (lambda: {"ready": True, "checks": {}})
        super().__init__(server_address, ControlPlaneApiHandler)
