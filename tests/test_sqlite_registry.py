#!/usr/bin/env python3
"""Tests for SQLite device registry backend."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from src.control_plane.registry import RegistryError
from src.control_plane.sqlite_registry import SqliteDeviceRegistry


class TestSqliteDeviceRegistry(unittest.TestCase):
    """SQLite registry persistence tests."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "devices.db"

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir)

    def test_register_and_reload_from_disk(self) -> None:
        policy = {
            "allowed_actions": ["deploy"],
            "allowed_deployment_types": ["docker"],
            "allowed_images": ["nginx:*"],
        }

        registry = SqliteDeviceRegistry(self.db_path)
        registry.register_device("edge-agent-001", policy)

        reloaded = SqliteDeviceRegistry(self.db_path)
        device = reloaded.get_device("edge-agent-001")
        self.assertIsNotNone(device)
        assert device is not None
        self.assertEqual(device["policy"]["allowed_images"], ["nginx:*"])

    def test_register_conflict(self) -> None:
        registry = SqliteDeviceRegistry(self.db_path)
        policy = {"allowed_actions": ["deploy"]}
        registry.register_device("edge-agent-001", policy)
        with self.assertRaises(RegistryError):
            registry.register_device("edge-agent-001", policy)


if __name__ == "__main__":
    unittest.main()
