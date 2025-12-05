"""
GrowPi SQLite Database Manager

Thread-safe SQLite connection manager mit automatischer Schema-Migration.
"""

import sqlite3
import logging
import os
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

from .models import SensorReading, LampStateLog, SystemEvent

logger = logging.getLogger(__name__)

# Default database path
DEFAULT_DB_PATH = '/opt/grow-pi/data/growpi.db'

# SQL Schema
SCHEMA_SQL = """
-- Sensor Readings Table
CREATE TABLE IF NOT EXISTS sensor_readings (
    id TEXT PRIMARY KEY,
    sensor_type TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT NOT NULL,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_type_time
ON sensor_readings(sensor_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_sensor_readings_synced
ON sensor_readings(synced_at);

-- Lamp State Log Table
CREATE TABLE IF NOT EXISTS lamp_state_log (
    id TEXT PRIMARY KEY,
    channel INTEGER NOT NULL,
    name TEXT NOT NULL,
    intensity INTEGER NOT NULL,
    source TEXT NOT NULL,
    curve_time TEXT,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_lamp_state_channel_time
ON lamp_state_log(channel, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_lamp_state_synced
ON lamp_state_log(synced_at);

-- System Events Table
CREATE TABLE IF NOT EXISTS system_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_system_events_type_time
ON system_events(event_type, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_system_events_severity
ON system_events(severity, created_at DESC);

-- Sync Status Table (single row)
CREATE TABLE IF NOT EXISTS sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    last_sync TEXT,
    last_attempt TEXT,
    readings_pending INTEGER DEFAULT 0,
    lamp_logs_pending INTEGER DEFAULT 0,
    status TEXT DEFAULT 'never',
    error_message TEXT
);

-- Insert initial sync status if not exists
INSERT OR IGNORE INTO sync_status (id, status) VALUES (1, 'never');
"""


class Database:
    """
    Thread-safe SQLite Database Manager.

    Usage:
        db = Database('/path/to/growpi.db')
        db.initialize()

        # Insert sensor reading
        reading = SensorReading('temperature', 22.5, '°C')
        db.insert_sensor_reading(reading)

        # Query readings
        readings = db.get_sensor_readings('temperature', hours=24)
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        """
        Initialize database manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            # Create connection with optimized settings
            self._local.connection = sqlite3.connect(
                self.db_path,
                detect_types=sqlite3.PARSE_DECLTYPES,
                check_same_thread=False
            )
            # Enable WAL mode for better concurrent access
            self._local.connection.execute('PRAGMA journal_mode=WAL')
            # Enable foreign keys
            self._local.connection.execute('PRAGMA foreign_keys=ON')
            # Optimize for performance
            self._local.connection.execute('PRAGMA synchronous=NORMAL')

        return self._local.connection

    @contextmanager
    def _cursor(self):
        """Context manager for database cursor with auto-commit."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

    def initialize(self) -> None:
        """Initialize database schema."""
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return

            logger.info(f"Initializing database at: {self.db_path}")

            with self._cursor() as cursor:
                cursor.executescript(SCHEMA_SQL)

            self._initialized = True
            logger.info("Database initialized successfully")

    def close(self) -> None:
        """Close database connection."""
        if hasattr(self._local, 'connection') and self._local.connection:
            self._local.connection.close()
            self._local.connection = None

    # =========================================================================
    # Sensor Readings
    # =========================================================================

    def insert_sensor_reading(self, reading: SensorReading) -> None:
        """Insert a sensor reading."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO sensor_readings (id, sensor_type, value, unit, created_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (reading.id, reading.sensor_type, reading.value,
                 reading.unit, reading.created_at, reading.synced_at)
            )

    def get_sensor_readings(
        self,
        sensor_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[SensorReading]:
        """
        Get sensor readings.

        Args:
            sensor_type: Filter by sensor type (None = all)
            hours: Get readings from last N hours
            limit: Maximum number of readings
        """
        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            if sensor_type:
                cursor.execute(
                    """
                    SELECT id, sensor_type, value, unit, created_at, synced_at
                    FROM sensor_readings
                    WHERE sensor_type = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (sensor_type, since, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, sensor_type, value, unit, created_at, synced_at
                    FROM sensor_readings
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (since, limit)
                )

            return [SensorReading.from_row(row) for row in cursor.fetchall()]

    def get_latest_sensor_reading(self, sensor_type: str) -> Optional[SensorReading]:
        """Get the most recent reading for a sensor type."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, sensor_type, value, unit, created_at, synced_at
                FROM sensor_readings
                WHERE sensor_type = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (sensor_type,)
            )
            row = cursor.fetchone()
            return SensorReading.from_row(row) if row else None

    # =========================================================================
    # Lamp State Log
    # =========================================================================

    def insert_lamp_state(self, state: LampStateLog) -> None:
        """Insert a lamp state log entry."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO lamp_state_log
                (id, channel, name, intensity, source, curve_time, created_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (state.id, state.channel, state.name, state.intensity,
                 state.source, state.curve_time, state.created_at, state.synced_at)
            )

    def get_lamp_state_log(
        self,
        channel: Optional[int] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[LampStateLog]:
        """
        Get lamp state log entries.

        Args:
            channel: Filter by channel (None = all)
            hours: Get entries from last N hours
            limit: Maximum number of entries
        """
        since = (datetime.now() - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            if channel:
                cursor.execute(
                    """
                    SELECT id, channel, name, intensity, source, curve_time, created_at, synced_at
                    FROM lamp_state_log
                    WHERE channel = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (channel, since, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, channel, name, intensity, source, curve_time, created_at, synced_at
                    FROM lamp_state_log
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (since, limit)
                )

            return [LampStateLog.from_row(row) for row in cursor.fetchall()]

    def get_latest_lamp_state(self, channel: int) -> Optional[LampStateLog]:
        """Get the most recent state for a lamp channel."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, channel, name, intensity, source, curve_time, created_at, synced_at
                FROM lamp_state_log
                WHERE channel = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (channel,)
            )
            row = cursor.fetchone()
            return LampStateLog.from_row(row) if row else None

    def should_log_lamp_state(self, channel: int, intensity: int, dedupe_seconds: int = 5) -> bool:
        """
        Check if lamp state should be logged (deduplication).

        Returns False if last log for this channel was within dedupe_seconds
        and had the same intensity.
        """
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT intensity, created_at
                FROM lamp_state_log
                WHERE channel = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (channel,)
            )
            row = cursor.fetchone()

            if not row:
                return True  # No previous log, should log

            last_intensity, last_time_str = row

            # Different intensity? Always log
            if last_intensity != intensity:
                return True

            # Check time difference
            try:
                last_time = datetime.fromisoformat(last_time_str)
                time_diff = (datetime.now() - last_time).total_seconds()
                return time_diff >= dedupe_seconds
            except (ValueError, TypeError):
                return True  # Can't parse time, log anyway

    # =========================================================================
    # System Events
    # =========================================================================

    def insert_system_event(self, event: SystemEvent) -> None:
        """Insert a system event."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO system_events (id, event_type, severity, message, details, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (event.id, event.event_type, event.severity,
                 event.message, event.details, event.created_at)
            )

    def get_system_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[SystemEvent]:
        """Get system events with optional filters."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        conditions = ["created_at >= ?"]
        params = [since]

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if severity:
            conditions.append("severity = ?")
            params.append(severity)

        params.append(limit)
        where_clause = " AND ".join(conditions)

        with self._cursor() as cursor:
            cursor.execute(
                f"""
                SELECT id, event_type, severity, message, details, created_at
                FROM system_events
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                params
            )
            return [SystemEvent.from_row(row) for row in cursor.fetchall()]

    # =========================================================================
    # Statistics & Maintenance
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with self._cursor() as cursor:
            # Count records
            cursor.execute("SELECT COUNT(*) FROM sensor_readings")
            sensor_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lamp_state_log")
            lamp_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM system_events")
            event_count = cursor.fetchone()[0]

            # Count unsynced
            cursor.execute("SELECT COUNT(*) FROM sensor_readings WHERE synced_at IS NULL")
            sensor_unsynced = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lamp_state_log WHERE synced_at IS NULL")
            lamp_unsynced = cursor.fetchone()[0]

            # Database file size
            db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

            return {
                'sensor_readings': sensor_count,
                'lamp_state_logs': lamp_count,
                'system_events': event_count,
                'sensor_unsynced': sensor_unsynced,
                'lamp_unsynced': lamp_unsynced,
                'database_size_bytes': db_size,
                'database_size_mb': round(db_size / (1024 * 1024), 2),
            }

    def cleanup_old_data(self, retention_days: int = 30) -> Dict[str, int]:
        """
        Delete data older than retention_days that has been synced.

        Returns count of deleted records per table.
        """
        cutoff = (datetime.now() - timedelta(days=retention_days)).isoformat()
        deleted = {}

        with self._cursor() as cursor:
            # Delete synced sensor readings
            cursor.execute(
                """
                DELETE FROM sensor_readings
                WHERE created_at < ? AND synced_at IS NOT NULL
                """,
                (cutoff,)
            )
            deleted['sensor_readings'] = cursor.rowcount

            # Delete synced lamp logs
            cursor.execute(
                """
                DELETE FROM lamp_state_log
                WHERE created_at < ? AND synced_at IS NOT NULL
                """,
                (cutoff,)
            )
            deleted['lamp_state_log'] = cursor.rowcount

            # Delete old system events (always, regardless of sync)
            cursor.execute(
                "DELETE FROM system_events WHERE created_at < ?",
                (cutoff,)
            )
            deleted['system_events'] = cursor.rowcount

        # Optimize database after deletion
        self._get_connection().execute('VACUUM')

        logger.info(f"Cleanup completed: {deleted}")
        return deleted


# Global database instance
_db_instance: Optional[Database] = None
_db_lock = threading.Lock()


def get_database(db_path: str = DEFAULT_DB_PATH) -> Database:
    """
    Get or create global database instance.

    Thread-safe singleton pattern.
    """
    global _db_instance

    if _db_instance is None:
        with _db_lock:
            if _db_instance is None:
                _db_instance = Database(db_path)
                _db_instance.initialize()

    return _db_instance
