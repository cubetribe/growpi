#!/usr/bin/env python3
"""
GrowPi Web Dependencies
Centralized dependency injection for Flask blueprints.

This module provides singleton access to all core services and controllers,
ensuring blueprints don't directly couple to hardware implementations.
"""

import logging
from typing import Optional, Callable, Tuple, Dict
from .services.lamp_config import get_lamp_channels, LampChannel
from ..version import get_version

logger = logging.getLogger(__name__)

# ============================================================================
# Global Singletons (initialized by app.py)
# ============================================================================

_pwm_controller = None
_dht_sensor = None
_data_logger = None
_curve_controller = None
_mode_manager = None
_db = None

# Availability flags
_dht_available = False
_db_available = False
_curve_available = False
_mode_available = False

# API Version - dynamically loaded from VERSION file
_api_version = get_version()


# ============================================================================
# Initialization Functions (called by app.py)
# ============================================================================

def init_pwm_controller(controller):
    """Initialize PWM controller singleton."""
    global _pwm_controller
    _pwm_controller = controller
    logger.info("PWM Controller dependency registered")


def init_dht_sensor(sensor, available: bool = True):
    """Initialize DHT22 sensor singleton."""
    global _dht_sensor, _dht_available
    _dht_sensor = sensor
    _dht_available = available
    logger.info(f"DHT22 Sensor dependency registered (available: {available})")


def init_data_logger(logger_instance, db_instance=None):
    """Initialize data logger and database singletons."""
    global _data_logger, _db, _db_available
    _data_logger = logger_instance
    _db = db_instance
    _db_available = db_instance is not None
    logger.info(f"DataLogger dependency registered (DB available: {_db_available})")


def init_curve_controller(controller, available: bool = True):
    """Initialize curve controller singleton."""
    global _curve_controller, _curve_available
    _curve_controller = controller
    _curve_available = available
    logger.info(f"CurveController dependency registered (available: {available})")


def init_mode_manager(manager, available: bool = True):
    """Initialize mode manager singleton."""
    global _mode_manager, _mode_available
    _mode_manager = manager
    _mode_available = available
    logger.info(f"ModeManager dependency registered (available: {available})")


# ============================================================================
# Getter Functions (used by blueprints)
# ============================================================================

def get_pwm_controller():
    """Get PWM controller instance."""
    return _pwm_controller


def get_dht_sensor():
    """Get DHT22 sensor instance."""
    return _dht_sensor


def get_data_logger():
    """Get data logger instance."""
    return _data_logger


def get_curve_controller():
    """Get curve controller instance."""
    return _curve_controller


def get_mode_manager():
    """Get mode manager instance."""
    return _mode_manager


def get_database():
    """Get database instance."""
    return _db


# ============================================================================
# Availability Checks
# ============================================================================

def is_dht_available() -> bool:
    """Check if DHT22 sensor is available."""
    return _dht_available


def is_db_available() -> bool:
    """Check if database is available."""
    return _db_available


def is_curve_available() -> bool:
    """Check if curve controller is available."""
    return _curve_available


def is_mode_available() -> bool:
    """Check if mode manager is available."""
    return _mode_available


# ============================================================================
# Configuration Getters
# ============================================================================

def get_lamp_channels_dict() -> Dict[int, LampChannel]:
    """
    Get lamp channel configuration.

    Returns:
        Dictionary mapping channel IDs to LampChannel objects
    """
    return get_lamp_channels()


def get_api_version() -> str:
    """Get current API version."""
    return _api_version


# ============================================================================
# Convenience Functions for Blueprints
# ============================================================================

def get_dht_reader() -> Callable[[], Tuple[Optional[float], Optional[float]]]:
    """
    Get a function to read DHT22 sensor data.

    Returns:
        Callable that returns (temperature, humidity) tuple
    """
    sensor = get_dht_sensor()

    if sensor and is_dht_available():
        # Real hardware sensor
        def read_sensor():
            try:
                temperature = sensor.temperature
                humidity = sensor.humidity
                return (temperature, humidity)
            except Exception as e:
                logger.error(f"DHT22 read error: {e}")
                return (None, None)
        return read_sensor
    else:
        # Mock data for development
        import random
        def mock_sensor():
            temp = round(20 + random.uniform(-2, 2), 1)
            humidity = round(60 + random.uniform(-5, 5), 1)
            return (temp, humidity)
        return mock_sensor


def get_lamp_reader() -> Callable[[], Dict[int, Dict]]:
    """
    Get a function to read current lamp states.

    Returns:
        Callable that returns dict of lamp states
    """
    pwm = get_pwm_controller()
    channels = get_lamp_channels()

    def read_lamps():
        states = {}
        if pwm:
            current_state = pwm.get_current_state()
            for channel_id, config in channels.items():
                intensity = current_state.get(channel_id, 0)
                states[channel_id] = {
                    "name": config.name,
                    "intensity": intensity,
                    "gpio": config.gpio_pin
                }
        else:
            # Fallback when PWM not available
            for channel_id, config in channels.items():
                states[channel_id] = {
                    "name": config.name,
                    "intensity": 0,
                    "gpio": config.gpio_pin
                }
        return states

    return read_lamps


# ============================================================================
# Cleanup
# ============================================================================

def cleanup_all():
    """
    Clean up all resources.
    Called during application shutdown.
    """
    global _pwm_controller, _dht_sensor, _data_logger, _curve_controller, _mode_manager, _db

    logger.info("Cleaning up dependencies...")

    # Stop data logger
    if _data_logger:
        try:
            _data_logger.stop()
            logger.info("DataLogger stopped")
        except Exception as e:
            logger.error(f"Error stopping DataLogger: {e}")

    # PWM controller cleanup is handled by its own destructor
    if _pwm_controller:
        logger.info("PWM Controller cleanup initiated")

    # Reset all singletons
    _pwm_controller = None
    _dht_sensor = None
    _data_logger = None
    _curve_controller = None
    _mode_manager = None
    _db = None

    logger.info("Dependencies cleanup complete")
