"""
GrowPi DataLogger Service

Hintergrund-Service der Sensor- und Lampen-Daten sammelt und in SQLite speichert.
Läuft als separater Thread parallel zur Web-API.
"""

import logging
import threading
import time
import json
from datetime import datetime
from typing import Optional, Dict, Callable, Any, List

from .db import Database, get_database
from .models import SensorReading, LampStateLog, SystemEvent, SensorType, SENSOR_UNITS, PlugLog
from ..lamps.smart_plug_controller import SmartPlugController

logger = logging.getLogger(__name__)


class DataLogger:
    """
    Data Logger Service.

    Sammelt periodisch:
    - Sensor-Messwerte (DHT22: Temperatur + Luftfeuchtigkeit)
    - Lampen-Zustände (alle 4 PWM-Kanäle)

    Usage:
        logger = DataLogger(db)
        logger.set_sensor_reader(read_dht22)
        logger.set_lamp_reader(get_lamp_states)
        logger.start()
        ...
        logger.stop()
    """

    def __init__(
        self,
        db: Optional[Database] = None,
        sensor_interval: int = 120,
        lamp_interval: int = 120,
        dedupe_seconds: int = 5
    ):
        """
        Initialize DataLogger.

        Args:
            db: Database instance (uses global if None)
            sensor_interval: Seconds between sensor readings
            lamp_interval: Seconds between lamp state logs
            dedupe_seconds: Min seconds between identical lamp logs
        """
        self.db = db or get_database()
        self.sensor_interval = sensor_interval
        self.sensor_interval = sensor_interval
        self.lamp_interval = lamp_interval
        self.plug_interval = 60  # Default 60s for plugs
        self.dedupe_seconds = dedupe_seconds

        self.plug_controller = SmartPlugController()

        # Callbacks for reading data
        self._sensor_reader: Optional[Callable[[], tuple]] = None
        self._lamp_reader: Optional[Callable[[], Dict[int, Dict[str, Any]]]] = None

        # Thread control
        self._running = False
        self._stop_event = threading.Event()  # CPU-effizientes Warten
        self._sensor_thread: Optional[threading.Thread] = None
        self._lamp_thread: Optional[threading.Thread] = None
        self._plug_thread: Optional[threading.Thread] = None

        # Last logged values (for change detection)
        self._last_lamp_states: Dict[int, int] = {}

    def set_sensor_reader(self, reader: Callable[[], tuple]) -> None:
        """
        Set the sensor reader callback.

        Callback should return (temperature, humidity) tuple.
        Can return (None, None) on read error.
        """
        self._sensor_reader = reader

    def set_lamp_reader(self, reader: Callable[[], Dict[int, Dict[str, Any]]]) -> None:
        """
        Set the lamp state reader callback.

        Callback should return dict like:
        {
            1: {'name': 'Far Red', 'intensity': 50},
            2: {'name': 'Warm White', 'intensity': 60},
            ...
        }
        """
        self._lamp_reader = reader

    def start(self) -> None:
        """Start the data logging threads."""
        if self._running:
            logger.warning("DataLogger already running")
            return

        self._running = True

        # Log service start
        self.log_event(
            'service_start',
            'info',
            'DataLogger service started',
            {'sensor_interval': self.sensor_interval, 'lamp_interval': self.lamp_interval}
        )

        # Start sensor logging thread
        if self._sensor_reader:
            self._sensor_thread = threading.Thread(
                target=self._sensor_loop,
                name="DataLogger-Sensors",
                daemon=True
            )
            self._sensor_thread.start()
            logger.info(f"Sensor logging started (interval: {self.sensor_interval}s)")

        # Start lamp logging thread
        if self._lamp_reader:
            self._lamp_thread = threading.Thread(
                target=self._lamp_loop,
                name="DataLogger-Lamps",
                daemon=True
            )
            self._lamp_thread.start()
            logger.info(f"Lamp logging started (interval: {self.lamp_interval}s)")

        # Start plug logging thread
        self._plug_thread = threading.Thread(
            target=self._plug_loop,
            name="DataLogger-Plugs",
            daemon=True
        )
        self._plug_thread.start()
        logger.info(f"Plug logging started (interval: {self.plug_interval}s)")

    def stop(self) -> None:
        """Stop the data logging threads."""
        if not self._running:
            return

        logger.info("Stopping DataLogger...")
        self._running = False
        self._stop_event.set()  # Weckt alle wartenden Threads sofort auf

        # Log service stop
        self.log_event('service_stop', 'info', 'DataLogger service stopped')

        # Wait for threads to finish
        if self._sensor_thread and self._sensor_thread.is_alive():
            self._sensor_thread.join(timeout=5)
        if self._lamp_thread and self._lamp_thread.is_alive():
            self._lamp_thread.join(timeout=5)
        if self._plug_thread and self._plug_thread.is_alive():
            self._plug_thread.join(timeout=5)

        logger.info("DataLogger stopped")

    def _sensor_loop(self) -> None:
        """Background loop for sensor logging."""
        while self._running:
            try:
                self._log_sensors()
            except Exception as e:
                logger.error(f"Sensor logging error: {e}")
                self.log_event('sensor_error', 'error', str(e))

            # CPU-effizientes Warten mit Event (statt 120x time.sleep(1))
            self._stop_event.wait(timeout=self.sensor_interval)

    def _lamp_loop(self) -> None:
        """Background loop for lamp state logging."""
        while self._running:
            try:
                self._log_lamps(source='periodic')
            except Exception as e:
                logger.error(f"Lamp logging error: {e}")
                self.log_event('pwm_error', 'error', str(e))

            # CPU-effizientes Warten mit Event (statt 120x time.sleep(1))
            self._stop_event.wait(timeout=self.lamp_interval)

    def _plug_loop(self) -> None:
        """Background loop for plug logging."""
        while self._running:
            try:
                self._log_plugs()
            except Exception as e:
                logger.error(f"Plug logging error: {e}")
                self.log_event('plug_error', 'error', str(e))

            # CPU-effizientes Warten mit Event (statt 60x time.sleep(1))
            self._stop_event.wait(timeout=self.plug_interval)

    def _log_sensors(self) -> None:
        """Read and log sensor values."""
        if not self._sensor_reader:
            return

        temp, humidity = self._sensor_reader()

        if temp is not None:
            reading = SensorReading(
                sensor_type=SensorType.TEMPERATURE,
                value=temp,
                unit=SENSOR_UNITS[SensorType.TEMPERATURE]
            )
            self.db.insert_sensor_reading(reading)
            logger.debug(f"Logged temperature: {temp}°C")

        if humidity is not None:
            reading = SensorReading(
                sensor_type=SensorType.HUMIDITY,
                value=humidity,
                unit=SENSOR_UNITS[SensorType.HUMIDITY]
            )
            self.db.insert_sensor_reading(reading)
            logger.debug(f"Logged humidity: {humidity}%")

    def _log_lamps(self, source: str = 'periodic') -> None:
        """Read and log lamp states."""
        if not self._lamp_reader:
            return

        states = self._lamp_reader()

        for channel, info in states.items():
            intensity = info.get('intensity', 0)
            name = info.get('name', f'Channel {channel}')

            # Check if we should log (deduplication)
            if source == 'periodic':
                if not self.db.should_log_lamp_state(channel, intensity, self.dedupe_seconds):
                    continue

            state = LampStateLog(
                channel=channel,
                name=name,
                intensity=intensity,
                source=source
            )
            self.db.insert_lamp_state(state)
            logger.debug(f"Logged lamp {channel} ({name}): {intensity}%")

    def _log_plugs(self) -> None:
        """Read and log plug values."""
        plugs = self.plug_controller.get_plugs()
        for plug in plugs:
            device_id = plug.get('device_id')
            if not device_id:
                continue
                
            status = self.plug_controller.get_status(device_id)
            if status:
                log = PlugLog(
                    device_id=device_id,
                    voltage=status.get('voltage', 0),
                    current=status.get('current', 0),
                    power=status.get('power', 0)
                )
                self.db.insert_plug_log(log)
                logger.debug(f"Logged plug {plug.get('name')}: {log.power}W")

    def log_lamp_change(
        self,
        channel: int,
        name: str,
        intensity: int,
        source: str,
        curve_time: Optional[str] = None
    ) -> None:
        """
        Log a lamp state change (called from PWM controller or API).

        Use this method when intensity changes, not just periodic logging.
        """
        # Check deduplication
        if not self.db.should_log_lamp_state(channel, intensity, self.dedupe_seconds):
            return

        state = LampStateLog(
            channel=channel,
            name=name,
            intensity=intensity,
            source=source,
            curve_time=curve_time
        )
        self.db.insert_lamp_state(state)
        logger.info(f"Lamp change logged: {name} (ch{channel}) -> {intensity}% [{source}]")

    def log_startup_states(self, states: Dict[int, Dict[str, Any]]) -> None:
        """Log initial lamp states at service startup."""
        for channel, info in states.items():
            state = LampStateLog(
                channel=channel,
                name=info.get('name', f'Channel {channel}'),
                intensity=info.get('intensity', 0),
                source='startup'
            )
            self.db.insert_lamp_state(state)
        logger.info(f"Logged startup states for {len(states)} channels")

    def log_shutdown_states(self, channels: List[int], names: Dict[int, str]) -> None:
        """Log lamp states at service shutdown (all off)."""
        for channel in channels:
            state = LampStateLog(
                channel=channel,
                name=names.get(channel, f'Channel {channel}'),
                intensity=0,
                source='shutdown'
            )
            self.db.insert_lamp_state(state)
        logger.info(f"Logged shutdown states for {len(channels)} channels")

    def log_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: Optional[Dict] = None
    ) -> None:
        """Log a system event."""
        try:
            event = SystemEvent(
                event_type=event_type,
                severity=severity,
                message=message,
                details=json.dumps(details) if details else None
            )
            self.db.insert_system_event(event)
        except Exception as e:
            logger.error(f"Failed to log event: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Get logger status and statistics."""
        stats = self.db.get_stats()
        return {
            'running': self._running,
            'sensor_interval': self.sensor_interval,
            'lamp_interval': self.lamp_interval,
            'has_sensor_reader': self._sensor_reader is not None,
            'has_lamp_reader': self._lamp_reader is not None,
            'database': stats
        }


# Global logger instance
_logger_instance: Optional[DataLogger] = None
_logger_lock = threading.Lock()


def get_logger(
    db: Optional[Database] = None,
    sensor_interval: int = 60,
    lamp_interval: int = 60
) -> DataLogger:
    """
    Get or create global DataLogger instance.

    Thread-safe singleton pattern.
    """
    global _logger_instance

    if _logger_instance is None:
        with _logger_lock:
            if _logger_instance is None:
                _logger_instance = DataLogger(
                    db=db,
                    sensor_interval=sensor_interval,
                    lamp_interval=lamp_interval
                )

    return _logger_instance
