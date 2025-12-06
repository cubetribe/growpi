#!/usr/bin/env python3
"""
Dehumidifier Blueprint - Room Climate Control API
Provides endpoints for dehumidifier control and room status monitoring.

Endpoints:
    GET  /api/room                 - Get room status (temp, humidity, dehumidifier)
    GET  /api/room/config          - Get dehumidifier configuration
    POST /api/room/config          - Update dehumidifier configuration
    POST /api/room/dehumidifier    - Manual dehumidifier control (on/off)
"""

from flask import Blueprint, jsonify, request
import logging
from datetime import datetime

dehumidifier_bp = Blueprint('dehumidifier', __name__)
logger = logging.getLogger(__name__)


# ============================================================================
# Module-level variables
# ============================================================================

# Will be set via dependency injection from app.py
_dehumidifier_controller = None
_humidity_reader = None


def set_dehumidifier_controller(controller):
    """Set dehumidifier controller instance (DI)"""
    global _dehumidifier_controller
    _dehumidifier_controller = controller


def set_humidity_reader(reader_func):
    """Set humidity reader function (DI)"""
    global _humidity_reader
    _humidity_reader = reader_func


def _get_dehumidifier():
    """Get dehumidifier controller instance"""
    return _dehumidifier_controller


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


# ============================================================================
# API Routes
# ============================================================================

@dehumidifier_bp.route('/api/room', methods=['GET'])
def get_room_status():
    """Get room status including temperature, humidity, and dehumidifier state"""
    try:
        # Read temperature and humidity
        temp = None
        humidity = None
        if _humidity_reader:
            try:
                temp, humidity = _humidity_reader()
            except TypeError:
                # If reader returns only humidity
                humidity = _humidity_reader()

        response_data = {
            "temperature": temp,
            "humidity": humidity,
            "timestamp": datetime.now().isoformat()
        }

        # Add dehumidifier status if available
        controller = _get_dehumidifier()
        if controller:
            response_data["dehumidifier"] = controller.get_status()
        else:
            response_data["dehumidifier"] = {"available": False}

        return jsonify(create_response(True, response_data))

    except Exception as e:
        logger.error(f"Error in get_room_status: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@dehumidifier_bp.route('/api/room/config', methods=['GET'])
def get_room_config():
    """Get room/dehumidifier configuration"""
    controller = _get_dehumidifier()
    if not controller:
        return jsonify(create_response(False, error="Dehumidifier not available")), 503

    try:
        return jsonify(create_response(True, {
            "config": controller.get_config()
        }))
    except Exception as e:
        logger.error(f"Error in get_room_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@dehumidifier_bp.route('/api/room/config', methods=['POST'])
def update_room_config():
    """Update dehumidifier configuration"""
    controller = _get_dehumidifier()
    if not controller:
        return jsonify(create_response(False, error="Dehumidifier not available")), 503

    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()

        updated = controller.update_config(
            enabled=data.get('enabled'),
            target=data.get('target'),
            threshold_high=data.get('threshold_high'),
            threshold_low=data.get('threshold_low'),
            min_run_time=data.get('min_run_time'),
            min_off_time=data.get('min_off_time'),
            schedule_enabled=data.get('schedule_enabled'),
            schedule_start_time=data.get('schedule_start_time'),
            schedule_duration_minutes=data.get('schedule_duration_minutes')
        )

        logger.info(f"Room config updated: {updated}")

        # If auto mode was just enabled, immediately run check_and_control
        # This ensures the dehumidifier state matches the current humidity
        control_result = None
        if data.get('enabled') is True:
            control_result = controller.check_and_control()
            if control_result is not None:
                logger.info(f"Auto-control triggered: {'ON' if control_result else 'OFF'}")

        return jsonify(create_response(True, {
            "config": updated,
            "message": "Configuration updated",
            "auto_control_applied": control_result
        }))

    except Exception as e:
        logger.error(f"Error in update_room_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@dehumidifier_bp.route('/api/room/dehumidifier', methods=['POST'])
def control_dehumidifier():
    """Manually control dehumidifier (on/off)"""
    controller = _get_dehumidifier()
    if not controller:
        return jsonify(create_response(False, error="Dehumidifier not available")), 503

    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        action = data.get('action')

        if action == 'on':
            success = controller.switch_on()
            message = "Dehumidifier turned ON" if success else "Failed to turn ON"
        elif action == 'off':
            success = controller.switch_off()
            message = "Dehumidifier turned OFF" if success else "Failed to turn OFF"
        else:
            return jsonify(create_response(False, error="Action must be 'on' or 'off'")), 400

        return jsonify(create_response(success, {
            "action": action,
            "message": message,
            "status": controller.get_status()
        }))

    except Exception as e:
        logger.error(f"Error in control_dehumidifier: {e}")
        return jsonify(create_response(False, error=str(e))), 500
