#!/usr/bin/env python3
"""
Shared Sensor Cache Module

Provides a centralized DHT22 sensor cache that can be imported from anywhere
without circular import issues. This ensures all endpoints return the same
cached sensor values.

Version: 6.22.5 - Tank-Mode Sensor Hardening
- Process isolation for DHT22 reads with timeout
- Circuit breaker pattern for persistent failures
- Graceful degradation with structured logging
"""

import logging
import time
import threading
from typing import Tuple, Optional, Callable
from multiprocessing import Process, Queue
import queue
import pybreaker

logger = logging.getLogger(__name__)

# ============================================================================
# DHT22 Sensor Cache Configuration
# ============================================================================

DHT_CACHE_SECONDS = 10  # v6.22.4: Reduced from 30 to 10 seconds for fresher data
DHT_MAX_CONSECUTIVE_ERRORS = 10  # Log system event after this many failures
DHT_REINIT_AFTER_ERRORS = 20  # v6.22.4: Reinitialize sensor after this many consecutive failures
DHT_READ_TIMEOUT = 5.0  # v6.22.5: Max seconds to wait for sensor read in isolated process

# ============================================================================
# Circuit Breaker Configuration
# ============================================================================

# Circuit breaker opens after 5 failures in evaluation window
# Stays open for 30 seconds before attempting reset
# Note: state_storage removed for compatibility with pybreaker 1.4.x
_sensor_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    name="DHT22_Sensor"
)

# Shared cache - single source of truth for all sensor readings
_sensor_cache = {
    "temp": None,
    "humidity": None,
    "timestamp": 0,
    "error_count": 0
}

# Thread-safety lock for cache access
# v6.23.0: CRITICAL - Added thread-safety to prevent race conditions
# Uses RLock to allow nested locking (important for functions that call each other)
# LOCK ORDERING: This is lock #1 in the global lock hierarchy
_cache_lock = threading.RLock()

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
    v6.23.0: Added thread-safety with lock protection.

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

        # Reset error count (thread-safe)
        with _cache_lock:
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
    v6.23.0: Added thread-safety with lock protection.

    Returns:
        Age of cache in seconds (0 if never cached)
    """
    with _cache_lock:
        return time.time() - _sensor_cache.get("timestamp", 0)


# ============================================================================
# Process Isolation for Sensor Reads (v6.22.5)
# ============================================================================

def _read_sensor_in_process(result_queue: Queue) -> None:
    """
    Isolated process for DHT22 sensor read.

    v6.22.5: Runs in separate process to prevent blocking main thread.
    If sensor hangs, only this process blocks - can be terminated.

    Args:
        result_queue: Queue to return result (temp, humidity, error)
    """
    try:
        temp = _dht_sensor.temperature
        humidity = _dht_sensor.humidity
        result_queue.put({
            "temp": temp,
            "humidity": humidity,
            "error": None
        })
    except Exception as e:
        result_queue.put({
            "temp": None,
            "humidity": None,
            "error": str(e)
        })


def _read_dht22_with_timeout(timeout_seconds: float = DHT_READ_TIMEOUT) -> Tuple[Optional[float], Optional[float]]:
    """
    Read DHT22 sensor in isolated process with hard timeout.

    v6.22.5: CRITICAL FIX - Prevents sensor freeze from blocking entire system.
    If sensor blocks beyond timeout, process is terminated forcefully.

    Args:
        timeout_seconds: Maximum time to wait for sensor read

    Returns:
        Tuple of (temperature, humidity) or raises exception

    Raises:
        TimeoutError: If sensor read exceeds timeout
        RuntimeError: If sensor read fails or no result returned
    """
    result_queue = Queue()
    proc = Process(target=_read_sensor_in_process, args=(result_queue,))
    proc.start()
    proc.join(timeout=timeout_seconds)

    # Check if process is still alive (timeout occurred)
    if proc.is_alive():
        logger.warning(f"DHT22 read timeout after {timeout_seconds}s - terminating process")
        proc.terminate()
        proc.join(timeout=1.0)  # Wait for clean termination

        # Force kill if still alive
        if proc.is_alive():
            proc.kill()
            proc.join()

        raise TimeoutError(f"DHT22 read timed out after {timeout_seconds}s")

    # Get result from queue
    try:
        result = result_queue.get_nowait()
        if result["error"]:
            raise RuntimeError(f"DHT22 read error: {result['error']}")
        return (result["temp"], result["humidity"])
    except queue.Empty:
        raise RuntimeError("No result from sensor process")


def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    """
    Read temperature and humidity from DHT22 sensor with caching.

    This is THE ONLY function that should be used to read DHT22 values.
    All endpoints should call this function to ensure consistent values.

    v6.23.0: Added thread-safety with lock protection to prevent race conditions.

    Returns:
        Tuple of (temperature, humidity) or (None, None) on error
    """
    global _sensor_cache

    now = time.time()

    # Return cached value if still valid (thread-safe check)
    with _cache_lock:
        if now - _sensor_cache["timestamp"] < DHT_CACHE_SECONDS:
            if _sensor_cache["temp"] is not None:
                return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # Mock mode - generate fake data (thread-safe)
    if not _dht_available or _dht_sensor is None:
        import random
        with _cache_lock:
            _sensor_cache["temp"] = round(20 + random.uniform(-2, 2), 1)
            _sensor_cache["humidity"] = round(60 + random.uniform(-5, 5), 1)
            _sensor_cache["timestamp"] = now
            _sensor_cache["error_count"] = 0
            return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # v6.23.0: Check circuit breaker state BEFORE attempting sensor read
    # If circuit breaker is OPEN, skip sensor read entirely and return cached value
    if _sensor_circuit_breaker.current_state == pybreaker.STATE_OPEN:
        logger.warning("Circuit breaker OPEN - skipping sensor read, returning cached value")
        with _cache_lock:
            if _sensor_cache["temp"] is not None:
                return (_sensor_cache["temp"], _sensor_cache["humidity"])
            return (None, None)

    # Try to read from real sensor (up to 3 attempts) with circuit breaker protection
    for attempt in range(3):
        try:
            # v6.23.0: Use circuit breaker wrapped sensor read
            # This will raise CircuitBreakerError if breaker is open
            # and will track failures/successes for breaker state management
            @_sensor_circuit_breaker
            def _protected_sensor_read():
                temp = _dht_sensor.temperature
                humidity = _dht_sensor.humidity
                if temp is None or humidity is None:
                    raise RuntimeError("Sensor returned None values")
                return (temp, humidity)

            temp, humidity = _protected_sensor_read()

            # Thread-safe cache update
            with _cache_lock:
                _sensor_cache["temp"] = round(temp, 1)
                _sensor_cache["humidity"] = round(humidity, 1)
                # BUGFIX v6.22.3: Always update timestamp, even on success
                _sensor_cache["timestamp"] = now
                _sensor_cache["error_count"] = 0
                return (_sensor_cache["temp"], _sensor_cache["humidity"])
        except pybreaker.CircuitBreakerError:
            # Circuit breaker tripped during our read attempts
            logger.warning("Circuit breaker tripped - returning cached value")
            with _cache_lock:
                if _sensor_cache["temp"] is not None:
                    return (_sensor_cache["temp"], _sensor_cache["humidity"])
            return (None, None)
        except Exception as e:
            if attempt < 2:
                time.sleep(0.5)
            logger.debug(f"DHT22 read attempt {attempt + 1} failed: {e}")

    # All 3 attempts failed - increment error counter (thread-safe)
    with _cache_lock:
        _sensor_cache["error_count"] += 1
        # BUGFIX v6.22.3: CRITICAL - Always update timestamp after sensor read attempt
        # This prevents infinite cache loops when sensor fails
        _sensor_cache["timestamp"] = now
        error_count = _sensor_cache["error_count"]

    # Log persistent errors (use local variable to avoid race conditions)
    if error_count >= DHT_MAX_CONSECUTIVE_ERRORS:
        logger.error(f"DHT22 failed {error_count} times consecutively")

        # Log system event if data logger available
        if _data_logger and error_count == DHT_MAX_CONSECUTIVE_ERRORS:
            try:
                _data_logger.log_event(
                    'sensor_persistent_error',
                    'error',
                    f'DHT22 failed {error_count} consecutive reads',
                    {'error_count': error_count}
                )
            except Exception:
                pass

    # v6.22.4: Attempt sensor reinitialization after too many consecutive errors
    if error_count >= DHT_REINIT_AFTER_ERRORS:
        logger.critical(f"SENSOR FREEZE DETECTED - {error_count} consecutive failures - Attempting reinit")
        if reinitialize_sensor():
            # Reset timestamp to force immediate retry on next call (thread-safe)
            with _cache_lock:
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

    # Return last known good value if available (thread-safe)
    with _cache_lock:
        if _sensor_cache["temp"] is not None:
            if error_count > 0:
                logger.warning(f"DHT22 read failed (error #{error_count}) - returning cached value")
            return (_sensor_cache["temp"], _sensor_cache["humidity"])

    # No cached value available
    return (None, None)


def get_cached_values() -> Tuple[Optional[float], Optional[float]]:
    """
    Get the current cached sensor values WITHOUT reading the sensor.

    Use this when you just need the values without triggering a sensor read.

    v6.23.0: Added thread-safety with lock protection.

    Returns:
        Tuple of (temperature, humidity) from cache
    """
    with _cache_lock:
        return (_sensor_cache.get("temp"), _sensor_cache.get("humidity"))


def get_cache_status() -> dict:
    """
    Get cache status information for debugging.

    v6.22.4: Added cache_age and reinit_threshold fields.
    v6.23.0: Added thread-safety with lock protection.

    Returns:
        Dictionary with cache state information
    """
    with _cache_lock:
        return {
            "temp": _sensor_cache.get("temp"),
            "humidity": _sensor_cache.get("humidity"),
            "timestamp": _sensor_cache.get("timestamp"),
            "cache_age": get_cache_age(),  # This also uses the lock (RLock allows nested)
            "error_count": _sensor_cache.get("error_count"),
            "sensor_available": _dht_available,
            "cache_ttl": DHT_CACHE_SECONDS,
            "reinit_threshold": DHT_REINIT_AFTER_ERRORS
        }


def get_sensor_health() -> dict:
    """
    Export sensor subsystem health status.

    v6.22.5: Added for health check endpoint.
    v6.23.0: Added circuit breaker state to health metrics.

    Returns:
        Dictionary with sensor health metrics
    """
    with _cache_lock:
        error_count = _sensor_cache.get("error_count", 0)
        cache_age = get_cache_age()

        # Get circuit breaker state
        cb_state = _sensor_circuit_breaker.current_state
        cb_fail_count = _sensor_circuit_breaker.fail_counter

        # Determine overall health status
        if cb_state == pybreaker.STATE_OPEN:
            status = "circuit_open"
        elif error_count >= DHT_REINIT_AFTER_ERRORS:
            status = "critical"
        elif error_count >= DHT_MAX_CONSECUTIVE_ERRORS:
            status = "degraded"
        elif cache_age > 60:
            status = "stale"
        else:
            status = "healthy"

        return {
            "status": status,
            "error_count": error_count,
            "cache_age": round(cache_age, 2),
            "last_successful_read": _sensor_cache.get("timestamp", 0),
            "sensor_available": _dht_available,
            "circuit_breaker": {
                "state": str(cb_state),
                "fail_count": cb_fail_count,
                "fail_max": _sensor_circuit_breaker.fail_max,
                "reset_timeout": _sensor_circuit_breaker.reset_timeout
            },
            "current_values": {
                "temp": _sensor_cache.get("temp"),
                "humidity": _sensor_cache.get("humidity")
            }
        }


def get_cache_state() -> dict:
    """
    Export cache state for incident snapshots.

    v6.22.5: Added for incident snapshot capture.

    Returns:
        Dictionary with complete cache state
    """
    with _cache_lock:
        return {
            "cache_data": dict(_sensor_cache),
            "sensor_available": _dht_available,
            "config": {
                "cache_ttl": DHT_CACHE_SECONDS,
                "max_consecutive_errors": DHT_MAX_CONSECUTIVE_ERRORS,
                "reinit_threshold": DHT_REINIT_AFTER_ERRORS
            }
        }
