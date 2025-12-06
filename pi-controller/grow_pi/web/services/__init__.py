"""
GrowPi Web Services

Hardware abstraction layer that separates Flask blueprints from
hardware controllers (PWM, sensors, curves, logging).
"""

# Lamp Configuration
from .lamp_config import (
    get_lamp_channels,
    get_lamp_channel,
    is_valid_channel,
    LampChannel,
)

# Hardware Service
from .hardware_service import (
    get_pwm_service,
    initialize_pwm,
    set_lamp_intensity,
    get_lamp_state,
    set_all_lamps,
    initialize_dht22,
    read_dht22,
    clear_dht_cache,
    PWM_AVAILABLE,
    DHT_AVAILABLE,
)

# Logging Service
from .logging_service import (
    get_data_logger,
    start_data_logger,
    stop_data_logger,
    log_lamp_change,
    log_system_event,
    get_logger_status,
    is_logger_running,
    LOGGING_AVAILABLE,
)

# Curve Service
from .curve_service import (
    get_curve_service,
    initialize_curves,
    get_current_intensities,
    get_channel_curve,
    get_all_curves,
    update_channel_curve,
    is_curve_enabled,
    get_channel_name,
    get_curve_status,
    get_mode_service,
    get_current_mode,
    set_mode,
    is_auto_mode,
    is_manual_mode,
    register_mode_callback,
    apply_curve_values,
    CURVE_AVAILABLE,
    MODE_AVAILABLE,
)

__all__ = [
    # Lamp Config
    'get_lamp_channels',
    'get_lamp_channel',
    'is_valid_channel',
    'LampChannel',
    # Hardware
    'get_pwm_service',
    'initialize_pwm',
    'set_lamp_intensity',
    'get_lamp_state',
    'set_all_lamps',
    'initialize_dht22',
    'read_dht22',
    'clear_dht_cache',
    'PWM_AVAILABLE',
    'DHT_AVAILABLE',
    # Logging
    'get_data_logger',
    'start_data_logger',
    'stop_data_logger',
    'log_lamp_change',
    'log_system_event',
    'get_logger_status',
    'is_logger_running',
    'LOGGING_AVAILABLE',
    # Curves
    'get_curve_service',
    'initialize_curves',
    'get_current_intensities',
    'get_channel_curve',
    'get_all_curves',
    'update_channel_curve',
    'is_curve_enabled',
    'get_channel_name',
    'get_curve_status',
    'get_mode_service',
    'get_current_mode',
    'set_mode',
    'is_auto_mode',
    'is_manual_mode',
    'register_mode_callback',
    'apply_curve_values',
    'CURVE_AVAILABLE',
    'MODE_AVAILABLE',
]
