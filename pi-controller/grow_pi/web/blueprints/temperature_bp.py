#!/usr/bin/env python3
"""
Temperature Blueprint
Provides DHT22 sensor data endpoint with caching.

Endpoints:
    GET /api/temperature - Get current temperature and humidity
"""

from flask import Blueprint, jsonify
import logging
import time
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Create blueprint
temperature_bp = Blueprint('temperature', __name__)

# Try to import DHT22 sensor
DHT_AVAILABLE = False
try:
    import board
    import adafruit_dht
    DHT_AVAILABLE = True
except ImportError:
    logger.warning("adafruit_dht not available - sensor will return mock data")


# ============================================================================
# Shared Instances (injected from api.py)
# ============================================================================

dht_sensor = None


def init_temperature_bp(dht_sensor_instance):
    """Initialize blueprint with DHT sensor instance."""
    global dht_sensor
    dht_sensor = dht_sensor_instance


# ============================================================================
# Helper Functions
# ============================================================================

def create_response(success: bool, data: dict = None, error: str = None) -> dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# Cache for DHT22 readings (sensor needs 2s between reads)
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0}
DHT_CACHE_SECONDS = 3  # Minimum seconds between sensor reads


def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    """Read temperature and humidity from DHT22 with caching and retry"""
    global _dht_cache

    if dht_sensor is None:
        # Return mock data for testing
        import random
        return (22.0 + random.uniform(-2, 2), 60.0 + random.uniform(-5, 5))

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


# ============================================================================
# API Routes
# ============================================================================

@temperature_bp.route('/api/temperature', methods=['GET'])
def get_temperature():
    """Get current temperature and humidity"""
    try:
        temp, humidity = read_dht22()

        if temp is None or humidity is None:
            return jsonify(create_response(False, error="Sensor read failed")), 503

        return jsonify(create_response(True, {
            "temperature": temp,
            "humidity": humidity,
            "unit_temperature": "°C",
            "unit_humidity": "%"
        }))

    except Exception as e:
        logger.error(f"Error in get_temperature: {e}")
        return jsonify(create_response(False, error=str(e))), 500
