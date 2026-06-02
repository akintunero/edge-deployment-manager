#!/usr/bin/env python3
"""Leader election unit tests."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import MagicMock, patch

from src.control_plane.leader_election import LeaderElector


class TestLeaderElector(unittest.TestCase):
    """PostgreSQL advisory lock elector tests."""

    def test_acquire_sets_leader(self) -> None:
        fake_psycopg = MagicMock()
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (True,)
        connection.cursor.return_value.__enter__.return_value = cursor
        fake_psycopg.connect.return_value = connection

        with patch.dict(sys.modules, {"psycopg": fake_psycopg}):
            elector = LeaderElector(
                database_url="postgresql://edge:edge@localhost/edge",
                lock_key=84001,
                holder_id="replica-a",
                poll_interval_seconds=0.01,
            )
            elector._try_acquire()

        self.assertTrue(elector.is_leader)
        fake_psycopg.connect.assert_called_once()

    def test_failed_acquire_stays_follower(self) -> None:
        fake_psycopg = MagicMock()
        connection = MagicMock()
        cursor = MagicMock()
        cursor.fetchone.return_value = (False,)
        connection.cursor.return_value.__enter__.return_value = cursor
        fake_psycopg.connect.return_value = connection

        with patch.dict(sys.modules, {"psycopg": fake_psycopg}):
            elector = LeaderElector(
                database_url="postgresql://edge:edge@localhost/edge",
                lock_key=84001,
                holder_id="replica-b",
            )
            elector._try_acquire()

        self.assertFalse(elector.is_leader)
        connection.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
