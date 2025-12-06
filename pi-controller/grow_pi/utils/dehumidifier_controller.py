"""
Dehumidifier Controller with Hysteresis Logic

Controls a smart plug based on humidity sensor readings.
Implements configurable hysteresis to prevent rapid on/off cycling.
"""

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional, Callable

from .tuya_cloud import get_tuya_service, TuyaCloudService

logger = logging.getLogger(__name__)

# Config file location
CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'config')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'room_config.json')


@dataclass
class DehumidifierConfig:
    """Configuration for dehumidifier control."""
    enabled: bool = True
    target: float = 60.0  # Target humidity %
    threshold_high: float = 65.0  # Turn ON above this
    threshold_low: float = 55.0  # Turn OFF below this
    device_id: str = "bfc705014c6241667avzn8"  # Entfeuchter
    min_run_time: int = 60  # Minimum seconds to run before turning off
    min_off_time: int = 60  # Minimum seconds off before turning on again

    # Zeitfenster-Override (präventiv vor Lampen-Aus)
    schedule_enabled: bool = False  # Zeitfenster aktiviert?
    schedule_start_time: str = "19:45"  # Start-Zeit (HH:MM)
    schedule_duration_minutes: int = 30  # Dauer in Minuten


class DehumidifierController:
    """
    Controls dehumidifier based on humidity with hysteresis.

    Hysteresis Logic:
    - Turn ON when humidity > threshold_high
    - Turn OFF when humidity < threshold_low
    - This prevents rapid cycling around the target value

    Example:
        target=60%, high=65%, low=55%
        - At 66% humidity -> turns ON
        - Stays ON until humidity drops to 54%
        - Then stays OFF until humidity rises to 66% again
    """

    def __init__(self, humidity_reader: Optional[Callable[[], Optional[float]]] = None):
        """
        Initialize controller.

        Args:
            humidity_reader: Callable that returns current humidity or None
        """
        self.config = DehumidifierConfig()
        self._tuya: Optional[TuyaCloudService] = None
        self._humidity_reader = humidity_reader
        self._is_on = False
        self._last_switch_time = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        # Load saved config
        self._load_config()

        # Initialize Tuya service
        self._tuya = get_tuya_service()
        if self._tuya and self._tuya.is_available:
            logger.info("DehumidifierController initialized with Tuya Cloud")
            # Sync actual device state on startup
            self._sync_device_state()
        else:
            logger.warning("DehumidifierController: Tuya Cloud not available")

    def _sync_device_state(self):
        """Sync internal state with actual device state from Tuya Cloud."""
        try:
            if not self._tuya or not self._tuya.is_available:
                return

            status = self._tuya.get_device_status(self.config.device_id)
            if status and 'switch' in status:
                self._is_on = status['switch']
                logger.info(f"Dehumidifier state synced from cloud: {'ON' if self._is_on else 'OFF'}")
            else:
                logger.warning("Could not get device status from Tuya Cloud")
        except Exception as e:
            logger.error(f"Error syncing device state: {e}")

    def _load_config(self):
        """Load config from file."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)
                    if 'dehumidifier' in data:
                        cfg = data['dehumidifier']
                        self.config = DehumidifierConfig(
                            enabled=cfg.get('enabled', True),
                            target=cfg.get('target', 60.0),
                            threshold_high=cfg.get('threshold_high', 65.0),
                            threshold_low=cfg.get('threshold_low', 55.0),
                            device_id=cfg.get('device_id', self.config.device_id),
                            min_run_time=cfg.get('min_run_time', 60),
                            min_off_time=cfg.get('min_off_time', 60),
                            schedule_enabled=cfg.get('schedule_enabled', False),
                            schedule_start_time=cfg.get('schedule_start_time', '19:45'),
                            schedule_duration_minutes=cfg.get('schedule_duration_minutes', 30)
                        )
                        logger.info(f"Loaded dehumidifier config: target={self.config.target}%, schedule={'ON' if self.config.schedule_enabled else 'OFF'}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def _save_config(self):
        """Save config to file."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)

            data = {}
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    data = json.load(f)

            data['dehumidifier'] = asdict(self.config)

            with open(CONFIG_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info("Saved dehumidifier config")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    def get_config(self) -> dict:
        """Get current config as dict."""
        return asdict(self.config)

    def update_config(
        self,
        enabled: Optional[bool] = None,
        target: Optional[float] = None,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        min_run_time: Optional[int] = None,
        min_off_time: Optional[int] = None,
        schedule_enabled: Optional[bool] = None,
        schedule_start_time: Optional[str] = None,
        schedule_duration_minutes: Optional[int] = None
    ) -> dict:
        """
        Update configuration.

        Args:
            enabled: Enable/disable automatic control
            target: Target humidity percentage
            threshold_high: Turn ON threshold
            threshold_low: Turn OFF threshold
            min_run_time: Minimum run time in seconds
            min_off_time: Minimum off time in seconds
            schedule_enabled: Enable/disable schedule window
            schedule_start_time: Schedule start time (HH:MM)
            schedule_duration_minutes: Schedule duration in minutes

        Returns:
            Updated config dict
        """
        with self._lock:
            if enabled is not None:
                self.config.enabled = enabled
            if target is not None:
                self.config.target = float(target)
            if threshold_high is not None:
                self.config.threshold_high = float(threshold_high)
            if threshold_low is not None:
                self.config.threshold_low = float(threshold_low)
            if min_run_time is not None:
                self.config.min_run_time = int(min_run_time)
            if min_off_time is not None:
                self.config.min_off_time = int(min_off_time)
            if schedule_enabled is not None:
                self.config.schedule_enabled = schedule_enabled
            if schedule_start_time is not None:
                self.config.schedule_start_time = schedule_start_time
            if schedule_duration_minutes is not None:
                self.config.schedule_duration_minutes = int(schedule_duration_minutes)

            self._save_config()
            return self.get_config()

    def set_humidity_reader(self, reader: Callable[[], Optional[float]]):
        """Set the humidity reader function."""
        self._humidity_reader = reader

    def get_current_humidity(self) -> Optional[float]:
        """Get current humidity from reader."""
        if self._humidity_reader:
            try:
                return self._humidity_reader()
            except Exception as e:
                logger.error(f"Error reading humidity: {e}")
        return None

    def _is_in_schedule_window(self) -> bool:
        """
        Check if current time is within the scheduled time window.

        Returns:
            True if schedule is enabled AND current time is within window
        """
        if not self.config.schedule_enabled:
            return False

        from datetime import datetime, time as dt_time, timedelta

        now = datetime.now()
        current_time = now.time()

        # Parse start time
        try:
            start_hour, start_minute = map(int, self.config.schedule_start_time.split(':'))
            start_time = dt_time(start_hour, start_minute)
        except Exception as e:
            logger.error(f"Invalid schedule_start_time format: {e}")
            return False

        # Calculate end time
        start_datetime = datetime.combine(now.date(), start_time)
        end_datetime = start_datetime + timedelta(minutes=self.config.schedule_duration_minutes)
        end_time = end_datetime.time()

        # Handle midnight wraparound
        if end_datetime.date() > now.date():
            # Window crosses midnight
            return current_time >= start_time or current_time <= end_time
        else:
            # Normal window within same day
            return start_time <= current_time <= end_time

    def switch_on(self) -> bool:
        """Manually turn dehumidifier ON."""
        if not self._tuya or not self._tuya.is_available:
            logger.warning("Cannot switch: Tuya not available")
            return False

        success = self._tuya.switch_on(self.config.device_id)
        if success:
            self._is_on = True
            self._last_switch_time = time.time()
        return success

    def switch_off(self) -> bool:
        """Manually turn dehumidifier OFF."""
        if not self._tuya or not self._tuya.is_available:
            logger.warning("Cannot switch: Tuya not available")
            return False

        success = self._tuya.switch_off(self.config.device_id)
        if success:
            self._is_on = False
            self._last_switch_time = time.time()
        return success

    def get_status(self) -> dict:
        """
        Get current status.

        Returns:
            Dict with is_on, humidity, config, in_schedule, etc.
        """
        humidity = self.get_current_humidity()
        in_schedule = self._is_in_schedule_window()

        return {
            'is_on': self._is_on,
            'humidity': humidity,
            'enabled': self.config.enabled,
            'config': self.get_config(),
            'tuya_available': self._tuya.is_available if self._tuya else False,
            'running': self._running,
            'in_schedule_window': in_schedule  # Neuer Status für UI
        }

    def check_and_control(self) -> Optional[bool]:
        """
        Check humidity and control dehumidifier.

        Logic:
        1. If in schedule window -> ALWAYS ON (Override)
        2. If not in schedule window -> Normal hysteresis control

        Returns:
            True if turned ON, False if turned OFF, None if no change
        """
        if not self.config.enabled:
            return None

        if not self._tuya or not self._tuya.is_available:
            return None

        humidity = self.get_current_humidity()
        if humidity is None:
            logger.warning("No humidity reading available")
            return None

        now = time.time()
        time_since_switch = now - self._last_switch_time
        in_schedule = self._is_in_schedule_window()

        with self._lock:
            # PRIORITY 1: Schedule Window Override
            if in_schedule:
                # During schedule window, always turn ON (ignoring hysteresis)
                if not self._is_on:
                    logger.info(f"Schedule active [{self.config.schedule_start_time} for {self.config.schedule_duration_minutes}min] - turning ON")
                    if self.switch_on():
                        return True
                # If already ON during schedule, keep it ON
                return None

            # PRIORITY 2: Normal Hysteresis Control (outside schedule window)
            # Check if we should turn ON
            if not self._is_on and humidity > self.config.threshold_high:
                # Respect minimum off time
                if time_since_switch >= self.config.min_off_time:
                    logger.info(f"Humidity {humidity}% > {self.config.threshold_high}% - turning ON")
                    if self.switch_on():
                        return True

            # Check if we should turn OFF
            elif self._is_on and humidity < self.config.threshold_low:
                # Respect minimum run time
                if time_since_switch >= self.config.min_run_time:
                    logger.info(f"Humidity {humidity}% < {self.config.threshold_low}% - turning OFF")
                    if self.switch_off():
                        return False

        return None

    def start(self, check_interval: int = 30):
        """
        Start automatic control loop.

        Args:
            check_interval: Seconds between checks
        """
        if self._running:
            return

        self._running = True

        def control_loop():
            while self._running:
                try:
                    self.check_and_control()
                except Exception as e:
                    logger.error(f"Control loop error: {e}")
                time.sleep(check_interval)

        self._thread = threading.Thread(target=control_loop, daemon=True)
        self._thread.start()
        logger.info(f"DehumidifierController started (interval: {check_interval}s)")

    def stop(self):
        """Stop automatic control loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("DehumidifierController stopped")


# Singleton instance
_controller: Optional[DehumidifierController] = None


def get_dehumidifier_controller() -> DehumidifierController:
    """Get or create singleton DehumidifierController."""
    global _controller

    if _controller is None:
        _controller = DehumidifierController()

    return _controller
