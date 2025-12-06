#!/usr/bin/env python3
"""
Mode Blueprint
Handles operating mode management (auto/manual).

Endpoints:
    GET  /api/mode - Get current operating mode
    POST /api/mode - Set operating mode (auto/manual)
"""

from flask import Blueprint, jsonify, request
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Blueprint definition
mode_bp = Blueprint('mode', __name__)

# Module-level references (will be injected by main app)
_mode_manager = None
_curve_controller = None
_pwm_controller = None
_data_logger = None


def init_mode_blueprint(mode_manager, curve_controller=None, pwm_controller=None, data_logger=None):
    """Initialize blueprint with dependencies"""
    global _mode_manager, _curve_controller, _pwm_controller, _data_logger
    _mode_manager = mode_manager
    _curve_controller = curve_controller
    _pwm_controller = pwm_controller
    _data_logger = data_logger
    logger.info("Mode blueprint initialized")


def create_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


def _apply_curve_values() -> dict:
    """Apply current curve values to lamps. Returns applied intensities."""
    applied = {}
    if _curve_controller and _pwm_controller:
        intensities = _curve_controller.get_current_intensities()
        for channel, intensity in intensities.items():
            _pwm_controller.set_intensity(channel, intensity)
            applied[channel] = intensity
        logger.info(f"Applied curve intensities: {applied}")
    return applied


def _get_current_mode() -> str:
    """Get current mode from ModeManager or fallback."""
    if _mode_manager:
        return _mode_manager.get_mode()
    return "auto"


# ============================================================================
# Routes
# ============================================================================

@mode_bp.route('/api/mode', methods=['GET'])
def get_mode():
    """Get current operating mode

    Response:
        {
            "success": true,
            "mode": "auto",
            "modes": {
                "auto": "Zeitsteuerung (Kurven aktiv)",
                "manual": "Manuell (Slider aktiv)"
            }
        }
    """
    current = _get_current_mode()
    return jsonify(create_response(True, {
        "mode": current,
        "modes": {
            "auto": "Zeitsteuerung (Kurven aktiv)",
            "manual": "Manuell (Slider aktiv)"
        }
    }))


@mode_bp.route('/api/mode', methods=['POST'])
def set_mode():
    """Set operating mode

    Request body:
        {
            "mode": "auto" | "manual"
        }

    Response:
        {
            "success": true,
            "mode": "auto",
            "message": "Mode set to auto",
            "applied_intensities": {1: 50, 2: 75, ...}  // Only in auto mode
        }

    Behavior:
        - auto mode: Immediately applies curve values to lamps
        - manual mode: Keeps current lamp values unchanged (user adjusts via sliders)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        mode = data.get('mode')

        if mode not in ('auto', 'manual'):
            return jsonify(create_response(False, error="Mode must be 'auto' or 'manual'")), 400

        old_mode = _get_current_mode()
        applied_intensities = {}

        # Update mode in ModeManager
        if _mode_manager:
            _mode_manager.set_mode(mode)

        # When switching to auto mode, immediately apply curve values
        if mode == 'auto':
            applied_intensities = _apply_curve_values()

        # When switching to manual mode, keep current lamp values (no change needed)
        # The sliders in UI will show current values and user can adjust from there

        # Log the change
        if _data_logger and old_mode != mode:
            try:
                _data_logger.log_event(
                    'mode_change',
                    'info',
                    f'Mode changed from {old_mode} to {mode}',
                    {'old_mode': old_mode, 'new_mode': mode, 'applied': applied_intensities}
                )
            except Exception as e:
                logger.warning(f"Failed to log mode change: {e}")

        logger.info(f"Mode changed: {old_mode} -> {mode}")

        return jsonify(create_response(True, {
            "mode": mode,
            "message": f"Mode set to {mode}",
            "applied_intensities": applied_intensities
        }))

    except Exception as e:
        logger.error(f"Error in set_mode: {e}")
        return jsonify(create_response(False, error=str(e))), 500
