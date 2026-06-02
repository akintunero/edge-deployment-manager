#!/usr/bin/env python3
"""Tests for secret resolution."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from src.secrets import SecretNotFoundError, SecretProvider


class TestSecretProvider(unittest.TestCase):
    """SecretProvider resolution tests."""

    def test_reads_environment_variable(self) -> None:
        os.environ["TEST_EDGE_SECRET"] = "from-env"
        try:
            provider = SecretProvider(secrets_dir=Path("/nonexistent"))
            self.assertEqual(provider.get("TEST_EDGE_SECRET"), "from-env")
        finally:
            os.environ.pop("TEST_EDGE_SECRET", None)

    def test_reads_mounted_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            secret_dir = Path(temp_dir)
            (secret_dir / "CONTROL_PLANE_API_TOKEN").write_text("from-file\n", encoding="utf-8")
            provider = SecretProvider(secrets_dir=secret_dir)
            self.assertEqual(provider.get("CONTROL_PLANE_API_TOKEN"), "from-file")

    def test_missing_secret_raises(self) -> None:
        provider = SecretProvider(secrets_dir=Path("/nonexistent-edge-secrets"))
        with self.assertRaises(SecretNotFoundError):
            provider.get("MISSING_EDGE_SECRET")


if __name__ == "__main__":
    unittest.main()
