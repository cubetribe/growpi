#!/usr/bin/env python3
"""
GrowPi Mode Manager

Centralized mode management to prevent race conditions.
Persists mode to disk for crash recovery.

Modes:
- auto: Zeitsteuerung (curves control the lamps)
- manual: Manuell (sliders control the lamps)

IMPORTANT:
- On startup: ALWAYS defaults to 'auto' for plant safety
- Mode is persisted to /tmp/growpi_mode.txt
- Single source of truth for mode across all modules

Thread-Safety (v6.23.0):
- All public methods are thread-safe via self._lock
- LOCK ORDERING: This is lock #2 in the global lock hierarchy
  (sensor_cache._cache_lock → mode_manager._lock → pwm_state._lock)
"""

import os
import logging
import threading
from typing import Optional, Callable, Dict, List

logger = logging.getLogger(__name__)

# Mode file location - /tmp is cleared on reboot, ensuring 'auto' default
MODE_FILE = "/tmp/growpi_mode.txt"

# Valid modes
MODES = ('auto', 'manual')

# Singleton instance
_mode_manager_instance: Optional["ModeManager"] = None


def get_mode_manager() -> "ModeManager":
    """Get the global ModeManager singleton instance."""
    global _mode_manager_instance
    if _mode_manager_instance is None:
        _mode_manager_instance = ModeManager()
    return _mode_manager_instance


class ModeManager:
    """
    Centralized mode management.

    Thread-safe singleton that manages the current operating mode.
    Notifies registered callbacks when mode changes.
    """

    def __init__(self):
        self._mode: str = "auto"
        self._lock = threading.Lock()
        self._callbacks: List[Callable[[str, str], None]] = []
        self._mode_file_mtime: Optional[float] = None
        self._load_mode()

    def _load_mode(self) -> None:
        """Load mode from file, default to 'auto' if not exists."""
        try:
            if os.path.exists(MODE_FILE):
                self._mode_file_mtime = os.path.getmtime(MODE_FILE)
                with open(MODE_FILE, 'r') as f:
                    mode = f.read().strip()
                    if mode in MODES:
                        self._mode = mode
                        logger.info(f"Mode loaded from file: {mode}")
                    else:
                        logger.warning(f"Invalid mode in file: {mode}, using 'auto'")
                        self._mode = "auto"
            else:
                logger.info("No mode file found, defaulting to 'auto'")
                self._mode = "auto"
                self._mode_file_mtime = None
        except Exception as e:
            logger.error(f"Error loading mode: {e}, defaulting to 'auto'")
            self._mode = "auto"
            self._mode_file_mtime = None

    def _save_mode(self) -> None:
        """Save mode to file."""
        try:
            with open(MODE_FILE, 'w') as f:
                f.write(self._mode)
            self._mode_file_mtime = os.path.getmtime(MODE_FILE)
        except Exception as e:
            logger.error(f"Error saving mode: {e}")

    def _sync_mode_from_file(self) -> None:
        """
        Sync mode with persistent state file for cross-process consistency.

        In split-process mode the web and controller services run in separate
        processes. This method ensures both processes observe mode changes.
        """
        try:
            if not os.path.exists(MODE_FILE):
                self._mode_file_mtime = None
                return

            current_mtime = os.path.getmtime(MODE_FILE)
            if self._mode_file_mtime is not None and current_mtime <= self._mode_file_mtime:
                return

            with open(MODE_FILE, 'r') as f:
                mode = f.read().strip()

            self._mode_file_mtime = current_mtime

            if mode in MODES and mode != self._mode:
                old_mode = self._mode
                self._mode = mode
                logger.info(f"Mode synced from file: {old_mode} -> {mode}")
        except Exception as e:
            logger.error(f"Error syncing mode from file: {e}")

    def get_mode(self) -> str:
        """Get current mode (thread-safe)."""
        with self._lock:
            self._sync_mode_from_file()
            return self._mode

    def set_mode(self, mode: str) -> bool:
        """
        Set operating mode.

        Args:
            mode: 'auto' or 'manual'

        Returns:
            True if mode was changed, False if invalid or same
        """
        if mode not in MODES:
            logger.error(f"Invalid mode: {mode}")
            return False

        with self._lock:
            old_mode = self._mode
            if mode == old_mode:
                return False  # No change

            self._mode = mode
            self._save_mode()
            logger.info(f"Mode changed: {old_mode} -> {mode}")

        # Notify callbacks (outside lock to prevent deadlocks)
        self._notify_callbacks(old_mode, mode)
        return True

    def is_auto(self) -> bool:
        """Check if currently in auto mode."""
        return self.get_mode() == "auto"

    def is_manual(self) -> bool:
        """Check if currently in manual mode."""
        return self.get_mode() == "manual"

    def register_callback(self, callback: Callable[[str, str], None]) -> None:
        """
        Register a callback for mode changes.

        Callback signature: callback(old_mode: str, new_mode: str)

        v6.23.0: Lock protection already present - thread-safe.
        """
        with self._lock:
            self._callbacks.append(callback)

    def _notify_callbacks(self, old_mode: str, new_mode: str) -> None:
        """
        Notify all registered callbacks about mode change.

        v6.23.0: Thread-safe callback iteration.
        Creates a copy of callbacks list to avoid issues if callbacks modify the list.
        """
        # Create a copy of callbacks to iterate safely
        with self._lock:
            callbacks_copy = self._callbacks.copy()

        # Execute callbacks outside lock to prevent deadlocks
        for callback in callbacks_copy:
            try:
                callback(old_mode, new_mode)
            except Exception as e:
                logger.error(f"Mode callback error: {e}")
