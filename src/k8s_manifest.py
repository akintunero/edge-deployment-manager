#!/usr/bin/env python3
"""Apply Kubernetes manifests using the dynamic client (create-or-replace)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import yaml
from kubernetes import client
from kubernetes.client.rest import ApiException
from kubernetes.dynamic import DynamicClient
from kubernetes.dynamic.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


def load_manifest_documents(path: str) -> List[Dict[str, Any]]:
    """Load YAML manifest documents from a file."""
    manifest_path = Path(path)
    if not manifest_path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")

    documents: List[Dict[str, Any]] = []
    with manifest_path.open("r", encoding="utf-8") as handle:
        for document in yaml.safe_load_all(handle):
            if not document or not isinstance(document, dict):
                continue
            if "kind" not in document or "apiVersion" not in document:
                raise ValueError("manifest documents must include kind and apiVersion")
            documents.append(document)
    return documents


def apply_manifest(
    api_client: client.ApiClient,
    resource: Dict[str, Any],
    default_namespace: str,
) -> None:
    """Create a resource or replace it when it already exists."""
    metadata = dict(resource.get("metadata") or {})
    namespace = str(metadata.get("namespace") or default_namespace)
    metadata["namespace"] = namespace
    resource = dict(resource)
    resource["metadata"] = metadata

    name = metadata.get("name")
    if not name:
        raise ValueError(f"{resource.get('kind')} manifest requires metadata.name")

    dyn_client = DynamicClient(api_client)
    api = dyn_client.resources.get(api_version=resource["apiVersion"], kind=resource["kind"])

    try:
        api.get(name=name, namespace=namespace)
    except ResourceNotFoundError:
        api.create(body=resource, namespace=namespace)
        logger.info("Created %s/%s in namespace %s", resource["kind"], name, namespace)
        return

    api.replace(body=resource, name=name, namespace=namespace)
    logger.info("Replaced %s/%s in namespace %s", resource["kind"], name, namespace)


def apply_manifests_from_file(
    api_client: client.ApiClient,
    yaml_file: str,
    namespace: str = "default",
    *,
    allowed_kinds: Optional[Iterable[str]] = None,
) -> bool:
    """Apply all supported documents from a multi-document YAML file."""
    allowed = set(allowed_kinds) if allowed_kinds is not None else None

    try:
        documents = load_manifest_documents(yaml_file)
        for document in documents:
            kind = str(document.get("kind", ""))
            if allowed is not None and kind not in allowed:
                logger.warning("Skipping unsupported resource kind: %s", kind)
                continue
            apply_manifest(api_client, document, namespace)
        return True
    except (FileNotFoundError, ValueError, yaml.YAMLError) as exc:
        logger.error("Manifest apply failed: %s", exc)
        return False
    except ApiException as exc:
        logger.error("Kubernetes API error applying %s: %s", yaml_file, exc)
        return False
