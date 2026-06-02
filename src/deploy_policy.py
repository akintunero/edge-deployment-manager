#!/usr/bin/env python3
"""Shared deployment policy checks for agents and control plane."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict

from .command_envelope import CommandValidationError


def enforce_deploy_policy(params: Dict[str, Any], policy: Dict[str, Any]) -> None:
    """Ensure deploy params comply with a device policy object."""
    deployment_type = params.get("type", "docker")
    allowed_types = policy.get("allowed_deployment_types", ["docker", "kubernetes"])
    if deployment_type not in allowed_types:
        raise CommandValidationError(f"deployment type not allowed: {deployment_type}")

    if deployment_type == "docker":
        _enforce_docker_policy(params, policy)
    else:
        _enforce_kubernetes_policy(params, policy)


def _enforce_docker_policy(params: Dict[str, Any], policy: Dict[str, Any]) -> None:
    allowed_images = policy.get("allowed_images")
    if not allowed_images:
        return

    image = params.get("image", "")
    if not any(fnmatch.fnmatchcase(image, pattern) for pattern in allowed_images):
        raise CommandValidationError("docker image is not allowed by policy")


def _enforce_kubernetes_policy(params: Dict[str, Any], policy: Dict[str, Any]) -> None:
    allowed_roots = policy.get("allowed_yaml_roots", [])
    if not allowed_roots:
        return

    yaml_file = params.get("yaml_file", "")
    resolved = Path(yaml_file).expanduser().resolve()
    for root in allowed_roots:
        root_path = Path(root).expanduser().resolve()
        try:
            resolved.relative_to(root_path)
            return
        except ValueError:
            continue

    raise CommandValidationError("kubernetes manifest path is not allowed by policy")
