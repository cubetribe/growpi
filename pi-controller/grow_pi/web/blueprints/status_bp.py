#!/usr/bin/env python3
"""
Status & Health Blueprint
Provides system status and health check endpoints.

Endpoints:
    GET /api/status  - Get all lamp values, sensor data, and system info
    GET /api/health  - Health check with component availability
"""

from flask import Blueprint, jsonify, request
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
status_bp = Blueprint('status', __name__)


# ============================================================================
# Helper Functions
# ============================================================================

def create_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """
    Create standardized API response.

    Args:
        success: Whether the request was successful
        data: Optional data dictionary to include in response
        error: Optional error message

    Returns:
        Dict containing success status, data, and/or error message
    """
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# API Routes
# ============================================================================

@status_bp.route('/status', methods=['GET'])
def get_status():
    """
    Get current system status including all lamp intensities and sensor data.

    Returns:
        JSON response with:
        - lamps: List of lamp states (channel, name, intensity, color)
        - temperature: Current temperature in °C (or None)
        - humidity: Current humidity in % (or None)
        - timestamp: ISO-format timestamp
        - version: API version
        - logging_enabled: Whether data logging is active

    Example Response:
        {
            "success": true,
            "lamps": [
                {"channel": 1, "name": "Far Red", "intensity": 75, "color": "#ff4444"},
                {"channel": 2, "name": "Warm White", "intensity": 60, "color": "#ffbb44"},
                ...
            ],
            "temperature": 22.5,
            "humidity": 60.2,
            "timestamp": "2025-12-06T10:30:45.123456",
            "version": "1.2.0",
            "logging_enabled": true
        }
    """
    try:
        from ..dependencies import get_lamp_channels, get_pwm_controller, get_dht_reader, get_data_logger, get_api_version

        # Get lamp channels config
        lamp_channels = get_lamp_channels()

        # Get lamp intensities
        lamps: List[Dict] = []
        pwm_controller = get_pwm_controller()

        for channel_id, config in lamp_channels.items():
            intensity = 0
            if pwm_controller:
                state = pwm_controller.get_current_state()
                intensity = state.get(channel_id, 0)

            lamps.append({
                "channel": config.id,
                "name": config.name,
                "intensity": intensity,
                "color": config.color
            })

        # Get sensor data
        dht_reader = get_dht_reader()
        temp, humidity = dht_reader()

        # Check logging status
        data_logger = get_data_logger()
        logging_enabled = data_logger is not None and data_logger._running

        return jsonify(create_response(True, {
            "lamps": lamps,
            "temperature": temp,
            "humidity": humidity,
            "timestamp": datetime.now().isoformat(),
            "version": get_api_version(),
            "logging_enabled": logging_enabled
        }))

    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@status_bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint to verify component availability.

    Returns:
        JSON response with:
        - status: Overall health status ("healthy")
        - version: API version
        - pwm_available: Whether PWM controller is initialized
        - sensor_available: Whether DHT22 sensor is available
        - logging_available: Whether database logging is available
        - logging_running: Whether data logger is actively running
        - curves_available: Whether curve controller is available

    Example Response:
        {
            "status": "healthy",
            "version": "1.2.0",
            "pwm_available": true,
            "sensor_available": true,
            "logging_available": true,
            "logging_running": true,
            "curves_available": true
        }
    """
    try:
        from ..dependencies import (
            get_pwm_controller,
            get_dht_sensor,
            get_data_logger,
            get_curve_controller,
            get_api_version,
            is_dht_available,
            is_db_available,
            is_curve_available
        )

        pwm_controller = get_pwm_controller()
        dht_sensor = get_dht_sensor()
        data_logger = get_data_logger()
        curve_controller = get_curve_controller()

        return jsonify({
            "status": "healthy",
            "version": get_api_version(),
            "pwm_available": pwm_controller is not None,
            "sensor_available": dht_sensor is not None or not is_dht_available(),
            "logging_available": is_db_available() and data_logger is not None,
            "logging_running": data_logger._running if data_logger else False,
            "curves_available": is_curve_available() and curve_controller is not None
        })

    except Exception as e:
        logger.error(f"Error in health_check: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
