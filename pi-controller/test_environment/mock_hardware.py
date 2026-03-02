"""
Mock Hardware Components for GrowPi Testing
Allows running the controller without Raspberry Pi hardware.
"""

import time
import math
import random
import logging
from typing import Dict, Tuple, Optional, List, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


# ============================================================================
# Mock PWM Controller (Replaces pigpio)
# ============================================================================

class MockPWMController:
    """
    Mock PWM Controller for testing without GPIO hardware.
    Simulates the PWMController interface but stores values in-memory.
    """

    def __init__(self):
        """Initialize mock PWM controller."""
        self._channels: Dict[int, int] = {}  # channel -> intensity (0-100)
        self._initialized = False
        self._frequency = 1000  # Mock frequency
        logger.info("MockPWMController initialized (SIMULATION MODE)")

    def initialize(self, channels: List[Any]) -> None:
        """
        Initialize channels (mock implementation).

        Args:
            channels: List of channel configs (from config.yaml)
        """
        for ch_config in channels:
            channel = ch_config.channel if hasattr(ch_config, 'channel') else ch_config
            self._channels[channel] = 0  # Start at 0%

        self._initialized = True
        logger.info(f"MockPWM initialized {len(self._channels)} channels")

    def set_intensity(self, channel: int, intensity: int) -> None:
        """
        Set lamp intensity (mock - just stores value).

        Args:
            channel: Channel ID (1-4)
            intensity: Intensity 0-100
        """
        if channel not in self._channels:
            self._channels[channel] = 0

        # Validate intensity
        intensity = max(0, min(100, intensity))

        old_value = self._channels[channel]
        self._channels[channel] = intensity

        logger.debug(f"MockPWM: Channel {channel} set to {intensity}% (was {old_value}%)")

    def get_intensity(self, channel: int) -> int:
        """Get current intensity for a channel."""
        return self._channels.get(channel, 0)

    def get_current_state(self) -> Dict[int, int]:
        """Get all channel intensities."""
        return self._channels.copy()

    def cleanup(self) -> None:
        """Cleanup (mock - does nothing)."""
        logger.info("MockPWM cleanup (no-op)")
        self._channels = {}
        self._initialized = False


# Singleton instance
_mock_pwm_instance = None

def get_mock_pwm_controller() -> MockPWMController:
    """Get or create global mock PWM controller instance."""
    global _mock_pwm_instance
    if _mock_pwm_instance is None:
        _mock_pwm_instance = MockPWMController()
    return _mock_pwm_instance


# ============================================================================
# Mock DHT22 Sensor (Replaces adafruit_dht)
# ============================================================================

class MockDHT22:
    """
    Mock DHT22 sensor for testing.
    Generates realistic temperature/humidity data with time-based variation.
    """

    def __init__(
        self,
        base_temp: float = 22.0,
        base_humidity: float = 60.0,
        temp_variation: float = 4.0,
        humidity_variation: float = 10.0
    ):
        """
        Initialize mock sensor.

        Args:
            base_temp: Average temperature (°C)
            base_humidity: Average humidity (%)
            temp_variation: Temperature amplitude (°C)
            humidity_variation: Humidity amplitude (%)
        """
        self.base_temp = base_temp
        self.base_humidity = base_humidity
        self.temp_variation = temp_variation
        self.humidity_variation = humidity_variation

        logger.info("MockDHT22 initialized (SIMULATION MODE)")

    def read(self) -> Tuple[float, float]:
        """
        Read mock sensor values.

        Returns:
            (temperature, humidity) tuple

        Simulates realistic daily variation:
        - Temperature: Higher in afternoon, lower at night
        - Humidity: Inverse correlation with temperature
        - Small random noise
        """
        # Time-based variation (24h cycle)
        now = datetime.now()
        hour = now.hour + now.minute / 60.0

        # Sine wave: peak at 15:00, trough at 03:00
        time_factor = math.sin((hour - 3) * math.pi / 12)

        # Temperature: base + sine variation + noise
        temp = self.base_temp + (self.temp_variation * time_factor)
        temp += random.uniform(-0.5, 0.5)  # Small noise
        temp = round(temp, 1)

        # Humidity: inverse correlation + noise
        humidity = self.base_humidity - (self.humidity_variation * time_factor * 0.3)
        humidity += random.uniform(-2, 2)  # More noise
        humidity = round(max(20.0, min(95.0, humidity)), 1)  # Clamp 20-95%

        logger.debug(f"MockDHT22: temp={temp}°C, humidity={humidity}%")
        return (temp, humidity)

    @property
    def temperature(self) -> float:
        """Get temperature (alternative API)."""
        temp, _ = self.read()
        return temp

    @property
    def humidity(self) -> float:
        """Get humidity (alternative API)."""
        _, humidity = self.read()
        return humidity


# ============================================================================
# Mock Database (Replaces SQLite)
# ============================================================================

@dataclass
class MockSensorReading:
    """Mock sensor reading."""
    id: int
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            'id': self.id,
            'sensor_type': self.sensor_type,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MockLampStateLog:
    """Mock lamp state log."""
    id: int
    channel: int
    name: str
    intensity: int
    source: str
    timestamp: datetime
    curve_time: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            'id': self.id,
            'channel': self.channel,
            'name': self.name,
            'intensity': self.intensity,
            'source': self.source,
            'curve_time': self.curve_time,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class MockSystemEvent:
    """Mock system event."""
    id: int
    event_type: str
    severity: str
    message: str
    details: Optional[str]
    timestamp: datetime

    def to_dict(self) -> dict:
        """Convert to dict for API response."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat()
        }


class MockDatabase:
    """
    In-memory database for testing.
    Replaces SQLite with Python lists.
    """

    def __init__(self):
        """Initialize mock database."""
        self.sensor_readings: List[MockSensorReading] = []
        self.lamp_logs: List[MockLampStateLog] = []
        self.system_events: List[MockSystemEvent] = []
        self.plug_logs: List[dict] = []

        self._sensor_id_counter = 1
        self._lamp_id_counter = 1
        self._event_id_counter = 1

        logger.info("MockDatabase initialized (IN-MEMORY)")

    def insert_sensor_reading(self, reading: Any) -> int:
        """Insert sensor reading."""
        mock_reading = MockSensorReading(
            id=self._sensor_id_counter,
            sensor_type=reading.sensor_type,
            value=reading.value,
            unit=reading.unit,
            timestamp=datetime.now()
        )
        self.sensor_readings.append(mock_reading)
        self._sensor_id_counter += 1
        logger.debug(f"Inserted sensor reading: {reading.sensor_type}={reading.value}")
        return mock_reading.id

    def insert_lamp_state(self, state: Any) -> int:
        """Insert lamp state log."""
        mock_log = MockLampStateLog(
            id=self._lamp_id_counter,
            channel=state.channel,
            name=state.name,
            intensity=state.intensity,
            source=state.source,
            curve_time=getattr(state, 'curve_time', None),
            timestamp=datetime.now()
        )
        self.lamp_logs.append(mock_log)
        self._lamp_id_counter += 1
        logger.debug(f"Inserted lamp log: ch{state.channel}={state.intensity}%")
        return mock_log.id

    def insert_system_event(self, event: Any) -> int:
        """Insert system event."""
        mock_event = MockSystemEvent(
            id=self._event_id_counter,
            event_type=event.event_type,
            severity=event.severity,
            message=event.message,
            details=getattr(event, 'details', None),
            timestamp=datetime.now()
        )
        self.system_events.append(mock_event)
        self._event_id_counter += 1
        logger.debug(f"Inserted event: {event.event_type} - {event.message}")
        return mock_event.id

    def insert_plug_log(self, log: Any) -> int:
        """Insert plug log (stub for compatibility)."""
        self.plug_logs.append(asdict(log) if hasattr(log, '__dataclass_fields__') else log)
        return len(self.plug_logs)

    def get_sensor_readings(
        self,
        sensor_type: Optional[str] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[MockSensorReading]:
        """Get sensor readings with filtering."""
        cutoff = datetime.now() - timedelta(hours=hours)

        filtered = [
            r for r in self.sensor_readings
            if r.timestamp >= cutoff
            and (sensor_type is None or r.sensor_type == sensor_type)
        ]

        # Return newest first
        filtered.sort(key=lambda r: r.timestamp, reverse=True)
        return filtered[:limit]

    def get_lamp_state_log(
        self,
        channel: Optional[int] = None,
        hours: int = 24,
        limit: int = 1000
    ) -> List[MockLampStateLog]:
        """Get lamp state logs with filtering."""
        cutoff = datetime.now() - timedelta(hours=hours)

        filtered = [
            log for log in self.lamp_logs
            if log.timestamp >= cutoff
            and (channel is None or log.channel == channel)
        ]

        filtered.sort(key=lambda log: log.timestamp, reverse=True)
        return filtered[:limit]

    def get_system_events(
        self,
        event_type: Optional[str] = None,
        severity: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[MockSystemEvent]:
        """Get system events with filtering."""
        cutoff = datetime.now() - timedelta(hours=hours)

        filtered = [
            e for e in self.system_events
            if e.timestamp >= cutoff
            and (event_type is None or e.event_type == event_type)
            and (severity is None or e.severity == severity)
        ]

        filtered.sort(key=lambda e: e.timestamp, reverse=True)
        return filtered[:limit]

    def get_plug_logs(self, hours: int = 24, limit: int = 1000) -> List[dict]:
        """Get plug logs (stub)."""
        return self.plug_logs[:limit]

    def should_log_lamp_state(
        self,
        channel: int,
        intensity: int,
        dedupe_seconds: int = 5
    ) -> bool:
        """
        Check if we should log this lamp state (deduplication).

        Returns False if same value was logged recently.
        """
        cutoff = datetime.now() - timedelta(seconds=dedupe_seconds)

        recent = [
            log for log in self.lamp_logs
            if log.channel == channel
            and log.timestamp >= cutoff
        ]

        if not recent:
            return True

        # Don't log if intensity unchanged
        last_log = recent[-1]
        return last_log.intensity != intensity

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            'sensor_readings_count': len(self.sensor_readings),
            'lamp_logs_count': len(self.lamp_logs),
            'system_events_count': len(self.system_events),
            'plug_logs_count': len(self.plug_logs),
            'storage_type': 'in-memory'
        }


# Singleton instance
_mock_db_instance = None

def get_mock_database() -> MockDatabase:
    """Get or create global mock database instance."""
    global _mock_db_instance
    if _mock_db_instance is None:
        _mock_db_instance = MockDatabase()
    return _mock_db_instance


# ============================================================================
# Mock Data Logger (Uses Mock Database)
# ============================================================================

class MockDataLogger:
    """
    Mock DataLogger using in-memory storage.
    Compatible with real DataLogger API.
    """

    def __init__(self, sensor_interval: int = 60, lamp_interval: int = 60):
        """Initialize mock data logger."""
        self.db = get_mock_database()
        self.sensor_interval = sensor_interval
        self.lamp_interval = lamp_interval
        self._running = False
        self._sensor_reader = None
        self._lamp_reader = None

        logger.info("MockDataLogger initialized (IN-MEMORY)")

    def set_sensor_reader(self, reader) -> None:
        """Set sensor reader callback."""
        self._sensor_reader = reader

    def set_lamp_reader(self, reader) -> None:
        """Set lamp reader callback."""
        self._lamp_reader = reader

    def start(self) -> None:
        """Start logging (mock - does nothing)."""
        self._running = True
        logger.info("MockDataLogger started (no background threads)")

    def stop(self) -> None:
        """Stop logging."""
        self._running = False
        logger.info("MockDataLogger stopped")

    def log_lamp_change(self, channel: int, name: str, intensity: int, source: str) -> None:
        """Log a lamp change."""
        from .mock_hardware import MockLampStateLog
        state = type('State', (), {
            'channel': channel,
            'name': name,
            'intensity': intensity,
            'source': source,
            'curve_time': None
        })()
        self.db.insert_lamp_state(state)

    def log_event(self, event_type: str, severity: str, message: str, details: Optional[dict] = None) -> None:
        """Log a system event."""
        import json
        event = type('Event', (), {
            'event_type': event_type,
            'severity': severity,
            'message': message,
            'details': json.dumps(details) if details else None
        })()
        self.db.insert_system_event(event)

    def log_startup_states(self, states: dict) -> None:
        """Log startup states."""
        logger.info(f"MockDataLogger: Logged startup states for {len(states)} channels")

    def log_shutdown_states(self, channels: list, names: dict) -> None:
        """Log shutdown states."""
        logger.info(f"MockDataLogger: Logged shutdown states for {len(channels)} channels")

    def get_status(self) -> dict:
        """Get logger status."""
        return {
            'running': self._running,
            'sensor_interval': self.sensor_interval,
            'lamp_interval': self.lamp_interval,
            'has_sensor_reader': self._sensor_reader is not None,
            'has_lamp_reader': self._lamp_reader is not None,
            'database': self.db.get_stats()
        }


# ============================================================================
# Mock Smart Plug Controller
# ============================================================================

class MockSmartPlugController:
    """Mock smart plug controller for testing."""

    def __init__(self):
        """Initialize mock controller."""
        self._plugs = [
            {
                'device_id': 'mock_plug_1',
                'name': 'Test Plug 1',
                'connection': 'wifi',
                'ip': '<DEVICE_IP>'
            }
        ]
        logger.info("MockSmartPlugController initialized")

    def get_plugs(self) -> List[dict]:
        """Get list of plugs."""
        return self._plugs

    def get_status(self, device_id: str) -> Optional[dict]:
        """Get plug status (mock data)."""
        return {
            'on': True,
            'power': 50.0 + random.uniform(-5, 5),
            'voltage': 230.0 + random.uniform(-2, 2),
            'current': 0.22 + random.uniform(-0.02, 0.02),
            'updated_at': time.time()
        }

    def turn_on(self, device_id: str) -> bool:
        """Turn plug on (mock)."""
        logger.info(f"MockPlug: Turned ON {device_id}")
        return True

    def turn_off(self, device_id: str) -> bool:
        """Turn plug off (mock)."""
        logger.info(f"MockPlug: Turned OFF {device_id}")
        return True
