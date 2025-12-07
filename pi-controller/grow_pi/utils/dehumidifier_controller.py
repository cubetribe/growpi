#!/usr/bin/env python3
"""
Dehumidifier Controller - Automated Humidity Control with Time-Based Scheduling

This controller manages the dehumidifier device with the following priority logic:
1. TIME SCHEDULE (highest priority) - Force ON/OFF during defined time windows
2. HUMIDITY AUTOMATION (fallback) - Control based on humidity thresholds
3. MANUAL MODE - User can override all automation

Key Features:
- Time window scheduling with midnight wrap-around support
- Hysteresis-based humidity control (prevents rapid cycling)
- Minimum run/off time enforcement
- Automatic fallback from time schedule to humidity automation
- Comprehensive logging of all state changes

Version: 6.9.2
Date: 2025-12-07

Bugfix 6.9.1: Status-Desync Fix
- Added _sync_device_status() to synchronize internal state with actual Tuya device
- Modified _ensure_state() to sync before state checks
- Prevents issues when device is manually switched or state drifts

Bugfix 6.9.2: Manual Control Skip-Bug Fix
- MANUAL triggers now ALWAYS send commands, even if internal state appears correct
- Bypasses min_run_time/min_off_time constraints for manual overrides
- Fixes issue where user clicks "ON" but nothing happens due to stale state
"""

import logging
import threading
import time
import sqlite3
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)


class TriggerType(Enum):
    """Types of triggers that can change device state"""
    TIME_SCHEDULE = "time_schedule"
    HUMIDITY_AUTO = "humidity_auto"
    MANUAL = "manual"
    FALLBACK = "fallback"  # When time schedule ends, falls back to humidity


@dataclass
class TimeSchedule:
    """Time schedule for device control"""
    id: int
    device_id: int
    start_time: str  # "HH:MM" format
    end_time: str    # "HH:MM" format
    target_state: str  # "on" or "off"
    enabled: bool

    @classmethod
    def from_row(cls, row: tuple) -> 'TimeSchedule':
        return cls(
            id=row[0],
            device_id=row[1],
            start_time=row[2],
            end_time=row[3],
            target_state=row[4],
            enabled=bool(row[5])
        )


@dataclass
class DehumidifierConfig:
    """Configuration for dehumidifier automation"""
    enabled: bool = True
    target: float = 60.0
    threshold_high: float = 5.0
    threshold_low: float = 5.0
    min_run_time: int = 300  # seconds
    min_off_time: int = 60   # seconds
    time_schedule_enabled: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)


class DehumidifierController:
    """
    Controller for automated dehumidifier management.

    Priority Logic:
        1. TIME SCHEDULE - If current time is within a schedule window, force ON/OFF
        2. HUMIDITY AUTOMATION - If no schedule active, control based on humidity
        3. MANUAL - User can override by disabling automation

    Fallback Behavior:
        When a time schedule ends, the controller does NOT just turn off.
        Instead, it immediately checks the humidity automation logic
        and decides whether to keep the device running or turn it off.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config = DehumidifierConfig()
        self._is_on = False
        self._last_toggle_time: Optional[datetime] = None
        self._last_trigger: Optional[TriggerType] = None
        self._last_trigger_details: Optional[str] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._humidity_reader = None
        self._plug_controller = None
        self._device_id = 1  # Default device ID for dehumidifier
        self._tuya_device_id: Optional[str] = None
        self._db_path = '/opt/grow-pi/data/growpi.db'

        # In-time-window tracking (to detect when window ends)
        self._was_in_time_window = False

        # Load configuration from database
        self._load_config()
        self._load_plug_controller()

        self._initialized = True
        logger.info("DehumidifierController initialized")

    def _load_config(self) -> None:
        """Load configuration from database"""
        try:
            # BUGFIX 2025-12-07: Create database directory and file if they don't exist
            # This ensures migration can always run on fresh installations
            db_dir = os.path.dirname(self._db_path)
            if not os.path.exists(db_dir):
                logger.info(f"Creating database directory: {db_dir}")
                os.makedirs(db_dir, exist_ok=True)

            # Connect to database (creates file if not exists)
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()

            # Check if tables exist - ALWAYS run migration if missing
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='device_automation_config'
            """)
            if not cursor.fetchone():
                logger.info("device_automation_config table not found, running migration...")
                self._run_migration(conn)

            # Load config
            cursor.execute("""
                SELECT enabled, target_value, threshold_high, threshold_low,
                       min_run_time, min_off_time, time_schedule_enabled
                FROM device_automation_config
                WHERE device_id = ?
            """, (self._device_id,))
            row = cursor.fetchone()

            if row:
                self._config = DehumidifierConfig(
                    enabled=bool(row[0]),
                    target=row[1] or 60.0,
                    threshold_high=row[2] or 5.0,
                    threshold_low=row[3] or 5.0,
                    min_run_time=row[4] or 300,
                    min_off_time=row[5] or 60,
                    time_schedule_enabled=bool(row[6])
                )
                logger.info(f"Loaded config: {self._config}")

            # Load Tuya device ID
            cursor.execute("""
                SELECT tuya_device_id FROM switchable_devices WHERE id = ?
            """, (self._device_id,))
            row = cursor.fetchone()
            if row and row[0]:
                self._tuya_device_id = row[0]

            conn.close()

        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def _run_migration(self, conn: sqlite3.Connection) -> None:
        """Run database migration"""
        try:
            migration_path = os.path.join(
                os.path.dirname(__file__),
                '..', 'database', 'migrations', '20251206_device_time_schedules.sql'
            )
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    sql = f.read()
                conn.executescript(sql)
                conn.commit()
                logger.info("Migration completed successfully")
            else:
                logger.warning(f"Migration file not found: {migration_path}")
        except Exception as e:
            logger.error(f"Migration error: {e}")

    def _load_plug_controller(self) -> None:
        """Load Tuya plug controller"""
        try:
            from ..lamps.smart_plug_controller import SmartPlugController
            self._plug_controller = SmartPlugController()
            logger.info("SmartPlugController loaded")
        except ImportError as e:
            logger.warning(f"SmartPlugController not available: {e}")

    def set_humidity_reader(self, reader_func) -> None:
        """Set the humidity reader function"""
        self._humidity_reader = reader_func

    def get_humidity(self) -> Optional[float]:
        """Get current humidity reading"""
        if self._humidity_reader:
            try:
                result = self._humidity_reader()
                if isinstance(result, tuple):
                    return result[1]  # (temp, humidity)
                return result
            except Exception as e:
                logger.error(f"Error reading humidity: {e}")
        return None

    # =========================================================================
    # Time Schedule Logic
    # =========================================================================

    def get_time_schedules(self) -> List[TimeSchedule]:
        """Get all time schedules for this device"""
        schedules = []
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, device_id, start_time, end_time, target_state, enabled
                FROM device_time_schedules
                WHERE device_id = ?
                ORDER BY start_time
            """, (self._device_id,))
            schedules = [TimeSchedule.from_row(row) for row in cursor.fetchall()]
            conn.close()
        except Exception as e:
            logger.error(f"Error getting schedules: {e}")
        return schedules

    def add_time_schedule(
        self,
        start_time: str,
        end_time: str,
        target_state: str = "on",
        enabled: bool = True
    ) -> Optional[int]:
        """
        Add a new time schedule.

        Args:
            start_time: Start time in "HH:MM" format
            end_time: End time in "HH:MM" format
            target_state: "on" or "off"
            enabled: Whether the schedule is active

        Returns:
            Schedule ID if successful, None otherwise
        """
        # Validate inputs
        if not self._validate_time_format(start_time):
            raise ValueError(f"Invalid start_time format: {start_time}")
        if not self._validate_time_format(end_time):
            raise ValueError(f"Invalid end_time format: {end_time}")
        if target_state not in ("on", "off"):
            raise ValueError(f"target_state must be 'on' or 'off', got: {target_state}")

        # Check for overlaps
        if self._check_schedule_overlap(start_time, end_time):
            raise ValueError("Schedule overlaps with existing schedule")

        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_time_schedules
                (device_id, start_time, end_time, target_state, enabled)
                VALUES (?, ?, ?, ?, ?)
            """, (self._device_id, start_time, end_time, target_state, int(enabled)))
            schedule_id = cursor.lastrowid
            conn.commit()
            conn.close()

            logger.info(f"Added schedule {schedule_id}: {start_time}-{end_time} ({target_state})")
            return schedule_id

        except Exception as e:
            logger.error(f"Error adding schedule: {e}")
            return None

    def delete_time_schedule(self, schedule_id: int) -> bool:
        """Delete a time schedule"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM device_time_schedules
                WHERE id = ? AND device_id = ?
            """, (schedule_id, self._device_id))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()

            if deleted:
                logger.info(f"Deleted schedule {schedule_id}")
            return deleted

        except Exception as e:
            logger.error(f"Error deleting schedule: {e}")
            return False

    def update_time_schedule(
        self,
        schedule_id: int,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        target_state: Optional[str] = None,
        enabled: Optional[bool] = None
    ) -> bool:
        """Update an existing time schedule"""
        try:
            # Build update query dynamically
            updates = []
            params = []

            if start_time is not None:
                if not self._validate_time_format(start_time):
                    raise ValueError(f"Invalid start_time: {start_time}")
                updates.append("start_time = ?")
                params.append(start_time)

            if end_time is not None:
                if not self._validate_time_format(end_time):
                    raise ValueError(f"Invalid end_time: {end_time}")
                updates.append("end_time = ?")
                params.append(end_time)

            if target_state is not None:
                if target_state not in ("on", "off"):
                    raise ValueError(f"Invalid target_state: {target_state}")
                updates.append("target_state = ?")
                params.append(target_state)

            if enabled is not None:
                updates.append("enabled = ?")
                params.append(int(enabled))

            if not updates:
                return True  # Nothing to update

            params.extend([schedule_id, self._device_id])

            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE device_time_schedules
                SET {', '.join(updates)}
                WHERE id = ? AND device_id = ?
            """, params)
            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()

            return updated

        except Exception as e:
            logger.error(f"Error updating schedule: {e}")
            return False

    def _validate_time_format(self, time_str: str) -> bool:
        """Validate time format is HH:MM"""
        try:
            parts = time_str.split(':')
            if len(parts) != 2:
                return False
            hours, minutes = int(parts[0]), int(parts[1])
            return 0 <= hours <= 23 and 0 <= minutes <= 59
        except (ValueError, AttributeError):
            return False

    def _check_schedule_overlap(
        self,
        start_time: str,
        end_time: str,
        exclude_id: Optional[int] = None
    ) -> bool:
        """Check if a schedule overlaps with existing schedules"""
        schedules = self.get_time_schedules()

        start = self._time_to_minutes(start_time)
        end = self._time_to_minutes(end_time)

        for schedule in schedules:
            if exclude_id and schedule.id == exclude_id:
                continue
            if not schedule.enabled:
                continue

            s_start = self._time_to_minutes(schedule.start_time)
            s_end = self._time_to_minutes(schedule.end_time)

            # Check for overlap (including midnight wrap-around)
            if self._times_overlap(start, end, s_start, s_end):
                return True

        return False

    def _time_to_minutes(self, time_str: str) -> int:
        """Convert HH:MM to minutes since midnight"""
        parts = time_str.split(':')
        return int(parts[0]) * 60 + int(parts[1])

    def _times_overlap(self, s1: int, e1: int, s2: int, e2: int) -> bool:
        """Check if two time ranges overlap (handling midnight wrap)"""
        # Normalize ranges that wrap around midnight
        if e1 < s1:
            e1 += 24 * 60
        if e2 < s2:
            e2 += 24 * 60

        # Check overlap
        return not (e1 <= s2 or e2 <= s1)

    def get_active_time_schedule(
        self,
        current_time: Optional[datetime] = None
    ) -> Optional[TimeSchedule]:
        """
        Check if there's an active time schedule for the current time.

        Handles midnight wrap-around (e.g., 23:00 - 01:00).

        Returns:
            Active schedule if in a time window, None otherwise
        """
        if not self._config.time_schedule_enabled:
            return None

        if current_time is None:
            current_time = datetime.now()

        current_minutes = current_time.hour * 60 + current_time.minute

        for schedule in self.get_time_schedules():
            if not schedule.enabled:
                continue

            start = self._time_to_minutes(schedule.start_time)
            end = self._time_to_minutes(schedule.end_time)

            # Handle midnight wrap-around
            if end < start:
                # Schedule wraps midnight (e.g., 23:00 - 01:00)
                if current_minutes >= start or current_minutes < end:
                    return schedule
            else:
                # Normal schedule (e.g., 19:00 - 20:30)
                if start <= current_minutes < end:
                    return schedule

        return None

    # =========================================================================
    # Control Logic
    # =========================================================================

    def check_and_control(self) -> Optional[bool]:
        """
        Main control logic with priority:
        1. TIME SCHEDULE (highest)
        2. HUMIDITY AUTOMATION (fallback)
        3. MANUAL (disabled automation)

        Returns:
            True if turned ON, False if turned OFF, None if no change
        """
        if not self._config.enabled:
            # Manual mode - don't change anything
            return None

        current_time = datetime.now()

        # PRIORITY 1: Check time schedule
        active_schedule = self.get_active_time_schedule(current_time)

        if active_schedule:
            # We're IN a time window
            self._was_in_time_window = True
            target_on = active_schedule.target_state == "on"

            logger.debug(
                f"Time schedule active: {active_schedule.start_time}-{active_schedule.end_time} "
                f"-> {'ON' if target_on else 'OFF'}"
            )

            if target_on and not self._is_on:
                return self._ensure_state(
                    True,
                    TriggerType.TIME_SCHEDULE,
                    f"{active_schedule.start_time}-{active_schedule.end_time}"
                )
            elif not target_on and self._is_on:
                return self._ensure_state(
                    False,
                    TriggerType.TIME_SCHEDULE,
                    f"{active_schedule.start_time}-{active_schedule.end_time}"
                )
            return None

        # Time window just ended - check fallback
        if self._was_in_time_window:
            self._was_in_time_window = False
            logger.info("Time schedule ended -> Checking humidity fallback")

            # Don't just turn off! Check humidity logic first
            humidity_decision = self._check_humidity_logic()
            if humidity_decision is not None:
                return self._ensure_state(
                    humidity_decision,
                    TriggerType.FALLBACK,
                    "post-schedule humidity check"
                )

        # PRIORITY 2: Humidity automation
        return self._check_humidity_automation()

    def _check_humidity_logic(self) -> Optional[bool]:
        """
        Check humidity and determine if device should be ON or OFF.

        Returns:
            True if should be ON, False if should be OFF, None if in hysteresis zone
        """
        humidity = self.get_humidity()
        if humidity is None:
            logger.warning("Humidity read failed - keeping current state")
            return None

        target = self._config.target
        high_threshold = target + self._config.threshold_high
        low_threshold = target - self._config.threshold_low

        if humidity > high_threshold:
            return True  # Should be ON
        elif humidity < low_threshold:
            return False  # Should be OFF
        else:
            return None  # In hysteresis zone - no change

    def _check_humidity_automation(self) -> Optional[bool]:
        """
        Humidity-based automation with hysteresis.

        Returns:
            True if turned ON, False if turned OFF, None if no change
        """
        humidity = self.get_humidity()
        if humidity is None:
            logger.warning("Humidity read failed - skipping automation")
            return None

        target = self._config.target
        high_threshold = target + self._config.threshold_high
        low_threshold = target - self._config.threshold_low

        logger.debug(
            f"Humidity: {humidity:.1f}% (target: {target}%, "
            f"high: {high_threshold}%, low: {low_threshold}%)"
        )

        # Check if humidity is too high -> turn ON
        if humidity > high_threshold and not self._is_on:
            return self._ensure_state(
                True,
                TriggerType.HUMIDITY_AUTO,
                f"humidity {humidity:.1f}% > {high_threshold}%"
            )

        # Check if humidity is low enough -> turn OFF
        if humidity < low_threshold and self._is_on:
            return self._ensure_state(
                False,
                TriggerType.HUMIDITY_AUTO,
                f"humidity {humidity:.1f}% < {low_threshold}%"
            )

        return None  # No change needed

    def _ensure_state(
        self,
        target_on: bool,
        trigger: TriggerType,
        details: str = ""
    ) -> Optional[bool]:
        """
        Ensure device is in the target state, respecting min run/off times.

        BUGFIX 6.9.2: For MANUAL triggers, ALWAYS send the command even if the
        internal state appears correct. This handles cases where:
        - Device was manually switched and status is stale
        - User explicitly wants to force the command
        - Status sync failed or returned incorrect data

        Returns:
            True if turned ON, False if turned OFF, None if blocked by min time
        """
        # BUGFIX 6.9.1: Sync with actual device status BEFORE checking state
        # This prevents issues when device was manually switched externally
        self._sync_device_status()

        # Check minimum time constraints (skip for MANUAL triggers - user override)
        if trigger != TriggerType.MANUAL and self._last_toggle_time:
            elapsed = (datetime.now() - self._last_toggle_time).total_seconds()

            if target_on and not self._is_on:
                # Want to turn ON - check min_off_time
                if elapsed < self._config.min_off_time:
                    logger.debug(f"Blocked: min_off_time ({elapsed:.0f}s < {self._config.min_off_time}s)")
                    return None
            elif not target_on and self._is_on:
                # Want to turn OFF - check min_run_time
                if elapsed < self._config.min_run_time:
                    logger.debug(f"Blocked: min_run_time ({elapsed:.0f}s < {self._config.min_run_time}s)")
                    return None

        # BUGFIX 6.9.2: For MANUAL triggers, ALWAYS send the command
        # Reason: User explicitly clicked the button, so we must honor the request
        # even if our internal state thinks the device is already in that state.
        # The internal state could be wrong due to stale cache, sync failure, etc.
        if trigger == TriggerType.MANUAL:
            if target_on == self._is_on:
                logger.info(
                    f"MANUAL override: forcing {'ON' if target_on else 'OFF'} command "
                    f"even though internal state is already {self._is_on}"
                )
            # Continue to execute command regardless of current state
        else:
            # For automation triggers: Skip if state is already correct
            if target_on == self._is_on:
                logger.debug(f"State already {'ON' if target_on else 'OFF'}, skipping (trigger: {trigger.value})")
                return None

        # Execute state change
        success = self._set_plug_state(target_on)

        if success:
            self._is_on = target_on
            self._last_toggle_time = datetime.now()
            self._last_trigger = trigger
            self._last_trigger_details = details

            # Log the state change
            self._log_state_change(target_on, trigger, details)

            logger.info(
                f"Dehumidifier {'ON' if target_on else 'OFF'} "
                f"(trigger: {trigger.value}, {details})"
            )
            return target_on
        else:
            logger.error(f"Failed to set dehumidifier state to {'ON' if target_on else 'OFF'}")
            return None

    def _set_plug_state(self, on: bool) -> bool:
        """Set the Tuya smart plug state"""
        if self._plug_controller is None:
            logger.warning("Plug controller not available - simulating state change")
            return True  # Simulate success for testing

        try:
            if self._tuya_device_id:
                if on:
                    return self._plug_controller.turn_on(self._tuya_device_id)
                else:
                    return self._plug_controller.turn_off(self._tuya_device_id)
            else:
                logger.warning("No Tuya device ID configured")
                return True  # Simulate success
        except Exception as e:
            logger.error(f"Error controlling plug: {e}")
            return False

    def _sync_device_status(self) -> None:
        """
        Synchronize internal state with actual Tuya device status.

        BUGFIX 6.9.1: This prevents status desync when the device is manually
        switched (physically or via Tuya app) without the controller knowing.

        Called before _ensure_state() checks to ensure we're working with
        the real device state, not a potentially stale internal state.
        """
        if self._plug_controller is None or not self._tuya_device_id:
            return  # No controller or device ID - skip sync

        try:
            status = self._plug_controller.get_status(self._tuya_device_id)
            if status is not None:
                # get_status returns {'on': bool, 'power': ..., 'voltage': ..., ...}
                actual_is_on = status.get('on', False)

                if actual_is_on != self._is_on:
                    logger.info(
                        f"Status sync: internal={self._is_on}, actual={actual_is_on} "
                        f"-> updating internal state"
                    )
                    self._is_on = actual_is_on
                    # Note: We don't update _last_toggle_time here because
                    # we don't know when the external change happened
        except Exception as e:
            logger.warning(f"Could not sync device status: {e}")

    def _log_state_change(self, on: bool, trigger: TriggerType, details: str) -> None:
        """Log state change to database"""
        try:
            import uuid
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO device_state_log (id, device_id, state, trigger_type, trigger_details)
                VALUES (?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                self._device_id,
                "on" if on else "off",
                trigger.value,
                details
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error logging state change: {e}")

    # =========================================================================
    # Manual Control
    # =========================================================================

    def switch_on(self) -> bool:
        """Manually turn on dehumidifier"""
        result = self._ensure_state(True, TriggerType.MANUAL, "manual on")
        return result is True

    def switch_off(self) -> bool:
        """Manually turn off dehumidifier"""
        result = self._ensure_state(False, TriggerType.MANUAL, "manual off")
        return result is True

    # =========================================================================
    # Configuration
    # =========================================================================

    def get_config(self) -> Dict:
        """Get current configuration"""
        return self._config.to_dict()

    def update_config(
        self,
        enabled: Optional[bool] = None,
        target: Optional[float] = None,
        threshold_high: Optional[float] = None,
        threshold_low: Optional[float] = None,
        min_run_time: Optional[int] = None,
        min_off_time: Optional[int] = None,
        time_schedule_enabled: Optional[bool] = None,
        **kwargs  # Ignore unknown parameters
    ) -> Dict:
        """Update configuration"""
        if enabled is not None:
            self._config.enabled = enabled
        if target is not None:
            self._config.target = target
        if threshold_high is not None:
            self._config.threshold_high = threshold_high
        if threshold_low is not None:
            self._config.threshold_low = threshold_low
        if min_run_time is not None:
            self._config.min_run_time = min_run_time
        if min_off_time is not None:
            self._config.min_off_time = min_off_time
        if time_schedule_enabled is not None:
            self._config.time_schedule_enabled = time_schedule_enabled

        # Save to database
        self._save_config()

        return self._config.to_dict()

    def _save_config(self) -> None:
        """Save configuration to database"""
        try:
            conn = sqlite3.connect(self._db_path)
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE device_automation_config
                SET enabled = ?, target_value = ?, threshold_high = ?,
                    threshold_low = ?, min_run_time = ?, min_off_time = ?,
                    time_schedule_enabled = ?, updated_at = datetime('now')
                WHERE device_id = ?
            """, (
                int(self._config.enabled),
                self._config.target,
                self._config.threshold_high,
                self._config.threshold_low,
                self._config.min_run_time,
                self._config.min_off_time,
                int(self._config.time_schedule_enabled),
                self._device_id
            ))
            conn.commit()
            conn.close()
            logger.debug("Configuration saved")
        except Exception as e:
            logger.error(f"Error saving config: {e}")

    # =========================================================================
    # Status
    # =========================================================================

    def get_status(self) -> Dict:
        """Get current status"""
        # BUGFIX 6.9.1: Sync with actual device status before returning
        # This ensures API always returns the real device state
        self._sync_device_status()

        humidity = self.get_humidity()

        # Get active schedule if any
        active_schedule = self.get_active_time_schedule()
        active_schedule_info = None
        if active_schedule:
            active_schedule_info = {
                "id": active_schedule.id,
                "start_time": active_schedule.start_time,
                "end_time": active_schedule.end_time,
                "target_state": active_schedule.target_state
            }

        return {
            "is_on": self._is_on,
            "humidity": humidity,
            "config": self._config.to_dict(),
            "last_toggle": self._last_toggle_time.isoformat() if self._last_toggle_time else None,
            "last_trigger": self._last_trigger.value if self._last_trigger else None,
            "last_trigger_details": self._last_trigger_details,
            "active_schedule": active_schedule_info,
            "available": True
        }

    # =========================================================================
    # Background Control Loop
    # =========================================================================

    def start(self, check_interval: int = 10) -> None:
        """Start the background control loop"""
        if self._running:
            return

        self._running = True
        self._stop_event.clear()

        def control_loop():
            logger.info(f"Control loop started (interval: {check_interval}s)")
            while not self._stop_event.is_set():
                try:
                    self.check_and_control()
                except Exception as e:
                    logger.error(f"Control loop error: {e}")

                # Wait with event for clean shutdown
                self._stop_event.wait(timeout=check_interval)

            logger.info("Control loop stopped")

        self._thread = threading.Thread(target=control_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background control loop"""
        if not self._running:
            return

        self._running = False
        self._stop_event.set()

        if self._thread:
            self._thread.join(timeout=5)

        logger.info("DehumidifierController stopped")


# Singleton accessor
_controller_instance: Optional[DehumidifierController] = None


def get_dehumidifier_controller() -> DehumidifierController:
    """Get or create the singleton DehumidifierController instance"""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = DehumidifierController()
    return _controller_instance
