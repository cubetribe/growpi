#!/usr/bin/env python3
"""
Unit Tests for ModeManager

Tests mode management, persistence, callbacks, and thread safety.
Critical for preventing race conditions in lamp control.
"""

import pytest
import threading
import time
from pathlib import Path
from unittest.mock import Mock, patch
from grow_pi.utils.mode_manager import ModeManager, MODES


@pytest.fixture
def temp_mode_file(tmp_path):
    """Create a temporary mode file for testing."""
    mode_file = tmp_path / "test_mode.txt"
    return str(mode_file)


@pytest.fixture
def mode_manager_instance(temp_mode_file):
    """Create a fresh ModeManager instance with temporary mode file."""
    with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
        manager = ModeManager()
        yield manager


class TestModeManagerDefaults:
    """Test default mode initialization."""

    def test_default_mode_is_auto(self, mode_manager_instance):
        """ModeManager should default to 'auto' mode on initialization."""
        assert mode_manager_instance.get_mode() == "auto"

    def test_is_auto_returns_true_by_default(self, mode_manager_instance):
        """is_auto() should return True by default."""
        assert mode_manager_instance.is_auto() is True

    def test_is_manual_returns_false_by_default(self, mode_manager_instance):
        """is_manual() should return False by default."""
        assert mode_manager_instance.is_manual() is False


class TestModeManagerSetMode:
    """Test mode setting functionality."""

    def test_set_mode_auto(self, mode_manager_instance):
        """Setting mode to 'auto' should succeed."""
        # First change to manual, then back to auto
        mode_manager_instance.set_mode("manual")
        result = mode_manager_instance.set_mode("auto")
        assert result is True
        assert mode_manager_instance.get_mode() == "auto"

    def test_set_mode_manual(self, mode_manager_instance):
        """Setting mode to 'manual' should succeed."""
        result = mode_manager_instance.set_mode("manual")
        assert result is True
        assert mode_manager_instance.get_mode() == "manual"

    def test_invalid_mode_rejected(self, mode_manager_instance):
        """Invalid modes should be rejected."""
        result = mode_manager_instance.set_mode("invalid")
        assert result is False
        assert mode_manager_instance.get_mode() == "auto"  # Should remain unchanged

    def test_set_same_mode_returns_false(self, mode_manager_instance):
        """Setting the same mode should return False (no change)."""
        result = mode_manager_instance.set_mode("auto")
        assert result is False  # Already in auto mode

    def test_empty_string_mode_rejected(self, mode_manager_instance):
        """Empty string should be rejected as invalid mode."""
        result = mode_manager_instance.set_mode("")
        assert result is False
        assert mode_manager_instance.get_mode() == "auto"

    def test_none_mode_rejected(self, mode_manager_instance):
        """None should be rejected as invalid mode."""
        result = mode_manager_instance.set_mode(None)
        assert result is False
        assert mode_manager_instance.get_mode() == "auto"


class TestModeManagerPersistence:
    """Test mode persistence to file system."""

    def test_mode_persistence_to_file(self, temp_mode_file, mode_manager_instance):
        """Mode changes should be persisted to file."""
        mode_manager_instance.set_mode("manual")

        # Read file directly
        with open(temp_mode_file, 'r') as f:
            saved_mode = f.read().strip()

        assert saved_mode == "manual"

    def test_mode_loaded_from_file(self, temp_mode_file):
        """Mode should be loaded from file on initialization."""
        # Pre-create mode file with manual mode
        with open(temp_mode_file, 'w') as f:
            f.write("manual")

        # Create new manager instance
        with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
            manager = ModeManager()

        assert manager.get_mode() == "manual"

    def test_invalid_mode_in_file_defaults_to_auto(self, temp_mode_file):
        """Invalid mode in file should default to 'auto'."""
        # Pre-create mode file with invalid mode
        with open(temp_mode_file, 'w') as f:
            f.write("invalid_mode")

        with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
            manager = ModeManager()

        assert manager.get_mode() == "auto"

    def test_missing_mode_file_defaults_to_auto(self, temp_mode_file):
        """Missing mode file should default to 'auto'."""
        # Don't create file - it doesn't exist
        with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
            manager = ModeManager()

        assert manager.get_mode() == "auto"

    def test_corrupted_mode_file_defaults_to_auto(self, temp_mode_file):
        """Corrupted/unreadable mode file should default to 'auto'."""
        # Create file with permission issues
        Path(temp_mode_file).touch()
        Path(temp_mode_file).chmod(0o000)  # No permissions

        try:
            with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
                manager = ModeManager()
            assert manager.get_mode() == "auto"
        finally:
            # Restore permissions for cleanup
            Path(temp_mode_file).chmod(0o644)

    def test_mode_syncs_when_file_changes_externally(self, temp_mode_file):
        """get_mode() should sync when another process updates the mode file."""
        with patch('grow_pi.utils.mode_manager.MODE_FILE', temp_mode_file):
            manager = ModeManager()
            assert manager.get_mode() == "auto"

            time.sleep(0.01)
            with open(temp_mode_file, 'w') as f:
                f.write("manual")

            assert manager.get_mode() == "manual"


class TestModeManagerBooleanHelpers:
    """Test is_auto() and is_manual() helper methods."""

    def test_is_auto_returns_correct_bool(self, mode_manager_instance):
        """is_auto() should correctly reflect current mode."""
        mode_manager_instance.set_mode("auto")
        assert mode_manager_instance.is_auto() is True

        mode_manager_instance.set_mode("manual")
        assert mode_manager_instance.is_auto() is False

    def test_is_manual_returns_correct_bool(self, mode_manager_instance):
        """is_manual() should correctly reflect current mode."""
        mode_manager_instance.set_mode("manual")
        assert mode_manager_instance.is_manual() is True

        mode_manager_instance.set_mode("auto")
        assert mode_manager_instance.is_manual() is False


class TestModeManagerCallbacks:
    """Test callback registration and notification."""

    def test_callback_registered(self, mode_manager_instance):
        """Callbacks should be registered successfully."""
        callback = Mock()
        mode_manager_instance.register_callback(callback)

        # Trigger mode change
        mode_manager_instance.set_mode("manual")

        # Callback should be called
        callback.assert_called_once_with("auto", "manual")

    def test_callback_called_on_mode_change(self, mode_manager_instance):
        """Callback should be called with correct old/new modes."""
        callback = Mock()
        mode_manager_instance.register_callback(callback)

        # Change mode
        mode_manager_instance.set_mode("manual")
        callback.assert_called_with("auto", "manual")

        # Change back
        mode_manager_instance.set_mode("auto")
        callback.assert_called_with("manual", "auto")

    def test_callback_not_called_on_same_mode(self, mode_manager_instance):
        """Callback should NOT be called if mode doesn't change."""
        callback = Mock()
        mode_manager_instance.register_callback(callback)

        # Try to set same mode
        mode_manager_instance.set_mode("auto")

        # Callback should not be called
        callback.assert_not_called()

    def test_multiple_callbacks_registered(self, mode_manager_instance):
        """Multiple callbacks should all be called."""
        callback1 = Mock()
        callback2 = Mock()
        callback3 = Mock()

        mode_manager_instance.register_callback(callback1)
        mode_manager_instance.register_callback(callback2)
        mode_manager_instance.register_callback(callback3)

        mode_manager_instance.set_mode("manual")

        callback1.assert_called_once_with("auto", "manual")
        callback2.assert_called_once_with("auto", "manual")
        callback3.assert_called_once_with("auto", "manual")

    def test_callback_exception_does_not_crash(self, mode_manager_instance):
        """Exception in callback should not crash mode change."""
        def failing_callback(old, new):
            raise ValueError("Test exception")

        successful_callback = Mock()

        mode_manager_instance.register_callback(failing_callback)
        mode_manager_instance.register_callback(successful_callback)

        # Should not raise exception
        mode_manager_instance.set_mode("manual")

        # Mode should still change
        assert mode_manager_instance.get_mode() == "manual"

        # Other callback should still be called
        successful_callback.assert_called_once_with("auto", "manual")


class TestModeManagerThreadSafety:
    """Test thread-safety of ModeManager."""

    def test_thread_safety_concurrent_reads(self, mode_manager_instance):
        """Multiple threads reading mode should not cause issues."""
        results = []

        def read_mode():
            for _ in range(100):
                mode = mode_manager_instance.get_mode()
                results.append(mode)

        threads = [threading.Thread(target=read_mode) for _ in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All reads should succeed
        assert len(results) == 1000
        assert all(mode in MODES for mode in results)

    def test_thread_safety_concurrent_writes(self, mode_manager_instance):
        """Multiple threads writing mode should maintain consistency."""
        def toggle_mode():
            for i in range(50):
                if i % 2 == 0:
                    mode_manager_instance.set_mode("manual")
                else:
                    mode_manager_instance.set_mode("auto")

        threads = [threading.Thread(target=toggle_mode) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Final mode should be valid
        final_mode = mode_manager_instance.get_mode()
        assert final_mode in MODES

    def test_thread_safety_concurrent_read_write(self, mode_manager_instance):
        """Concurrent reads and writes should maintain consistency."""
        read_results = []
        write_count = [0]

        def reader():
            for _ in range(100):
                mode = mode_manager_instance.get_mode()
                read_results.append(mode)
                time.sleep(0.001)  # Small delay

        def writer():
            for i in range(50):
                if i % 2 == 0:
                    if mode_manager_instance.set_mode("manual"):
                        write_count[0] += 1
                else:
                    if mode_manager_instance.set_mode("auto"):
                        write_count[0] += 1
                time.sleep(0.001)

        readers = [threading.Thread(target=reader) for _ in range(3)]
        writers = [threading.Thread(target=writer) for _ in range(2)]

        all_threads = readers + writers
        for t in all_threads:
            t.start()
        for t in all_threads:
            t.join()

        # All reads should return valid modes
        assert all(mode in MODES for mode in read_results)

        # Some writes should have succeeded
        assert write_count[0] > 0

    def test_thread_safety_callback_registration(self, mode_manager_instance):
        """Callbacks can be safely registered during mode changes."""
        callbacks = [Mock() for _ in range(10)]

        def register_callbacks():
            for callback in callbacks:
                mode_manager_instance.register_callback(callback)
                time.sleep(0.001)

        def change_modes():
            for i in range(10):
                mode = "manual" if i % 2 == 0 else "auto"
                mode_manager_instance.set_mode(mode)
                time.sleep(0.001)

        t1 = threading.Thread(target=register_callbacks)
        t2 = threading.Thread(target=change_modes)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Final mode should be valid
        assert mode_manager_instance.get_mode() in MODES


class TestModeManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_mode_returns_string(self, mode_manager_instance):
        """get_mode() should always return a string."""
        mode = mode_manager_instance.get_mode()
        assert isinstance(mode, str)

    def test_mode_case_sensitivity(self, mode_manager_instance):
        """Mode should be case-sensitive (uppercase 'AUTO' is invalid)."""
        result = mode_manager_instance.set_mode("AUTO")
        assert result is False
        assert mode_manager_instance.get_mode() == "auto"

    def test_mode_with_whitespace_rejected(self, mode_manager_instance):
        """Mode with whitespace should be rejected."""
        result = mode_manager_instance.set_mode(" auto ")
        assert result is False
        assert mode_manager_instance.get_mode() == "auto"

    def test_rapid_mode_changes(self, mode_manager_instance):
        """Rapid mode changes should all be handled correctly."""
        for i in range(100):
            mode = "manual" if i % 2 == 0 else "auto"
            mode_manager_instance.set_mode(mode)

        # Final mode should be auto (i=99 is odd)
        assert mode_manager_instance.get_mode() == "auto"
