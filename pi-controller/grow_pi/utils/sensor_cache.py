#!/usr/bin/env python3
"""
Shared Sensor Cache Module

Provides a centralized DHT22 sensor cache that can be imported from anywhere
without circular import issues. This ensures all endpoints return the same
cached sensor values.

Version: 6.22.4
"""

import logging
import time
from typing import Tuple, Optional, Callable

logger = logging.getLogger(__name__)

# ============================================================================
# DHT22 Sensor Cache Configuration
# ============================================================================

DHT_CACHE_SECONDS = 10  # v6.22.4: Reduced from 30 to 10 seconds for fresher data
DHT_MAX_CONSECUTIVE_ERRORS = 10  # Log system event after this many failures
DHT_REINIT_AFTER_ERRORS = 20  # v6.22.4: Reinitialize sensor after this many consecutive failures

# Shared cache - single source of truth for all sensor readings
_sensor_cache = {
    "temp": None,
    "humidity": None,
    "timestamp": 0,
    "error_count": 0
}

# Sensor instance and availability (set by init_sensor())
_dht_sensor = None
_dht_available = False

# Data logger for system events (optional, set by init_data_logger())
_data_logger = None


def init_sensor(sensor, available: bool = True) -> None:
    """
    Initialize the DHT22 sensor instance.

    Args:
        sensor: The adafruit_dht.DHT22 sensor instance
        available: Whether the sensor is available (False for mock mode)
    """
    global _dht_sensor, _dht_available
    _dht_sensor = sensor
    _dht_available = available
    logger.info(f"Sensor cache initialized (available={available})")


def init_data_logger(data_logger) -> None:
    """
    Initialize the data logger for system events.

    Args:
        data_logger: DataLogger instance for logging sensor failures
    """
    global _data_logger
    _data_logger = data_logger


def reinitialize_sensor() -> bool:
    """
    Attempt to reinitialize the DHT22 sensor after persistent failures.

    v6.22.4: Added to recover from sensor freeze states.

    Returns:
        True if reinitialization was successful, False otherwise
    """
    global _dht_sensor, _dht_available, _sensor_cache

    if not _dht_available:
        return False

    try:
        import board
        import adafruit_dht

        # Try to exit/cleanup existing sensor
        if _dht_sensor:
            try:
                _dht_sensor.exit()
            except Exception:
                pass

        # Wait before reinit
        time.sleep(2)

        # Reinitialize
        _dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        _sensor_cache["error_count"] = 0
        logger.warning("DHT22 sensor reinitialized after persistent failures")
        return True
    except Exception as e:
        logger.error(f"Failed to reinitialize DHT22: {e}")
        return False


def get_cache_age() -> float:
    """
    Get the age of the cached sensor values in seconds.

    v6.22.4: Added for monitoring cache freshness.

    Returns:
        Age of cache in seconds (0 if never cached)
    """
    return time.time() - _sensor_cache.get("timestamp", 0)


def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    """
    Read temperature and humidity from DHT22 sensor with caching.

    This is THE ONLY function that should be used to read DHT22 values.
    All endpoints should call this function to ensure consistent values.

    Returns:
        Tuple of (temperature, humidity) or (None, None) on error
    """
    global _sensor_cache

    now = time.time()

    # Return cached value if still valid
    if now - _sensor_cache["timestamp"] < DHT_CACHE_SECONDS:
        if _sensor_cache["temp"] is not None:
            return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # Mock mode - generate fake data
    if not _dht_available or _dht_sensor is None:
        import random
        _sensor_cache["temp"] = round(20 + random.uniform(-2, 2), 1)
        _sensor_cache["humidity"] = round(60 + random.uniform(-5, 5), 1)
        _sensor_cache["timestamp"] = now
        _sensor_cache["error_count"] = 0
        return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # Try to read from real sensor (up to 3 attempts)
    for attempt in range(3):
        try:
            temp = _dht_sensor.temperature
            humidity = _dht_sensor.humidity

            if temp is not None and humidity is not None:
                _sensor_cache["temp"] = round(temp, 1)
                _sensor_cache["humidity"] = round(humidity, 1)
                # BUGFIX v6.22.3: Always update timestamp, even on success
                _sensor_cache["timestamp"] = now
                _sensor_cache["error_count"] = 0
                return (_sensor_cache["temp"], _sensor_cache["humidity"])
        except Exception as e:
            if attempt < 2:
                time.sleep(0.5)
            logger.debug(f"DHT22 read attempt {attempt + 1} failed: {e}")

    # All 3 attempts failed - increment error counter
    _sensor_cache["error_count"] += 1
    # BUGFIX v6.22.3: CRITICAL - Always update timestamp after sensor read attempt
    # This prevents infinite cache loops when sensor fails
    _sensor_cache["timestamp"] = now

    # Log persistent errors
    if _sensor_cache["error_count"] >= DHT_MAX_CONSECUTIVE_ERRORS:
        logger.error(f"DHT22 failed {_sensor_cache['error_count']} times consecutively")

        # Log system event if data logger available
        if _data_logger and _sensor_cache["error_count"] == DHT_MAX_CONSECUTIVE_ERRORS:
            try:
                _data_logger.log_event(
                    'sensor_persistent_error',
                    'error',
                    f'DHT22 failed {_sensor_cache["error_count"]} consecutive reads',
                    {'error_count': _sensor_cache["error_count"]}
                )
            except Exception:
                pass

    # v6.22.4: Attempt sensor reinitialization after too many consecutive errors
    if _sensor_cache["error_count"] >= DHT_REINIT_AFTER_ERRORS:
        logger.critical(f"SENSOR FREEZE DETECTED - {_sensor_cache['error_count']} consecutive failures - Attempting reinit")
        if reinitialize_sensor():
            # Reset timestamp to force immediate retry on next call
            _sensor_cache["timestamp"] = 0
            # Log the reinit event
            if _data_logger:
                try:
                    _data_logger.log_event(
                        'sensor_reinit',
                        'warning',
                        'DHT22 sensor reinitialized after freeze detection',
                        {'previous_error_count': DHT_REINIT_AFTER_ERRORS}
                    )
                except Exception:
                    pass

    # Return last known good value if available
    if _sensor_cache["temp"] is not None:
        if _sensor_cache["error_count"] > 0:
            logger.warning(f"DHT22 read failed (error #{_sensor_cache['error_count']}) - returning cached value")
        return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # No cached value available
    return (None, None)


def get_cached_values() -> Tuple[Optional[float], Optional[float]]:
    """
    Get the current cached sensor values WITHOUT reading the sensor.

    Use this when you just need the values without triggering a sensor read.

    Returns:
        Tuple of (temperature, humidity) from cache
    """
    return (_sensor_cache.get("temp"), _sensor_cache.get("humidity"))


def get_cache_status() -> dict:
    """
    Get cache status information for debugging.

    v6.22.4: Added cache_age and reinit_threshold fields.

    Returns:
        Dictionary with cache state information
    """
    return {
        "temp": _sensor_cache.get("temp"),
        "humidity": _sensor_cache.get("humidity"),
        "timestamp": _sensor_cache.get("timestamp"),
        "cache_age": get_cache_age(),
        "error_count": _sensor_cache.get("error_count"),
        "sensor_available": _dht_available,
        "cache_ttl": DHT_CACHE_SECONDS,
        "reinit_threshold": DHT_REINIT_AFTER_ERRORS
    }
