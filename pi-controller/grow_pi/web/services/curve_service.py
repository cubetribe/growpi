"""
Curve Service Layer

Abstracts CurveController and ModeManager operations from Flask blueprints.
Manages automated curve-based lighting control.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

# Try to import curve modules
CURVE_AVAILABLE = False
MODE_AVAILABLE = False

try:
    from ...utils.curve_controller import CurveController, get_curve_controller
    CURVE_AVAILABLE = True
except ImportError:
    logger.warning("CurveController not available")

try:
    from ...utils.mode_manager import get_mode_manager
    MODE_AVAILABLE = True
except ImportError:
    logger.warning("ModeManager not available")


# ============================================================================
# CurveController Service
# ============================================================================

def get_curve_service() -> Optional['CurveController']:
    """
    Get the global CurveController singleton.

    Returns:
        CurveController instance or None if not available
    """
    if not CURVE_AVAILABLE:
        return None

    try:
        return get_curve_controller()
    except Exception as e:
        logger.error(f"Failed to get CurveController: {e}")
        return None


def initialize_curves(channels: Dict[int, str]) -> bool:
    """
    Initialize curve controller with channel configuration.

    Args:
        channels: Dict mapping channel number to name {1: "Far Red", ...}

    Returns:
        True if initialization successful
    """
    controller = get_curve_service()
    if not controller:
        logger.error("CurveController not available")
        return False

    if controller._initialized:
        logger.debug("CurveController already initialized")
        return True

    try:
        controller.initialize(channels)
        logger.info(f"CurveController initialized with {len(channels)} channels")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize CurveController: {e}")
        return False


def get_current_intensities(current_time: datetime = None) -> Dict[int, int]:
    """
    Calculate current intensity for all channels based on curves.

    Args:
        current_time: Time to calculate for (default: now)

    Returns:
        Dict mapping channel to intensity {1: 45, 2: 30, ...}
    """
    controller = get_curve_service()
    if not controller:
        return {ch: 0 for ch in range(1, 5)}

    return controller.get_current_intensities(current_time)


def get_channel_curve(channel: int) -> Optional[List[Dict]]:
    """
    Get curve points for a specific channel.

    Args:
        channel: Channel number (1-4)

    Returns:
        List of {time, intensity} dicts or None if not found
    """
    controller = get_curve_service()
    if not controller:
        return None

    return controller.get_curve(channel)


def get_all_curves() -> Dict[int, List[Dict]]:
    """
    Get curves for all channels.

    Returns:
        Dict mapping channel to curve points
    """
    controller = get_curve_service()
    if not controller:
        return {}

    return controller.get_all_curves()


def update_channel_curve(channel: int, curve_points: List[Dict], enabled: bool = True) -> bool:
    """
    Update curve for a specific channel.

    Args:
        channel: Channel number (1-4)
        curve_points: List of {time, intensity} dicts
        enabled: Whether curve is active

    Returns:
        True if successful
    """
    controller = get_curve_service()
    if not controller:
        return False

    return controller.update_curve(channel, curve_points, enabled)


def is_curve_enabled(channel: int) -> bool:
    """
    Check if a channel's curve is enabled.

    Args:
        channel: Channel number (1-4)

    Returns:
        True if curve is enabled
    """
    controller = get_curve_service()
    if not controller:
        return False

    return controller.is_enabled(channel)


def get_channel_name(channel: int) -> str:
    """
    Get name for a channel.

    Args:
        channel: Channel number (1-4)

    Returns:
        Channel name or "Channel X" if not found
    """
    controller = get_curve_service()
    if not controller:
        return f"Channel {channel}"

    return controller.get_channel_name(channel)


def get_curve_status() -> Dict:
    """
    Get curve controller status.

    Returns:
        Status dict with initialized state and channel info
    """
    controller = get_curve_service()
    if not controller:
        return {
            'initialized': False,
            'available': False,
            'channels': {}
        }

    status = controller.get_status()
    status['available'] = True
    return status


# ============================================================================
# ModeManager Service
# ============================================================================

def get_mode_service():
    """
    Get the global ModeManager singleton.

    Returns:
        ModeManager instance or None if not available
    """
    if not MODE_AVAILABLE:
        return None

    try:
        return get_mode_manager()
    except Exception as e:
        logger.error(f"Failed to get ModeManager: {e}")
        return None


def get_current_mode() -> str:
    """
    Get current operating mode.

    Returns:
        'auto' or 'manual' (defaults to 'auto')
    """
    mode_manager = get_mode_service()
    if not mode_manager:
        return "auto"

    return mode_manager.get_mode()


def set_mode(mode: str) -> bool:
    """
    Set operating mode.

    Args:
        mode: 'auto' or 'manual'

    Returns:
        True if mode was changed
    """
    mode_manager = get_mode_service()
    if not mode_manager:
        logger.warning("ModeManager not available, cannot set mode")
        return False

    return mode_manager.set_mode(mode)


def is_auto_mode() -> bool:
    """
    Check if currently in auto mode.

    Returns:
        True if auto mode is active
    """
    return get_current_mode() == "auto"


def is_manual_mode() -> bool:
    """
    Check if currently in manual mode.

    Returns:
        True if manual mode is active
    """
    return get_current_mode() == "manual"


def register_mode_callback(callback) -> bool:
    """
    Register a callback for mode changes.

    Args:
        callback: Function with signature callback(old_mode: str, new_mode: str)

    Returns:
        True if registered successfully
    """
    mode_manager = get_mode_service()
    if not mode_manager:
        return False

    try:
        mode_manager.register_callback(callback)
        return True
    except Exception as e:
        logger.error(f"Failed to register mode callback: {e}")
        return False


# ============================================================================
# Combined Curve + Mode Operations
# ============================================================================

def apply_curve_values(pwm_controller) -> Dict[int, int]:
    """
    Apply current curve values to PWM controller.

    This is the main function that bridges curves to hardware.
    Called when switching to auto mode or periodically in auto mode.

    Args:
        pwm_controller: PWM controller instance

    Returns:
        Dict of applied intensities {channel: intensity}
    """
    applied = {}

    if not pwm_controller:
        logger.warning("No PWM controller provided")
        return applied

    controller = get_curve_service()
    if not controller:
        logger.warning("CurveController not available")
        return applied

    try:
        intensities = controller.get_current_intensities()

        for channel, intensity in intensities.items():
            success = pwm_controller.set_intensity(channel, intensity)
            if success:
                applied[channel] = intensity

        if applied:
            logger.info(f"Applied curve intensities: {applied}")

        return applied

    except Exception as e:
        logger.error(f"Failed to apply curve values: {e}")
        return applied
