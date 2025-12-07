"""
Hardware Service Layer

Abstracts hardware interactions (PWM Controller, DHT22 Sensor) from Flask blueprints.
Provides singleton access and caching for sensor readings.
"""

import logging
import time
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Try to import hardware modules
PWM_AVAILABLE = False
DHT_AVAILABLE = False
dht_sensor = None

try:
    from ...lamps.pwm_controller import PWMController, get_pwm_controller
    PWM_AVAILABLE = True
except ImportError:
    logger.warning("PWMController not available")

try:
    import board
    import adafruit_dht
    DHT_AVAILABLE = True
except ImportError:
    logger.warning("adafruit_dht not available - sensor will return mock data")


# ============================================================================
# PWM Controller Service
# ============================================================================

def get_pwm_service() -> Optional['PWMController']:
    """
    Get the global PWM Controller singleton.

    Returns:
        PWMController instance or None if not available
    """
    if not PWM_AVAILABLE:
        return None

    try:
        return get_pwm_controller()
    except Exception as e:
        logger.error(f"Failed to get PWM controller: {e}")
        return None


def initialize_pwm(channels_config: list) -> bool:
    """
    Initialize PWM controller with channel configuration.

    Args:
        channels_config: List of channel configurations

    Returns:
        True if initialization successful
    """
    controller = get_pwm_service()
    if not controller:
        logger.error("PWM controller not available")
        return False

    if controller._initialized:
        logger.debug("PWM controller already initialized")
        return True

    try:
        return controller.initialize(channels_config)
    except Exception as e:
        logger.error(f"Failed to initialize PWM: {e}")
        return False


def set_lamp_intensity(channel: int, intensity: int) -> bool:
    """
    Set intensity for a specific lamp channel.

    Args:
        channel: Channel number (1-4)
        intensity: Intensity percentage (0-100)

    Returns:
        True if successful
    """
    controller = get_pwm_service()
    if not controller:
        return False

    return controller.set_intensity(channel, intensity)


def get_lamp_state() -> Dict[int, int]:
    """
    Get current intensity of all lamp channels.

    Returns:
        Dict mapping channel number to intensity
    """
    controller = get_pwm_service()
    if not controller:
        return {}

    return controller.get_current_state()


def set_all_lamps(intensities: Dict[int, int]) -> None:
    """
    Set intensities for multiple channels at once.

    Args:
        intensities: Dict mapping channel to intensity
    """
    controller = get_pwm_service()
    if controller:
        controller.set_all_intensities(intensities)


# ============================================================================
# DHT22 Sensor Service
# ============================================================================

# Cache for DHT22 readings (sensor needs 2s between reads)
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0}
DHT_CACHE_SECONDS = 30  # Minimum seconds between sensor reads (erhöht für CPU-Optimierung)


def initialize_dht22() -> bool:
    """
    Initialize DHT22 sensor on GPIO 4.

    Returns:
        True if initialization successful
    """
    global dht_sensor

    if not DHT_AVAILABLE:
        logger.warning("DHT22 hardware not available - will use mock data")
        return True  # Return True since mock mode works

    if dht_sensor is not None:
        logger.debug("DHT22 already initialized")
        return True

    try:
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        logger.info("DHT22 Sensor initialized on GPIO-4")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize DHT22: {e}")
        return False


def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    """
    Read temperature and humidity from DHT22 with caching and retry logic.

    Returns:
        Tuple of (temperature, humidity) in (°C, %)
        Returns (None, None) if all retries fail
    """
    global _dht_cache

    if dht_sensor is None:
        # Return mock data for testing
        import random
        temp = round(22.0 + random.uniform(-2, 2), 1)
        humidity = round(60.0 + random.uniform(-5, 5), 1)
        return (temp, humidity)

    # Return cached value if recent enough
    now = time.time()
    if now - _dht_cache["timestamp"] < DHT_CACHE_SECONDS:
        if _dht_cache["temp"] is not None:
            return (_dht_cache["temp"], _dht_cache["humidity"])

    # Try up to 3 times to read the sensor
    for attempt in range(3):
        try:
            temp = dht_sensor.temperature
            humidity = dht_sensor.humidity

            if temp is not None and humidity is not None:
                _dht_cache["temp"] = round(temp, 1)
                _dht_cache["humidity"] = round(humidity, 1)
                _dht_cache["timestamp"] = now
                return (_dht_cache["temp"], _dht_cache["humidity"])

        except RuntimeError as e:
            logger.warning(f"DHT22 read attempt {attempt+1}/3: {e}")
            if attempt < 2:
                time.sleep(0.5)

    # Return last known good value if available
    if _dht_cache["temp"] is not None:
        logger.info("Returning cached DHT22 value")
        return (_dht_cache["temp"], _dht_cache["humidity"])

    return (None, None)


def clear_dht_cache() -> None:
    """Clear the DHT22 sensor cache (useful for testing)."""
    global _dht_cache
    _dht_cache = {"temp": None, "humidity": None, "timestamp": 0}
    logger.debug("DHT22 cache cleared")
