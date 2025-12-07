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

from .models import SensorReading, LampStateLog, SystemEvent, LampCurve, PlugLog, CurvePreset

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

-- Lamp Curves Table (per-channel curves)
CREATE TABLE IF NOT EXISTS lamp_curves (
    id TEXT PRIMARY KEY,
    channel INTEGER NOT NULL UNIQUE,
    name TEXT NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1,
    curve TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_lamp_curves_channel
ON lamp_curves(channel);

-- Plug Logs Table
CREATE TABLE IF NOT EXISTS plug_logs (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    voltage REAL,
    current REAL,
    power REAL,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_plug_logs_device_time
ON plug_logs(device_id, created_at DESC);

-- Curve Presets Table (saved lighting curve configurations)
CREATE TABLE IF NOT EXISTS curve_presets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    curves_json TEXT NOT NULL,
    is_system INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_curve_presets_name
ON curve_presets(name);

CREATE INDEX IF NOT EXISTS idx_curve_presets_system
ON curve_presets(is_system);
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

    def get_sensor_readings_downsampled(
        self,
        sensor_type: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get sensor readings with intelligent downsampling based on time range.

        Downsampling rules:
        - 0-4 hours: Raw data (every minute)
        - 4-24 hours: 5-minute averages
        - 1-7 days: 15-minute averages
        - 7-30 days: 30-minute averages
        - >30 days: 1-hour averages

        Args:
            sensor_type: Filter by sensor type (None = all)
            hours: Get readings from last N hours

        Returns:
            List of dicts with sensor reading data (averaged where applicable)
        """
        now = datetime.now()
        results = []

        # Define time boundaries
        boundary_4h = (now - timedelta(hours=4)).isoformat()
        boundary_24h = (now - timedelta(hours=24)).isoformat()
        boundary_7d = (now - timedelta(hours=168)).isoformat()
        boundary_30d = (now - timedelta(hours=720)).isoformat()
        start_time = (now - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            # Build type filter
            type_filter = "AND sensor_type = ?" if sensor_type else ""
            base_params = [sensor_type] if sensor_type else []

            # 1. Raw data for last 4 hours (or less if hours < 4)
            if hours > 0:
                raw_end = now.isoformat()
                raw_start = max(start_time, boundary_4h)

                query = f"""
                    SELECT sensor_type, value, unit, created_at
                    FROM sensor_readings
                    WHERE created_at >= ? AND created_at <= ? {type_filter}
                    ORDER BY created_at DESC
                """
                params = [raw_start, raw_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'sensor_type': row[0],
                        'value': row[1],
                        'unit': row[2],
                        'created_at': row[3]
                    })

            # 2. 5-minute averages for 4-24 hours
            if hours > 4:
                agg_start = max(start_time, boundary_24h)
                agg_end = boundary_4h

                query = f"""
                    SELECT
                        sensor_type,
                        AVG(value) as avg_value,
                        unit,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
                            ':00' as time_bucket
                    FROM sensor_readings
                    WHERE created_at >= ? AND created_at < ? {type_filter}
                    GROUP BY sensor_type, time_bucket, unit
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'sensor_type': row[0],
                        'value': round(row[1], 2),
                        'unit': row[2],
                        'created_at': row[3]
                    })

            # 3. 15-minute averages for 1-7 days
            if hours > 24:
                agg_start = max(start_time, boundary_7d)
                agg_end = boundary_24h

                query = f"""
                    SELECT
                        sensor_type,
                        AVG(value) as avg_value,
                        unit,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 15) * 15) ||
                            ':00' as time_bucket
                    FROM sensor_readings
                    WHERE created_at >= ? AND created_at < ? {type_filter}
                    GROUP BY sensor_type, time_bucket, unit
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'sensor_type': row[0],
                        'value': round(row[1], 2),
                        'unit': row[2],
                        'created_at': row[3]
                    })

            # 4. 30-minute averages for 7-30 days
            if hours > 168:
                agg_start = max(start_time, boundary_30d)
                agg_end = boundary_7d

                query = f"""
                    SELECT
                        sensor_type,
                        AVG(value) as avg_value,
                        unit,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 30) * 30) ||
                            ':00' as time_bucket
                    FROM sensor_readings
                    WHERE created_at >= ? AND created_at < ? {type_filter}
                    GROUP BY sensor_type, time_bucket, unit
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'sensor_type': row[0],
                        'value': round(row[1], 2),
                        'unit': row[2],
                        'created_at': row[3]
                    })

            # 5. Hourly averages for >30 days
            if hours > 720:
                agg_start = start_time
                agg_end = boundary_30d

                query = f"""
                    SELECT
                        sensor_type,
                        AVG(value) as avg_value,
                        unit,
                        strftime('%Y-%m-%dT%H:00:00', created_at) as time_bucket
                    FROM sensor_readings
                    WHERE created_at >= ? AND created_at < ? {type_filter}
                    GROUP BY sensor_type, time_bucket, unit
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'sensor_type': row[0],
                        'value': round(row[1], 2),
                        'unit': row[2],
                        'created_at': row[3]
                    })

        # Sort all results by created_at descending
        results.sort(key=lambda x: x['created_at'], reverse=True)
        return results

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

    def get_lamp_state_log_downsampled(
        self,
        channel: Optional[int] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get lamp state log entries with intelligent downsampling based on time range.

        Downsampling rules:
        - 0-4 hours: Raw data (every minute)
        - 4-24 hours: 5-minute averages
        - 1-7 days: 15-minute averages
        - 7-30 days: 30-minute averages
        - >30 days: 1-hour averages

        Args:
            channel: Filter by channel (None = all)
            hours: Get entries from last N hours

        Returns:
            List of dicts with lamp state data (averaged intensities where applicable)
        """
        now = datetime.now()
        results = []

        # Define time boundaries
        boundary_4h = (now - timedelta(hours=4)).isoformat()
        boundary_24h = (now - timedelta(hours=24)).isoformat()
        boundary_7d = (now - timedelta(hours=168)).isoformat()
        boundary_30d = (now - timedelta(hours=720)).isoformat()
        start_time = (now - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            # Build channel filter
            channel_filter = "AND channel = ?" if channel else ""
            base_params = [channel] if channel else []

            # 1. Raw data for last 4 hours
            if hours > 0:
                raw_end = now.isoformat()
                raw_start = max(start_time, boundary_4h)

                query = f"""
                    SELECT channel, name, intensity, source, curve_time, created_at
                    FROM lamp_state_log
                    WHERE created_at >= ? AND created_at <= ? {channel_filter}
                    ORDER BY created_at DESC
                """
                params = [raw_start, raw_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'channel': row[0],
                        'name': row[1],
                        'intensity': row[2],
                        'source': row[3],
                        'curve_time': row[4],
                        'created_at': row[5]
                    })

            # 2. 5-minute averages for 4-24 hours
            if hours > 4:
                agg_start = max(start_time, boundary_24h)
                agg_end = boundary_4h

                query = f"""
                    SELECT
                        channel,
                        name,
                        ROUND(AVG(intensity)) as avg_intensity,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
                            ':00' as time_bucket
                    FROM lamp_state_log
                    WHERE created_at >= ? AND created_at < ? {channel_filter}
                    GROUP BY channel, name, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'channel': row[0],
                        'name': row[1],
                        'intensity': int(row[2]),
                        'source': 'aggregated',
                        'curve_time': None,
                        'created_at': row[3]
                    })

            # 3. 15-minute averages for 1-7 days
            if hours > 24:
                agg_start = max(start_time, boundary_7d)
                agg_end = boundary_24h

                query = f"""
                    SELECT
                        channel,
                        name,
                        ROUND(AVG(intensity)) as avg_intensity,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 15) * 15) ||
                            ':00' as time_bucket
                    FROM lamp_state_log
                    WHERE created_at >= ? AND created_at < ? {channel_filter}
                    GROUP BY channel, name, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'channel': row[0],
                        'name': row[1],
                        'intensity': int(row[2]),
                        'source': 'aggregated',
                        'curve_time': None,
                        'created_at': row[3]
                    })

            # 4. 30-minute averages for 7-30 days
            if hours > 168:
                agg_start = max(start_time, boundary_30d)
                agg_end = boundary_7d

                query = f"""
                    SELECT
                        channel,
                        name,
                        ROUND(AVG(intensity)) as avg_intensity,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 30) * 30) ||
                            ':00' as time_bucket
                    FROM lamp_state_log
                    WHERE created_at >= ? AND created_at < ? {channel_filter}
                    GROUP BY channel, name, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'channel': row[0],
                        'name': row[1],
                        'intensity': int(row[2]),
                        'source': 'aggregated',
                        'curve_time': None,
                        'created_at': row[3]
                    })

            # 5. Hourly averages for >30 days
            if hours > 720:
                agg_start = start_time
                agg_end = boundary_30d

                query = f"""
                    SELECT
                        channel,
                        name,
                        ROUND(AVG(intensity)) as avg_intensity,
                        strftime('%Y-%m-%dT%H:00:00', created_at) as time_bucket
                    FROM lamp_state_log
                    WHERE created_at >= ? AND created_at < ? {channel_filter}
                    GROUP BY channel, name, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'channel': row[0],
                        'name': row[1],
                        'intensity': int(row[2]),
                        'source': 'aggregated',
                        'curve_time': None,
                        'created_at': row[3]
                    })

        # Sort all results by created_at descending
        results.sort(key=lambda x: x['created_at'], reverse=True)
        return results

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
    # Lamp Curves
    # =========================================================================

    def insert_lamp_curve(self, curve: LampCurve) -> None:
        """Insert or replace a lamp curve."""
        import json
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT OR REPLACE INTO lamp_curves
                (id, channel, name, enabled, curve, created_at, updated_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (curve.id, curve.channel, curve.name, int(curve.enabled),
                 json.dumps(curve.curve), curve.created_at, curve.updated_at, curve.synced_at)
            )

    def get_lamp_curve(self, channel: int) -> Optional[LampCurve]:
        """Get lamp curve for a specific channel."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, channel, name, enabled, curve, created_at, updated_at, synced_at
                FROM lamp_curves
                WHERE channel = ?
                """,
                (channel,)
            )
            row = cursor.fetchone()
            return LampCurve.from_row(row) if row else None

    def get_all_lamp_curves(self) -> List[LampCurve]:
        """Get all lamp curves."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, channel, name, enabled, curve, created_at, updated_at, synced_at
                FROM lamp_curves
                ORDER BY channel
                """
            )
            return [LampCurve.from_row(row) for row in cursor.fetchall()]

    def update_lamp_curve(self, channel: int, curve_points: List[Dict], enabled: bool = True) -> Optional[LampCurve]:
        """Update curve points for a channel."""
        import json
        from .models import now_iso

        existing = self.get_lamp_curve(channel)
        if not existing:
            return None

        with self._cursor() as cursor:
            cursor.execute(
                """
                UPDATE lamp_curves
                SET curve = ?, enabled = ?, updated_at = ?, synced_at = NULL
                WHERE channel = ?
                """,
                (json.dumps(curve_points), int(enabled), now_iso(), channel)
            )

        return self.get_lamp_curve(channel)

    def initialize_default_curves(self, channels: Dict[int, str]) -> None:
        """
        Initialize default curves for all channels if not exists.

        Default sunrise sequence (max 50%):
        - Far Red (ch1): Starts first at 05:00, reaches 50% by 06:00
        - Cool White (ch3): Starts 15min later at 05:15, reaches 50% by 06:15
        - Warm White (ch2): Starts 30min later at 05:30, reaches 50% by 06:30
        - UV (ch4): Always 0

        Sunset sequence (reverse order):
        - Warm White drops first at 20:00
        - Cool White drops 15min later
        - Far Red drops last

        Args:
            channels: Dict mapping channel number to name {1: "Far Red", ...}
        """
        import json
        from .models import now_iso, generate_uuid

        # Default curves - UV always 0
        default_curves = {
            1: [  # Far Red - starts first at 05:45, reaches 100%
                {"time": "05:45", "intensity": 0},
                {"time": "06:15", "intensity": 50},   # 30min: 0 → 50%
                {"time": "06:30", "intensity": 100},  # 15min: 50 → 100%
                {"time": "20:30", "intensity": 100},  # Start sunset last
                {"time": "21:00", "intensity": 50},
                {"time": "21:30", "intensity": 0},    # Sunset complete
            ],
            2: [  # Warm White - starts at 05:30 (unchanged)
                {"time": "05:30", "intensity": 0},
                {"time": "06:30", "intensity": 50},   # Sunrise complete
                {"time": "20:00", "intensity": 50},   # Start sunset first
                {"time": "21:00", "intensity": 0},    # Sunset complete
            ],
            3: [  # Cool White - starts at 06:00, gradual ramp
                {"time": "06:00", "intensity": 15},   # Start with 15%
                {"time": "06:30", "intensity": 30},   # 30min: 30%
                {"time": "07:00", "intensity": 50},   # 60min: 50% reached
                {"time": "20:15", "intensity": 50},   # Start sunset middle
                {"time": "21:15", "intensity": 0},    # Sunset complete
            ],
            4: [  # UV - always 0
                {"time": "00:00", "intensity": 0},
                {"time": "12:00", "intensity": 0},
            ],
        }

        for channel, name in channels.items():
            existing = self.get_lamp_curve(channel)
            if existing:
                logger.debug(f"Curve for channel {channel} already exists")
                continue

            curve = LampCurve(
                channel=channel,
                name=name,
                enabled=(channel != 4),  # UV disabled by default
                curve=default_curves.get(channel, []),
            )
            self.insert_lamp_curve(curve)
            logger.info(f"Created default curve for {name} (ch{channel})")

    # =========================================================================
    # Plug Logs
    # =========================================================================

    def insert_plug_log(self, log: PlugLog) -> None:
        """Insert a plug log entry."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO plug_logs (id, device_id, voltage, current, power, created_at, synced_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (log.id, log.device_id, log.voltage, log.current, log.power, log.created_at, log.synced_at)
            )

    def get_plug_logs(
        self,
        device_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[PlugLog]:
        """Get plug logs."""
        since = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        with self._cursor() as cursor:
            if device_id:
                cursor.execute(
                    """
                    SELECT id, device_id, voltage, current, power, created_at, synced_at
                    FROM plug_logs
                    WHERE device_id = ? AND created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (device_id, since, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, device_id, voltage, current, power, created_at, synced_at
                    FROM plug_logs
                    WHERE created_at >= ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (since, limit)
                )
            return [PlugLog.from_row(row) for row in cursor.fetchall()]

    def get_plug_logs_downsampled(
        self,
        device_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get plug logs with intelligent downsampling based on time range.

        Downsampling rules:
        - 0-4 hours: Raw data (every minute)
        - 4-24 hours: 5-minute averages
        - 1-7 days: 15-minute averages
        - 7-30 days: 30-minute averages
        - >30 days: 1-hour averages

        Args:
            device_id: Filter by device ID (None = all)
            hours: Get logs from last N hours

        Returns:
            List of dicts with plug log data (averaged power values where applicable)
        """
        now = datetime.now()
        results = []

        # Define time boundaries
        boundary_4h = (now - timedelta(hours=4)).isoformat()
        boundary_24h = (now - timedelta(hours=24)).isoformat()
        boundary_7d = (now - timedelta(hours=168)).isoformat()
        boundary_30d = (now - timedelta(hours=720)).isoformat()
        start_time = (now - timedelta(hours=hours)).isoformat()

        with self._cursor() as cursor:
            # Build device filter
            device_filter = "AND device_id = ?" if device_id else ""
            base_params = [device_id] if device_id else []

            # 1. Raw data for last 4 hours
            if hours > 0:
                raw_end = now.isoformat()
                raw_start = max(start_time, boundary_4h)

                query = f"""
                    SELECT device_id, voltage, current, power, created_at
                    FROM plug_logs
                    WHERE created_at >= ? AND created_at <= ? {device_filter}
                    ORDER BY created_at DESC
                """
                params = [raw_start, raw_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'device_id': row[0],
                        'voltage': row[1],
                        'current': row[2],
                        'power': row[3],
                        'created_at': row[4]
                    })

            # 2. 5-minute averages for 4-24 hours
            if hours > 4:
                agg_start = max(start_time, boundary_24h)
                agg_end = boundary_4h

                query = f"""
                    SELECT
                        device_id,
                        AVG(voltage) as avg_voltage,
                        AVG(current) as avg_current,
                        AVG(power) as avg_power,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5) ||
                            ':00' as time_bucket
                    FROM plug_logs
                    WHERE created_at >= ? AND created_at < ? {device_filter}
                    GROUP BY device_id, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'device_id': row[0],
                        'voltage': round(row[1], 1) if row[1] else None,
                        'current': round(row[2], 3) if row[2] else None,
                        'power': round(row[3], 1) if row[3] else None,
                        'created_at': row[4]
                    })

            # 3. 15-minute averages for 1-7 days
            if hours > 24:
                agg_start = max(start_time, boundary_7d)
                agg_end = boundary_24h

                query = f"""
                    SELECT
                        device_id,
                        AVG(voltage) as avg_voltage,
                        AVG(current) as avg_current,
                        AVG(power) as avg_power,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 15) * 15) ||
                            ':00' as time_bucket
                    FROM plug_logs
                    WHERE created_at >= ? AND created_at < ? {device_filter}
                    GROUP BY device_id, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'device_id': row[0],
                        'voltage': round(row[1], 1) if row[1] else None,
                        'current': round(row[2], 3) if row[2] else None,
                        'power': round(row[3], 1) if row[3] else None,
                        'created_at': row[4]
                    })

            # 4. 30-minute averages for 7-30 days
            if hours > 168:
                agg_start = max(start_time, boundary_30d)
                agg_end = boundary_7d

                query = f"""
                    SELECT
                        device_id,
                        AVG(voltage) as avg_voltage,
                        AVG(current) as avg_current,
                        AVG(power) as avg_power,
                        strftime('%Y-%m-%dT%H:', created_at) ||
                            printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 30) * 30) ||
                            ':00' as time_bucket
                    FROM plug_logs
                    WHERE created_at >= ? AND created_at < ? {device_filter}
                    GROUP BY device_id, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'device_id': row[0],
                        'voltage': round(row[1], 1) if row[1] else None,
                        'current': round(row[2], 3) if row[2] else None,
                        'power': round(row[3], 1) if row[3] else None,
                        'created_at': row[4]
                    })

            # 5. Hourly averages for >30 days
            if hours > 720:
                agg_start = start_time
                agg_end = boundary_30d

                query = f"""
                    SELECT
                        device_id,
                        AVG(voltage) as avg_voltage,
                        AVG(current) as avg_current,
                        AVG(power) as avg_power,
                        strftime('%Y-%m-%dT%H:00:00', created_at) as time_bucket
                    FROM plug_logs
                    WHERE created_at >= ? AND created_at < ? {device_filter}
                    GROUP BY device_id, time_bucket
                    ORDER BY time_bucket DESC
                """
                params = [agg_start, agg_end] + base_params
                cursor.execute(query, params)

                for row in cursor.fetchall():
                    results.append({
                        'device_id': row[0],
                        'voltage': round(row[1], 1) if row[1] else None,
                        'current': round(row[2], 3) if row[2] else None,
                        'power': round(row[3], 1) if row[3] else None,
                        'created_at': row[4]
                    })

        # Sort all results by created_at descending
        results.sort(key=lambda x: x['created_at'], reverse=True)
        return results

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

            # Delete synced plug logs
            cursor.execute(
                """
                DELETE FROM plug_logs
                WHERE created_at < ? AND synced_at IS NOT NULL
                """,
                (cutoff,)
            )
            deleted['plug_logs'] = cursor.rowcount

        # Optimize database after deletion
        self._get_connection().execute('VACUUM')

        logger.info(f"Cleanup completed: {deleted}")
        return deleted

    # =========================================================================
    # Curve Presets
    # =========================================================================

    def insert_curve_preset(self, preset: CurvePreset) -> Optional[int]:
        """
        Insert a new curve preset.

        Returns:
            The ID of the inserted preset, or None if failed
        """
        import json
        with self._cursor() as cursor:
            try:
                cursor.execute(
                    """
                    INSERT INTO curve_presets (name, description, curves_json, is_system, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (preset.name, preset.description, json.dumps(preset.curves_json),
                     int(preset.is_system), preset.created_at)
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                logger.error(f"Preset with name '{preset.name}' already exists")
                return None

    def get_all_curve_presets(self) -> List[CurvePreset]:
        """Get all curve presets."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, curves_json, is_system, created_at
                FROM curve_presets
                ORDER BY is_system DESC, name ASC
                """
            )
            return [CurvePreset.from_row(row) for row in cursor.fetchall()]

    def get_curve_preset(self, preset_id: int) -> Optional[CurvePreset]:
        """Get a specific curve preset by ID."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, curves_json, is_system, created_at
                FROM curve_presets
                WHERE id = ?
                """,
                (preset_id,)
            )
            row = cursor.fetchone()
            return CurvePreset.from_row(row) if row else None

    def get_curve_preset_by_name(self, name: str) -> Optional[CurvePreset]:
        """Get a specific curve preset by name."""
        with self._cursor() as cursor:
            cursor.execute(
                """
                SELECT id, name, description, curves_json, is_system, created_at
                FROM curve_presets
                WHERE name = ?
                """,
                (name,)
            )
            row = cursor.fetchone()
            return CurvePreset.from_row(row) if row else None

    def update_curve_preset(self, preset_id: int, name: str = None, description: str = None) -> bool:
        """
        Update a curve preset (rename or update description).

        Args:
            preset_id: ID of preset to update
            name: New name (optional)
            description: New description (optional)

        Returns:
            True if successful, False otherwise
        """
        preset = self.get_curve_preset(preset_id)
        if not preset:
            return False

        # Check if it's a system preset - only allow description changes
        if preset.is_system and name is not None and name != preset.name:
            logger.warning(f"Cannot rename system preset: {preset.name}")
            return False

        updates = []
        params = []

        if name is not None:
            updates.append("name = ?")
            params.append(name)

        if description is not None:
            updates.append("description = ?")
            params.append(description)

        if not updates:
            return True  # Nothing to update

        params.append(preset_id)

        with self._cursor() as cursor:
            try:
                cursor.execute(
                    f"""
                    UPDATE curve_presets
                    SET {', '.join(updates)}
                    WHERE id = ?
                    """,
                    params
                )
                return cursor.rowcount > 0
            except sqlite3.IntegrityError:
                logger.error(f"Preset with name '{name}' already exists")
                return False

    def delete_curve_preset(self, preset_id: int) -> bool:
        """
        Delete a curve preset.

        System presets (is_system=1) cannot be deleted.

        Returns:
            True if deleted, False otherwise
        """
        preset = self.get_curve_preset(preset_id)
        if not preset:
            return False

        if preset.is_system:
            logger.warning(f"Cannot delete system preset: {preset.name}")
            return False

        with self._cursor() as cursor:
            cursor.execute(
                "DELETE FROM curve_presets WHERE id = ? AND is_system = 0",
                (preset_id,)
            )
            return cursor.rowcount > 0

    def initialize_default_presets(self) -> None:
        """
        Initialize default/system curve presets if they don't exist.

        Creates 3 built-in presets: Keimung (Germination), Wachstum (Growth), Bluete (Flowering)
        """
        # Check if presets already exist
        existing = self.get_all_curve_presets()
        if any(p.is_system for p in existing):
            logger.debug("System presets already exist")
            return

        # System preset definitions with realistic lighting curves
        presets = [
            {
                "name": "Keimung",
                "description": "Optimale Beleuchtung fuer Keimung und Samlinge - sanftes Licht, kurzer Tag",
                "curves_json": {
                    "1": [  # Far Red - minimal
                        {"time": "08:00", "intensity": 0},
                        {"time": "08:30", "intensity": 10},
                        {"time": "18:00", "intensity": 10},
                        {"time": "18:30", "intensity": 0}
                    ],
                    "2": [  # Warm White - low intensity
                        {"time": "08:00", "intensity": 0},
                        {"time": "09:00", "intensity": 30},
                        {"time": "17:00", "intensity": 30},
                        {"time": "18:00", "intensity": 0}
                    ],
                    "3": [  # Cool White - main light source
                        {"time": "08:00", "intensity": 0},
                        {"time": "09:00", "intensity": 40},
                        {"time": "17:00", "intensity": 40},
                        {"time": "18:00", "intensity": 0}
                    ],
                    "4": [  # UV - off
                        {"time": "00:00", "intensity": 0},
                        {"time": "12:00", "intensity": 0}
                    ]
                },
                "is_system": True
            },
            {
                "name": "Wachstum",
                "description": "Vegetative Wachstumsphase - hohe Lichtintensitaet, langer Tag (18h)",
                "curves_json": {
                    "1": [  # Far Red - sunrise/sunset effect
                        {"time": "05:45", "intensity": 0},
                        {"time": "06:15", "intensity": 50},
                        {"time": "06:30", "intensity": 100},
                        {"time": "22:30", "intensity": 100},
                        {"time": "23:00", "intensity": 50},
                        {"time": "23:30", "intensity": 0}
                    ],
                    "2": [  # Warm White - full power
                        {"time": "06:00", "intensity": 0},
                        {"time": "07:00", "intensity": 80},
                        {"time": "22:00", "intensity": 80},
                        {"time": "23:00", "intensity": 0}
                    ],
                    "3": [  # Cool White - full power (blue promotes vegetative growth)
                        {"time": "06:00", "intensity": 0},
                        {"time": "07:00", "intensity": 100},
                        {"time": "22:00", "intensity": 100},
                        {"time": "23:00", "intensity": 0}
                    ],
                    "4": [  # UV - slight exposure midday
                        {"time": "10:00", "intensity": 0},
                        {"time": "11:00", "intensity": 15},
                        {"time": "15:00", "intensity": 15},
                        {"time": "16:00", "intensity": 0}
                    ]
                },
                "is_system": True
            },
            {
                "name": "Bluete",
                "description": "Bluete- und Fruchtphase - warmes Spektrum, kurzer Tag (12h)",
                "curves_json": {
                    "1": [  # Far Red - high for flowering
                        {"time": "07:00", "intensity": 0},
                        {"time": "08:00", "intensity": 100},
                        {"time": "18:00", "intensity": 100},
                        {"time": "19:00", "intensity": 0}
                    ],
                    "2": [  # Warm White - high (red spectrum promotes flowering)
                        {"time": "07:00", "intensity": 0},
                        {"time": "08:00", "intensity": 100},
                        {"time": "18:00", "intensity": 100},
                        {"time": "19:00", "intensity": 0}
                    ],
                    "3": [  # Cool White - reduced
                        {"time": "07:00", "intensity": 0},
                        {"time": "08:00", "intensity": 50},
                        {"time": "18:00", "intensity": 50},
                        {"time": "19:00", "intensity": 0}
                    ],
                    "4": [  # UV - brief exposure for terpene/resin production
                        {"time": "11:00", "intensity": 0},
                        {"time": "12:00", "intensity": 20},
                        {"time": "14:00", "intensity": 20},
                        {"time": "15:00", "intensity": 0}
                    ]
                },
                "is_system": True
            }
        ]

        for preset_data in presets:
            preset = CurvePreset(
                name=preset_data["name"],
                description=preset_data["description"],
                curves_json=preset_data["curves_json"],
                is_system=preset_data["is_system"]
            )
            result = self.insert_curve_preset(preset)
            if result:
                logger.info(f"Created system preset: {preset.name}")
            else:
                logger.warning(f"Failed to create system preset: {preset.name}")


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
