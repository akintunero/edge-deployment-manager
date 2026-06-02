#!/usr/bin/env python3
"""End-to-end verification for the local production Docker Compose stack."""

from __future__ import annotations

import argparse
import json
import os
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _ssl_context() -> ssl.SSLContext:
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


def _request(
    method: str,
    url: str,
    *,
    token: Optional[str] = None,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 10.0,
) -> Tuple[int, Dict[str, Any]]:
    data = None
    headers: Dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, context=_ssl_context(), timeout=timeout) as response:
            payload = response.read().decode("utf-8")
            parsed = json.loads(payload) if payload else {}
            if not isinstance(parsed, dict):
                parsed = {}
            return response.status, parsed
    except urllib.error.HTTPError as exc:
        payload = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(payload)
            if not isinstance(parsed, dict):
                parsed = {"error": payload}
        except json.JSONDecodeError:
            parsed = {"error": payload}
        return exc.code, parsed


def _wait_for_url(url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            status, _ = _request("GET", url, timeout=5.0)
            if status == 200:
                return
        except urllib.error.URLError:
            pass
        time.sleep(2)
    raise RuntimeError(f"timeout waiting for {url}")


def _docker_container_running(name: str) -> bool:
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={name}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
        check=False,
    )
    return name in result.stdout


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify production stack E2E")
    parser.add_argument(
        "--control-plane-url",
        default=os.environ.get("CONTROL_PLANE_URL", "https://localhost:8080"),
    )
    parser.add_argument("--device-id", default="edge-agent-001")
    parser.add_argument("--deploy-name", default="nginx-edge-demo")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--skip-docker-check", action="store_true")
    args = parser.parse_args()

    _load_env(ROOT / ".env")
    api_token = os.environ.get("CONTROL_PLANE_API_TOKEN", "")
    if not api_token:
        raise SystemExit("CONTROL_PLANE_API_TOKEN is not set")

    base = args.control_plane_url.rstrip("/")
    print(f"Waiting for control plane at {base}/health")
    _wait_for_url(f"{base}/health", args.timeout)

    device_path = f"{base}/v1/devices/{args.device_id}"
    status, device = _request("GET", device_path, token=api_token)
    if status == 404:
        print(f"Registering device {args.device_id}")
        status, device = _request(
            "POST",
            f"{base}/v1/devices",
            token=api_token,
            body={
                "device_id": args.device_id,
                "policy": {
                    "allowed_actions": ["deploy"],
                    "allowed_deployment_types": ["docker"],
                    "allowed_images": ["nginx:*"],
                },
            },
        )
        if status not in {200, 201}:
            raise SystemExit(f"device registration failed ({status}): {device}")

    print("Issuing signed deploy command")
    deploy_body = json.loads(
        (ROOT / "examples" / "nginx-deploy-command.json").read_text(encoding="utf-8")
    )
    status, result = _request(
        "POST",
        f"{device_path}/commands",
        token=api_token,
        body=deploy_body,
    )
    if status not in {200, 202}:
        raise SystemExit(f"command publish failed ({status}): {result}")

    print(f"Command published: {result.get('command_id', 'unknown')}")

    if args.skip_docker_check:
        print("Skipping Docker verification")
        return

    deadline = time.time() + args.timeout
    while time.time() < deadline:
        if _docker_container_running(args.deploy_name):
            print(f"Container {args.deploy_name} is running")
            return
        time.sleep(3)

    raise SystemExit(f"container {args.deploy_name} did not start within {args.timeout}s")


if __name__ == "__main__":
    try:
        main()
    except SystemExit as exc:
        if exc.code:
            raise
    except Exception as exc:
        print(f"E2E failed: {exc}", file=sys.stderr)
        sys.exit(1)
