#!/usr/bin/env python3
"""Tests for Kubernetes manifest loading and apply helpers."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from kubernetes.dynamic.exceptions import ResourceNotFoundError

from src.k8s_manifest import apply_manifest, apply_manifests_from_file, load_manifest_documents


class TestK8sManifest(unittest.TestCase):
    """Kubernetes manifest helper tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.manifest_path = Path(self.temp_dir) / "deployment.yaml"
        self.manifest_path.write_text(
            "\n".join(
                [
                    "apiVersion: apps/v1",
                    "kind: Deployment",
                    "metadata:",
                    "  name: web",
                    "spec:",
                    "  replicas: 1",
                    "  selector:",
                    "    matchLabels:",
                    "      app: web",
                    "  template:",
                    "    metadata:",
                    "      labels:",
                    "        app: web",
                    "    spec:",
                    "      containers:",
                    "        - name: web",
                    "          image: nginx:1.27",
                    "---",
                    "apiVersion: v1",
                    "kind: Service",
                    "metadata:",
                    "  name: web",
                    "spec:",
                    "  selector:",
                    "    app: web",
                    "  ports:",
                    "    - port: 80",
                    "      targetPort: 80",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_load_manifest_documents(self) -> None:
        documents = load_manifest_documents(str(self.manifest_path))
        self.assertEqual(len(documents), 2)
        self.assertEqual(documents[0]["kind"], "Deployment")

    @patch("src.k8s_manifest.DynamicClient")
    def test_apply_manifest_creates_when_missing(self, dynamic_client_mock: MagicMock) -> None:
        api = MagicMock()
        api.get.side_effect = ResourceNotFoundError()
        dynamic_client_mock.return_value.resources.get.return_value = api

        apply_manifest(
            MagicMock(),
            {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "metadata": {"name": "web"},
                "spec": {},
            },
            "edge-apps",
        )

        api.create.assert_called_once()
        api.replace.assert_not_called()

    @patch("src.k8s_manifest.apply_manifest")
    def test_apply_manifests_from_file(self, apply_mock: MagicMock) -> None:
        api_client = MagicMock()
        self.assertTrue(
            apply_manifests_from_file(api_client, str(self.manifest_path), "edge-apps")
        )
        self.assertEqual(apply_mock.call_count, 2)


if __name__ == "__main__":
    unittest.main()
