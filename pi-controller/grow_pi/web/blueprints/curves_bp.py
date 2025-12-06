#!/usr/bin/env python3
"""
Curves Blueprint
Handles all lamp curve-related API endpoints.

Endpoints:
    GET  /api/curves                - Get all lamp curves
    GET  /api/curves/<channel>      - Get curve for specific channel
    PUT  /api/curves/<channel>      - Update curve for specific channel
    GET  /api/curves/preview        - Get 24h preview of all curves
    GET  /api/curves/intensities    - Get current interpolated intensities
"""

from flask import Blueprint, jsonify, request
from typing import Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Create blueprint
curves_bp = Blueprint('curves', __name__)

# Module-level references (initialized by init_blueprint)
_curve_controller = None
_data_logger = None
_lamp_channels = None


def init_blueprint(curve_controller, data_logger=None, lamp_channels=None):
    """Initialize blueprint with dependencies."""
    global _curve_controller, _data_logger, _lamp_channels
    _curve_controller = curve_controller
    _data_logger = data_logger
    _lamp_channels = lamp_channels or {}


def create_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# Curve API Routes
# ============================================================================

@curves_bp.route('/api/curves', methods=['GET'])
def get_all_curves():
    """Get all lamp curves"""
    if not _curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        curves = []
        for channel in range(1, 5):
            curve_data = _curve_controller.get_curve(channel)
            curves.append({
                "channel": channel,
                "name": _curve_controller.get_channel_name(channel),
                "enabled": _curve_controller.is_enabled(channel),
                "curve": curve_data or [],
                "current_intensity": _curve_controller.get_intensity(channel)
            })

        return jsonify(create_response(True, {
            "curves": curves,
            "status": _curve_controller.get_status()
        }))

    except Exception as e:
        logger.error(f"Error in get_all_curves: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@curves_bp.route('/api/curves/<int:channel>', methods=['GET'])
def get_curve(channel: int):
    """Get curve for a specific channel"""
    if not _curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    if _lamp_channels and channel not in _lamp_channels:
        return jsonify(create_response(False, error=f"Invalid channel: {channel}")), 400

    try:
        curve_data = _curve_controller.get_curve(channel)
        return jsonify(create_response(True, {
            "channel": channel,
            "name": _curve_controller.get_channel_name(channel),
            "enabled": _curve_controller.is_enabled(channel),
            "curve": curve_data or [],
            "current_intensity": _curve_controller.get_intensity(channel)
        }))

    except Exception as e:
        logger.error(f"Error in get_curve: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@curves_bp.route('/api/curves/<int:channel>', methods=['PUT'])
def update_curve(channel: int):
    """Update curve for a specific channel"""
    if not _curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    if _lamp_channels and channel not in _lamp_channels:
        return jsonify(create_response(False, error=f"Invalid channel: {channel}")), 400

    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        curve_points = data.get('curve', [])
        enabled = data.get('enabled', True)

        # Validate curve points
        for point in curve_points:
            if 'time' not in point or 'intensity' not in point:
                return jsonify(create_response(False, error="Each point needs 'time' and 'intensity'")), 400
            if not isinstance(point['intensity'], (int, float)) or not 0 <= point['intensity'] <= 100:
                return jsonify(create_response(False, error="Intensity must be 0-100")), 400

        # Update curve
        success = _curve_controller.update_curve(channel, curve_points, enabled)
        if not success:
            return jsonify(create_response(False, error="Failed to update curve")), 500

        # Log the change
        if _data_logger:
            _data_logger.log_event(
                'curve_update',
                'info',
                f'Curve updated for {_curve_controller.get_channel_name(channel)}',
                {'channel': channel, 'points': len(curve_points), 'enabled': enabled}
            )

        logger.info(f"Updated curve for channel {channel}: {len(curve_points)} points")

        return jsonify(create_response(True, {
            "channel": channel,
            "name": _curve_controller.get_channel_name(channel),
            "enabled": enabled,
            "curve": curve_points,
            "current_intensity": _curve_controller.get_intensity(channel)
        }))

    except Exception as e:
        logger.error(f"Error in update_curve: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@curves_bp.route('/api/curves/preview', methods=['GET'])
def get_curve_preview():
    """Get 24h preview of all curve intensities"""
    if not _curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        preview = []
        for hour in range(24):
            test_time = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            intensities = _curve_controller.get_current_intensities(test_time)
            preview.append({
                "hour": hour,
                "time": f"{hour:02d}:00",
                "intensities": intensities
            })

        return jsonify(create_response(True, {
            "preview": preview,
            "channels": {
                ch: _curve_controller.get_channel_name(ch)
                for ch in range(1, 5)
            }
        }))

    except Exception as e:
        logger.error(f"Error in get_curve_preview: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@curves_bp.route('/api/curves/intensities', methods=['GET'])
def get_current_intensities():
    """Get current interpolated intensities for all channels"""
    if not _curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        intensities = _curve_controller.get_current_intensities()
        return jsonify(create_response(True, {
            "intensities": intensities,
            "channels": {
                ch: {
                    "name": _curve_controller.get_channel_name(ch),
                    "enabled": _curve_controller.is_enabled(ch),
                    "intensity": intensities.get(ch, 0)
                }
                for ch in range(1, 5)
            },
            "timestamp": datetime.now().isoformat()
        }))

    except Exception as e:
        logger.error(f"Error in get_current_intensities: {e}")
        return jsonify(create_response(False, error=str(e))), 500
