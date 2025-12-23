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
import psutil
import time

logger = logging.getLogger(__name__)

# Create blueprint
status_bp = Blueprint('status', __name__)

# ============================================================================
# Health Thresholds
# ============================================================================

CPU_TEMP_NORMAL = 60    # < 60°C
CPU_TEMP_WARNING = 75   # 60-75°C
CPU_TEMP_CRITICAL = 80  # > 75°C

MEMORY_NORMAL = 70      # < 70%
MEMORY_WARNING = 85     # 70-85%
MEMORY_CRITICAL = 95    # > 85%

DISK_NORMAL = 70        # < 70%
DISK_WARNING = 85       # 70-85%
DISK_CRITICAL = 95      # > 85%

# Cache for system metrics (30s TTL)
_system_metrics_cache = None
_cache_timestamp = 0
_cache_ttl = 30  # seconds


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


def get_cpu_temperature() -> Optional[float]:
    """
    Read CPU temperature from thermal zone.

    Returns:
        Temperature in Celsius or None if not available
    """
    try:
        # Raspberry Pi thermal zone path
        with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
            temp_raw = f.read().strip()
            return float(temp_raw) / 1000.0
    except (FileNotFoundError, PermissionError, ValueError) as e:
        # Not on Raspberry Pi or no permission (dev environment)
        logger.debug(f"CPU temp not available: {e}")
        return None


def get_status_from_value(value: float, normal: float, warning: float, critical: float) -> str:
    """
    Determine status based on thresholds.

    Args:
        value: Current metric value
        normal: Normal threshold
        warning: Warning threshold
        critical: Critical threshold

    Returns:
        Status string: "normal", "warning", or "critical"
    """
    if value >= critical:
        return "critical"
    elif value >= warning:
        return "warning"
    else:
        return "normal"


def get_system_metrics() -> Dict:
    """
    Collect system health metrics with caching.

    Returns:
        Dictionary with CPU temp, load, memory, disk, and uptime
    """
    global _system_metrics_cache, _cache_timestamp

    # Check cache validity
    current_time = time.time()
    if _system_metrics_cache and (current_time - _cache_timestamp) < _cache_ttl:
        return _system_metrics_cache

    # Collect fresh metrics
    cpu_temp = get_cpu_temperature()
    cpu_load = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    boot_time = psutil.boot_time()
    uptime_seconds = int(current_time - boot_time)

    metrics = {
        "cpu_temp": round(cpu_temp, 1) if cpu_temp else None,
        "cpu_temp_status": get_status_from_value(cpu_temp, CPU_TEMP_NORMAL, CPU_TEMP_WARNING, CPU_TEMP_CRITICAL) if cpu_temp else "unknown",
        "cpu_load": round(cpu_load, 1),
        "memory_percent": round(memory.percent, 1),
        "memory_status": get_status_from_value(memory.percent, MEMORY_NORMAL, MEMORY_WARNING, MEMORY_CRITICAL),
        "disk_percent": round(disk.percent, 1),
        "disk_status": get_status_from_value(disk.percent, DISK_NORMAL, DISK_WARNING, DISK_CRITICAL),
        "uptime_seconds": uptime_seconds
    }

    # Update cache
    _system_metrics_cache = metrics
    _cache_timestamp = current_time

    return metrics


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
        from ..dependencies import get_lamp_channels, get_pwm_controller, get_data_logger, get_api_version
        # BUGFIX v6.22.2: Use shared sensor cache for consistent values
        from ...utils.sensor_cache import read_dht22

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

        # Get sensor data - use shared sensor cache for consistency
        temp, humidity = read_dht22()

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
    Health check endpoint to verify component availability and system health.

    Returns:
        JSON response with:
        - status: Overall health status ("healthy", "warning", or "critical")
        - version: API version
        - pwm_available: Whether PWM controller is initialized
        - sensor_available: Whether DHT22 sensor is available
        - logging_available: Whether database logging is available
        - logging_running: Whether data logger is actively running
        - curves_available: Whether curve controller is available
        - system: System health metrics (CPU temp, RAM, disk, uptime)

    Example Response:
        {
            "status": "healthy",
            "version": "6.21.0",
            "pwm_available": true,
            "sensor_available": true,
            "logging_available": true,
            "logging_running": true,
            "curves_available": true,
            "system": {
                "cpu_temp": 52.3,
                "cpu_temp_status": "normal",
                "cpu_load": 45.2,
                "memory_percent": 62.1,
                "memory_status": "normal",
                "disk_percent": 78.5,
                "disk_status": "warning",
                "uptime_seconds": 345678
            }
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

        # Collect system metrics
        system_metrics = get_system_metrics()

        # Determine overall status based on system health
        overall_status = "healthy"
        if system_metrics.get("cpu_temp_status") == "critical" or \
           system_metrics.get("memory_status") == "critical" or \
           system_metrics.get("disk_status") == "critical":
            overall_status = "critical"
        elif system_metrics.get("cpu_temp_status") == "warning" or \
             system_metrics.get("memory_status") == "warning" or \
             system_metrics.get("disk_status") == "warning":
            overall_status = "warning"

        return jsonify({
            "status": overall_status,
            "version": get_api_version(),
            "pwm_available": pwm_controller is not None,
            "sensor_available": dht_sensor is not None or not is_dht_available(),
            "logging_available": is_db_available() and data_logger is not None,
            "logging_running": data_logger._running if data_logger else False,
            "curves_available": is_curve_available() and curve_controller is not None,
            "system": system_metrics
        })

    except Exception as e:
        logger.error(f"Error in health_check: {e}")
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500
