"""
Logging Service Layer

Abstracts DataLogger operations from Flask blueprints.
Manages background data logging threads.
"""

import logging
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)

# Try to import database modules
LOGGING_AVAILABLE = False
try:
    from ...database import get_database, get_logger, DataLogger
    LOGGING_AVAILABLE = True
except ImportError:
    logger.warning("Database/logging modules not available")


# ============================================================================
# DataLogger Service
# ============================================================================

def get_data_logger(sensor_interval: int = 60, lamp_interval: int = 60) -> Optional['DataLogger']:
    """
    Get the global DataLogger singleton.

    Args:
        sensor_interval: Seconds between sensor readings
        lamp_interval: Seconds between lamp state logs

    Returns:
        DataLogger instance or None if not available
    """
    if not LOGGING_AVAILABLE:
        return None

    try:
        db = get_database()
        return get_logger(db=db, sensor_interval=sensor_interval, lamp_interval=lamp_interval)
    except Exception as e:
        logger.error(f"Failed to get DataLogger: {e}")
        return None


def start_data_logger(
    sensor_reader: Callable = None,
    lamp_reader: Callable = None,
    startup_states: Dict[int, Dict[str, Any]] = None
) -> bool:
    """
    Start the data logger with sensor and lamp readers.

    Args:
        sensor_reader: Callable that returns (temp, humidity) tuple
        lamp_reader: Callable that returns lamp states dict
        startup_states: Initial lamp states to log

    Returns:
        True if started successfully
    """
    data_logger = get_data_logger()
    if not data_logger:
        logger.warning("DataLogger not available")
        return False

    try:
        # Set up readers
        if sensor_reader:
            data_logger.set_sensor_reader(sensor_reader)
        if lamp_reader:
            data_logger.set_lamp_reader(lamp_reader)

        # Log startup states if provided
        if startup_states:
            data_logger.log_startup_states(startup_states)

        # Start background logging
        data_logger.start()
        logger.info("DataLogger started successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to start DataLogger: {e}")
        return False


def stop_data_logger(channels: list = None, channel_names: Dict[int, str] = None) -> bool:
    """
    Stop the data logger gracefully.

    Args:
        channels: List of channel numbers to log shutdown states
        channel_names: Dict mapping channel to name

    Returns:
        True if stopped successfully
    """
    data_logger = get_data_logger()
    if not data_logger:
        return False

    try:
        # Log shutdown states if provided
        if channels and channel_names:
            data_logger.log_shutdown_states(channels, channel_names)

        data_logger.stop()
        logger.info("DataLogger stopped successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to stop DataLogger: {e}")
        return False


def log_lamp_change(
    channel: int,
    name: str,
    intensity: int,
    source: str,
    curve_time: str = None
) -> bool:
    """
    Log a lamp state change event.

    Args:
        channel: Channel number
        name: Channel name
        intensity: New intensity (0-100)
        source: Change source (e.g., 'api', 'curve', 'manual')
        curve_time: Optional curve time reference

    Returns:
        True if logged successfully
    """
    data_logger = get_data_logger()
    if not data_logger:
        return False

    try:
        data_logger.log_lamp_change(channel, name, intensity, source, curve_time)
        return True
    except Exception as e:
        logger.error(f"Failed to log lamp change: {e}")
        return False


def log_system_event(
    event_type: str,
    severity: str,
    message: str,
    details: Dict = None
) -> bool:
    """
    Log a system event.

    Args:
        event_type: Event type identifier
        severity: 'info', 'warning', 'error'
        message: Event message
        details: Optional dict with additional details

    Returns:
        True if logged successfully
    """
    data_logger = get_data_logger()
    if not data_logger:
        return False

    try:
        data_logger.log_event(event_type, severity, message, details)
        return True
    except Exception as e:
        logger.error(f"Failed to log event: {e}")
        return False


def get_logger_status() -> Dict[str, Any]:
    """
    Get data logger status and statistics.

    Returns:
        Status dict with running state and database stats
    """
    data_logger = get_data_logger()
    if not data_logger:
        return {
            'running': False,
            'available': False,
            'error': 'DataLogger not available'
        }

    try:
        status = data_logger.get_status()
        status['available'] = True
        return status
    except Exception as e:
        logger.error(f"Failed to get logger status: {e}")
        return {
            'running': False,
            'available': False,
            'error': str(e)
        }


def is_logger_running() -> bool:
    """
    Check if data logger is currently running.

    Returns:
        True if logger is running
    """
    data_logger = get_data_logger()
    if not data_logger:
        return False

    return data_logger._running
