#!/usr/bin/env python3
"""
Lamps Blueprint
Handles lamp control endpoints.

Endpoints:
    POST /api/lamp/<channel> - Set lamp intensity (0-100)
"""

from flask import Blueprint, jsonify, request
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Blueprint definition
lamps_bp = Blueprint('lamps', __name__)

# Module-level references (will be injected by main app)
_pwm_controller = None
_lamp_channels = {}
_data_logger = None


def init_lamps_blueprint(pwm_controller, lamp_channels: Dict, data_logger=None):
    """Initialize blueprint with dependencies"""
    global _pwm_controller, _lamp_channels, _data_logger
    _pwm_controller = pwm_controller
    _lamp_channels = lamp_channels
    _data_logger = data_logger
    logger.info("Lamps blueprint initialized")


def create_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# Routes
# ============================================================================

@lamps_bp.route('/api/lamp/<int:channel>', methods=['POST'])
def set_lamp(channel: int):
    """Set intensity for a specific lamp channel

    Request body:
        {
            "intensity": 0-100
        }

    Response:
        {
            "success": true,
            "channel": 1,
            "name": "Far Red",
            "intensity": 50
        }
    """
    try:
        # Validate channel
        if channel not in _lamp_channels:
            return jsonify(create_response(False, error=f"Invalid channel: {channel}. Must be 1-4")), 400

        # Check PWM controller
        if _pwm_controller is None:
            return jsonify(create_response(False, error="PWM controller not available")), 503

        # Parse request
        if not request.is_json:
            return jsonify(create_response(False, error="Request must be JSON")), 400

        data = request.get_json()
        intensity = data.get('intensity')

        if intensity is None:
            return jsonify(create_response(False, error="Missing 'intensity' parameter")), 400

        # Validate intensity
        try:
            intensity = int(intensity)
        except (TypeError, ValueError):
            return jsonify(create_response(False, error="Intensity must be an integer")), 400

        if not 0 <= intensity <= 100:
            return jsonify(create_response(False, error="Intensity must be 0-100")), 400

        # Set lamp intensity
        _pwm_controller.set_intensity(channel, intensity)
        logger.info(f"Set lamp {channel} ({_lamp_channels[channel].name}) to {intensity}%")

        # Log the change (source: 'api' indicates manual control)
        if _data_logger:
            _data_logger.log_lamp_change(
                channel=channel,
                name=_lamp_channels[channel].name,
                intensity=intensity,
                source='api'
            )

        return jsonify(create_response(True, {
            "channel": channel,
            "name": _lamp_channels[channel].name,
            "intensity": intensity
        }))

    except Exception as e:
        logger.error(f"Error in set_lamp: {e}")
        return jsonify(create_response(False, error=str(e))), 500
