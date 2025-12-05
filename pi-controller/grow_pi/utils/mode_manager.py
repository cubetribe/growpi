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
        self._load_mode()

    def _load_mode(self) -> None:
        """Load mode from file, default to 'auto' if not exists."""
        try:
            if os.path.exists(MODE_FILE):
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
        except Exception as e:
            logger.error(f"Error loading mode: {e}, defaulting to 'auto'")
            self._mode = "auto"

    def _save_mode(self) -> None:
        """Save mode to file."""
        try:
            with open(MODE_FILE, 'w') as f:
                f.write(self._mode)
        except Exception as e:
            logger.error(f"Error saving mode: {e}")

    def get_mode(self) -> str:
        """Get current mode (thread-safe)."""
        with self._lock:
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
        """
        with self._lock:
            self._callbacks.append(callback)

    def _notify_callbacks(self, old_mode: str, new_mode: str) -> None:
        """Notify all registered callbacks about mode change."""
        for callback in self._callbacks:
            try:
                callback(old_mode, new_mode)
            except Exception as e:
                logger.error(f"Mode callback error: {e}")
