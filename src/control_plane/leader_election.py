#!/usr/bin/env python3
"""PostgreSQL advisory-lock leader election for control plane replicas."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Optional

from ..observability import METRICS

logger = logging.getLogger(__name__)


class LeaderElector:
    """
    Elect a single active leader using pg_try_advisory_lock on a dedicated session.

    The lock is held for the lifetime of the leader connection.
    """

    def __init__(
        self,
        database_url: str,
        lock_key: int,
        holder_id: str,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        try:
            import psycopg
        except ImportError as exc:
            raise ValueError(
                "psycopg is required for HA leader election; " "pip install 'edge-deployment-manager[postgres]'"
            ) from exc

        self._database_url = database_url
        self._lock_key = lock_key
        self._holder_id = holder_id
        self._poll_interval_seconds = poll_interval_seconds
        self._psycopg = psycopg

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._leader_conn: Any = None
        self._is_leader = False

    @property
    def holder_id(self) -> str:
        return self._holder_id

    @property
    def is_leader(self) -> bool:
        with self._lock:
            return self._is_leader

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, name="leader-elector", daemon=True)
        self._thread.start()
        logger.info("Leader election started for holder %s", self._holder_id)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5)
        self._release_leadership()

    def _run(self) -> None:
        while self._running:
            if not self.is_leader:
                self._try_acquire()
            else:
                self._verify_leadership()
            time.sleep(self._poll_interval_seconds)

    def _try_acquire(self) -> None:
        connection = None
        try:
            connection = self._psycopg.connect(self._database_url)
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_try_advisory_lock(%s)", (self._lock_key,))
                acquired = cursor.fetchone()[0]
            if not acquired:
                connection.close()
                return

            with self._lock:
                self._leader_conn = connection
                self._is_leader = True
            METRICS.set_gauge("edge_control_plane_is_leader", 1)
            logger.info("Acquired leader lock for holder %s", self._holder_id)
        except Exception as exc:
            logger.warning("Leader election acquire failed: %s", exc)
            if connection is not None:
                connection.close()

    def _verify_leadership(self) -> None:
        try:
            with self._lock:
                connection = self._leader_conn
            if connection is None:
                self._mark_follower()
                return
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
        except Exception as exc:
            logger.warning("Leader session lost for %s: %s", self._holder_id, exc)
            self._release_leadership()

    def _release_leadership(self) -> None:
        with self._lock:
            connection = self._leader_conn
            self._leader_conn = None
            self._is_leader = False

        if connection is None:
            METRICS.set_gauge("edge_control_plane_is_leader", 0)
            return

        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_advisory_unlock(%s)", (self._lock_key,))
            connection.close()
        except Exception as exc:
            logger.warning("Leader lock release failed: %s", exc)
        METRICS.set_gauge("edge_control_plane_is_leader", 0)
        logger.info("Released leader lock for holder %s", self._holder_id)

    def _mark_follower(self) -> None:
        with self._lock:
            self._is_leader = False
            self._leader_conn = None
        METRICS.set_gauge("edge_control_plane_is_leader", 0)
