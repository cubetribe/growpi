# Sensor Freeze Fix v6.22.4 - Implementation Report

**Date:** 2025-12-23
**Agent:** @builder
**Version:** 6.22.4

---

## Summary

Implemented comprehensive fixes to prevent sensor freeze issues in the GrowPi system. The root cause was multiple code paths reading directly from `temperature_bp.read_dht22()` instead of using the shared `sensor_cache`, causing inconsistent state and potential deadlocks.

---

## Files Modified

### 1. `/pi-controller/grow_pi/web/app.py` (Factory)

#### Fix 1: humidity_reader in _register_blueprints() (Lines 443-455)

**Before:**
```python
# Set humidity reader function
def humidity_reader():
    """Read humidity from DHT22 sensor"""
    if app.dht_sensor is None:
        import random
        return 60.0 + random.uniform(-5, 5)

    from .blueprints.temperature_bp import read_dht22 as bp_read_dht22
    _, humidity = bp_read_dht22()
    return humidity
```

**After:**
```python
# Set humidity reader function
# BUGFIX v6.22.4: Use sensor_cache instead of temperature_bp to prevent freeze
def humidity_reader():
    """Read humidity from DHT22 sensor via shared cache"""
    try:
        from grow_pi.utils.sensor_cache import read_dht22
    except ImportError:
        from ..utils.sensor_cache import read_dht22
    _, humidity = read_dht22()
    return humidity
```

#### Fix 2: DataLogger sensor_reader in run_server() (Lines 508-516)

**Before:**
```python
# Define sensor reader function
def read_dht22():
    """Read DHT22 sensor with caching"""
    if app.dht_sensor is None:
        # Return mock data
        import random
        return (22.0 + random.uniform(-2, 2), 60.0 + random.uniform(-5, 5))

    # Use the sensor reader from temperature blueprint
    from .blueprints.temperature_bp import read_dht22 as bp_read_dht22
    return bp_read_dht22()
```

**After:**
```python
# Define sensor reader function
# BUGFIX v6.22.4: Use sensor_cache instead of temperature_bp to prevent freeze
def read_dht22():
    """Read DHT22 sensor with caching via shared cache"""
    try:
        from grow_pi.utils.sensor_cache import read_dht22 as cache_read_dht22
    except ImportError:
        from ..utils.sensor_cache import read_dht22 as cache_read_dht22
    return cache_read_dht22()
```

---

### 2. `/pi-controller/grow_pi/web/dependencies.py`

#### Fix: get_dht_reader() function (Lines 163-184)

**Before:**
```python
def get_dht_reader() -> Callable[[], Tuple[Optional[float], Optional[float]]]:
    """..."""
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
```

**After:**
```python
def get_dht_reader() -> Callable[[], Tuple[Optional[float], Optional[float]]]:
    """
    BUGFIX v6.22.4: Use shared sensor_cache instead of direct sensor access
    to ensure consistent values and prevent sensor freeze issues.
    """
    # Always use sensor_cache for consistent readings
    def read_from_cache():
        try:
            try:
                from grow_pi.utils.sensor_cache import read_dht22
            except ImportError:
                from ..utils.sensor_cache import read_dht22
            return read_dht22()
        except Exception as e:
            logger.error(f"DHT22 cache read error: {e}")
            return (None, None)
    return read_from_cache
```

---

### 3. `/pi-controller/grow_pi/utils/sensor_cache.py`

#### Enhancement A: Reduced Cache TTL

**Before:**
```python
DHT_CACHE_SECONDS = 30  # Cache sensor readings for 30 seconds
```

**After:**
```python
DHT_CACHE_SECONDS = 10  # v6.22.4: Reduced from 30 to 10 seconds for fresher data
```

#### Enhancement B: Added Reinit Threshold Constant

```python
DHT_REINIT_AFTER_ERRORS = 20  # v6.22.4: Reinitialize sensor after this many consecutive failures
```

#### Enhancement C: New `reinitialize_sensor()` Function

```python
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
```

#### Enhancement D: New `get_cache_age()` Function

```python
def get_cache_age() -> float:
    """
    Get the age of the cached sensor values in seconds.

    v6.22.4: Added for monitoring cache freshness.

    Returns:
        Age of cache in seconds (0 if never cached)
    """
    return time.time() - _sensor_cache.get("timestamp", 0)
```

#### Enhancement E: Automatic Reinit Trigger in `read_dht22()`

Added after error logging:
```python
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
```

#### Enhancement F: Extended `get_cache_status()` Response

Added `cache_age` and `reinit_threshold` fields to the status response.

---

## Files NOT Modified (Already Correct)

### `/pi-controller/grow_pi/web/api.py`

The `_get_dehumidifier()` function at line 1132-1144 was already fixed in v6.22.3:

```python
def _get_dehumidifier():
    """Get or initialize dehumidifier controller with humidity reader."""
    global dehumidifier_controller
    if DEHUMIDIFIER_AVAILABLE and dehumidifier_controller is None:
        dehumidifier_controller = get_dehumidifier_controller()
        # Set humidity reader (using shared sensor cache)
        def humidity_reader():
            # BUGFIX v6.22.3: Use sensor_cache instead of temperature_bp.read_dht22()
            from grow_pi.utils.sensor_cache import read_dht22
            _, humidity = read_dht22()
            return humidity
        dehumidifier_controller.set_humidity_reader(humidity_reader)
    return dehumidifier_controller
```

---

## Architecture After Fix

```
                     SINGLE SOURCE OF TRUTH
                              |
                              v
                    +-------------------+
                    |   sensor_cache    |
                    |   read_dht22()    |
                    +-------------------+
                              ^
          ____________________|_____________________
         |          |          |          |         |
    app.py      api.py     deps.py    temp_bp   status_bp
   (factory)              humidity
                          _reader
```

All code paths now use `sensor_cache.read_dht22()`:
- DataLogger sensor_reader
- Dehumidifier humidity_reader
- dependencies.get_dht_reader()
- All API endpoints via blueprints

---

## Verification Checklist

- [x] `app.py` factory: humidity_reader uses sensor_cache
- [x] `app.py` factory: DataLogger sensor_reader uses sensor_cache
- [x] `dependencies.py`: get_dht_reader() uses sensor_cache
- [x] `sensor_cache.py`: Cache TTL reduced from 30s to 10s
- [x] `sensor_cache.py`: reinitialize_sensor() function added
- [x] `sensor_cache.py`: get_cache_age() function added
- [x] `sensor_cache.py`: Auto-reinit trigger after 20 consecutive errors
- [x] `sensor_cache.py`: get_cache_status() extended with new fields
- [x] `api.py`: _get_dehumidifier() already correct (v6.22.3)

---

## Next Steps

1. **Test locally** - Verify no import errors
2. **Deploy to Pi** - Update the running service
3. **Monitor logs** - Watch for "SENSOR FREEZE DETECTED" messages
4. **Validate** - Hand off to @validator for cross-file consistency check

---

## Git Diff Summary

```
Modified files:
 M pi-controller/grow_pi/web/app.py
 M pi-controller/grow_pi/web/dependencies.py
 M pi-controller/grow_pi/utils/sensor_cache.py
```

Total changes:
- 3 files modified
- ~80 lines added/changed
- 0 files created
- 0 files deleted
