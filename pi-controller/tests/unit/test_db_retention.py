import os
import tempfile
import time
from datetime import datetime, timedelta
import pytest

from grow_pi.database.db import Database
from grow_pi.database.models import SensorReading, LampStateLog, SystemEvent, SensorType


def test_database_retention_pruning():
    """Test that cleanup_old_data purges records older than retention_days."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db = Database(db_path)
        db.initialize()

        # Insert old readings (10 days old)
        old_time = (datetime.now() - timedelta(days=10)).isoformat()
        old_reading = SensorReading(
            sensor_type=SensorType.TEMPERATURE,
            value=24.5,
            unit="°C",
            created_at=old_time
        )
        db.insert_sensor_reading(old_reading)

        old_lamp = LampStateLog(
            channel=1,
            name="Far Red",
            intensity=50,
            source="periodic",
            created_at=old_time
        )
        db.insert_lamp_state(old_lamp)

        old_event = SystemEvent(
            event_type="test_event",
            severity="info",
            message="old event",
            created_at=old_time
        )
        db.insert_system_event(old_event)

        # Insert recent readings (1 day old)
        recent_time = (datetime.now() - timedelta(days=1)).isoformat()
        recent_reading = SensorReading(
            sensor_type=SensorType.TEMPERATURE,
            value=25.0,
            unit="°C",
            created_at=recent_time
        )
        db.insert_sensor_reading(recent_reading)

        recent_lamp = LampStateLog(
            channel=1,
            name="Far Red",
            intensity=75,
            source="periodic",
            created_at=recent_time
        )
        db.insert_lamp_state(recent_lamp)

        # Execute retention cleanup for 7 days
        deleted = db.cleanup_old_data(retention_days=7, include_unsynced=True)

        assert deleted["sensor_readings"] == 1
        assert deleted["lamp_state_log"] == 1
        assert deleted["system_events"] == 1

        # Verify recent records remain
        readings = db.get_sensor_readings(SensorType.TEMPERATURE, hours=48)
        assert len(readings) == 1
        assert readings[0].value == 25.0

        lamp_logs = db.get_lamp_state_log(channel=1, hours=48)
        assert len(lamp_logs) == 1
        assert lamp_logs[0].intensity == 75

        # Verify vacuum runs without error
        assert db.vacuum() is True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)


def test_lamp_state_deduplication():
    """Test should_log_lamp_state heartbeat and change detection."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        db = Database(db_path)
        db.initialize()

        # Initial log should always return True
        assert db.should_log_lamp_state(channel=1, intensity=50, dedupe_seconds=900) is True

        # Insert a log
        db.insert_lamp_state(LampStateLog(channel=1, name="Far Red", intensity=50, source="periodic"))

        # Same intensity within dedupe window should return False
        assert db.should_log_lamp_state(channel=1, intensity=50, dedupe_seconds=900) is False

        # Changed intensity should return True
        assert db.should_log_lamp_state(channel=1, intensity=60, dedupe_seconds=900) is True

    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
