#!/usr/bin/env python3
"""
GrowPi Flask REST API
Provides HTTP endpoints for lamp control, sensor reading, and data logging.

Core Endpoints:
    GET  /api/status      - Get all lamp values and temperature
    POST /api/lamp/<ch>   - Set lamp intensity (1-4)
    GET  /api/temperature - Get current temperature/humidity
    GET  /               - Serve frontend HTML

Legacy Log Routes (MIGRATED to blueprints/logs_bp.py):
    /api/logs/sensors - Sensor history with intelligent downsampling
    /api/logs/lamps   - Lamp state history with intelligent downsampling
    /api/logs/events  - System event history
    /api/logs/stats   - Logging statistics
    /api/logs/plugs   - Plug power/state history with intelligent downsampling
"""

from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_cors import CORS
import json
import logging
import os
import sys
import time
import atexit
from typing import Dict, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

# Add parent directory for imports
# Add parent directory for imports
# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    # Relative import (when run as module)
    from ..lamps.pwm_controller import PWMController, get_pwm_controller
except ImportError:
    try:
        # Absolute import (fallback)
        from grow_pi.lamps.pwm_controller import PWMController, get_pwm_controller
    except ImportError:
        # Development fallback (if run directly)
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from lamps.pwm_controller import PWMController, get_pwm_controller

# Try to import DHT22 sensor
DHT_AVAILABLE = False
try:
    import board
    import adafruit_dht
    DHT_AVAILABLE = True
except ImportError:
    logging.warning("adafruit_dht not available - sensor will return mock data")

# Try to import database module
DB_AVAILABLE = False
try:
    try:
        from ..database import get_database, get_logger, DataLogger
        from ..database.models import SensorType
    except ImportError:
        from grow_pi.database import get_database, get_logger, DataLogger
        from grow_pi.database.models import SensorType
    DB_AVAILABLE = True
except ImportError:
    logging.warning("Database module not available - logging disabled")

# Try to import curve controller
CURVE_AVAILABLE = False
curve_controller_module = None
try:
    try:
        from ..utils.curve_controller import CurveController, get_curve_controller
    except ImportError:
        from grow_pi.utils.curve_controller import CurveController, get_curve_controller
    CURVE_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CurveController not available - curve features disabled: {e}")

# Try to import mode manager
MODE_MANAGER_AVAILABLE = False
mode_manager = None
try:
    # Relative import (when run as module)
    from ..utils.mode_manager import get_mode_manager
    MODE_MANAGER_AVAILABLE = True
except ImportError:
    try:
        # Absolute import (fallback)
        from grow_pi.utils.mode_manager import get_mode_manager
        MODE_MANAGER_AVAILABLE = True
    except ImportError as e:
        logging.warning(f"ModeManager not available: {e}")


# ============================================================================
# Configuration
# ============================================================================

@dataclass
class LampChannel:
    """Lamp channel configuration"""
    id: int
    name: str
    gpio_pin: int
    color: str


# Lamp channel configuration - loaded from config file
LAMP_CHANNELS = {}

def load_lamp_channels():
    """Load lamp channels from config file"""
    global LAMP_CHANNELS
    try:
        try:
            from ..config import load_config
        except ImportError:
            from grow_pi.config import load_config
            
        config = load_config()
        # Colors: Far Red, Warm White, Cool White, UV
        colors = ["#ff4444", "#ffbb44", "#88ddff", "#cc66ff"]
        for i, ch in enumerate(config.lamps.channels):
            color = colors[i] if i < len(colors) else "#ffffff"
            LAMP_CHANNELS[ch.channel] = LampChannel(ch.channel, ch.name, ch.gpio_pin, color)
    except Exception as e:
        logging.error(f"Failed to load lamp channels: {e}")
        # Fallback - Final Pin Configuration 2025-12-05
        LAMP_CHANNELS = {
            1: LampChannel(1, "Far Red", 16, "#ff4444"),
            2: LampChannel(2, "Warm White", 13, "#ffbb44"),
            3: LampChannel(3, "Cool White", 18, "#88ddff"),
            4: LampChannel(4, "UV", 12, "#cc66ff")
        }

load_lamp_channels()

# Import version from centralized VERSION file
from grow_pi.version import get_version, get_version_display

# API Configuration
API_VERSION = get_version()  # GrowPi production version (from VERSION file)
API_PORT = 5000
API_HOST = "0.0.0.0"

# Static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# ============================================================================
# Register Blueprints for new API endpoints
# ============================================================================
try:
    from .blueprints.costs_bp import costs_bp
    from .blueprints.dehumidifier_bp import dehumidifier_bp
    from .blueprints.curves_bp import curves_bp, init_blueprint as init_curves_blueprint
    from .blueprints.logs_bp import logs_bp, init_logs_bp
    from .blueprints.calendar_bp import calendar_bp
    from .blueprints.status_bp import status_bp
    app.register_blueprint(costs_bp)
    app.register_blueprint(dehumidifier_bp)
    app.register_blueprint(curves_bp)
    app.register_blueprint(logs_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(status_bp, url_prefix='/api')
    logging.info("Registered costs_bp, dehumidifier_bp, curves_bp, logs_bp, calendar_bp, and status_bp blueprints")
except ImportError as e:
    logging.warning(f"Could not import blueprints: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Hardware Initialization
# ============================================================================

# Initialize PWM Controller (use singleton)
# BUGFIX 2025-12-07: Check for warm restart state BEFORE initializing
pwm_controller = None
try:
    pwm_controller = get_pwm_controller()  # Use singleton!
    # Initialize with channel configs (only if not already initialized)
    if not pwm_controller._initialized:
        try:
            from ..config import load_config
        except ImportError:
            from grow_pi.config import load_config
        config = load_config()

        # Check for warm restart state - don't reset PWM to 0 if state exists
        skip_zero = False
        try:
            try:
                from ..utils.pwm_state import state_exists
            except ImportError:
                from grow_pi.utils.pwm_state import state_exists
            skip_zero = state_exists()
            if skip_zero:
                logger.info("Warm restart detected - preserving PWM values")
        except ImportError:
            pass

        pwm_controller.initialize(config.lamps.channels, skip_zero_init=skip_zero)
    logger.info("PWM Controller initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize PWM Controller: {e}")

# Initialize DHT22 Sensor
dht_sensor = None
if DHT_AVAILABLE:
    # ROBUSTNESS FIX 2025-12-20: Multiple retry attempts after hard reset
    max_init_retries = 5
    init_retry_delay = 2

    for attempt in range(1, max_init_retries + 1):
        try:
            dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            logger.info(f"DHT22 Sensor initialized on GPIO-4 (attempt {attempt}/{max_init_retries})")
            break
        except RuntimeError as e:
            if attempt < max_init_retries:
                logger.warning(f"DHT22 init attempt {attempt}/{max_init_retries} failed: {e} - retrying in {init_retry_delay}s...")
                time.sleep(init_retry_delay)
            else:
                logger.error(f"DHT22 initialization failed after {max_init_retries} attempts: {e}")
                logger.error("DHT_AVAILABLE set to False - sensor will return mock data")
                DHT_AVAILABLE = False
                dht_sensor = None
        except Exception as e:
            logger.error(f"Unexpected DHT22 initialization error: {e}")
            DHT_AVAILABLE = False
            dht_sensor = None
            break

# Initialize DataLogger
db = None
data_logger: Optional['DataLogger'] = None
if DB_AVAILABLE:
    try:
        db = get_database()
        data_logger = get_logger(db=db, sensor_interval=60, lamp_interval=60)
        logger.info("DataLogger initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize DataLogger: {e}")

# Initialize CurveController
curve_controller: Optional['CurveController'] = None
if CURVE_AVAILABLE and DB_AVAILABLE:
    try:
        channels = {ch: cfg.name for ch, cfg in LAMP_CHANNELS.items()}
        curve_controller = get_curve_controller()
        curve_controller.initialize(channels)
        logger.info("CurveController initialized successfully")

        # Initialize curves blueprint with dependencies
        try:
            init_curves_blueprint(curve_controller, data_logger, LAMP_CHANNELS)
            logger.info("Curves blueprint initialized with dependencies")
        except Exception as e:
            logger.warning(f"Could not initialize curves blueprint: {e}")
    except Exception as e:
        logger.error(f"Failed to initialize CurveController: {e}")

# Initialize logs blueprint with database dependencies
if DB_AVAILABLE and data_logger:
    try:
        init_logs_bp(DB_AVAILABLE, data_logger, get_database)
        logger.info("Logs blueprint initialized with database dependencies")
    except Exception as e:
        logger.warning(f"Could not initialize logs blueprint: {e}")

# Initialize ModeManager
if MODE_MANAGER_AVAILABLE:
    try:
        mode_manager = get_mode_manager()
        logger.info(f"ModeManager initialized (current mode: {mode_manager.get_mode()})")
    except Exception as e:
        logger.error(f"Failed to initialize ModeManager: {e}")

# Register shared dependencies for blueprints (status/health/etc.)
try:
    from . import dependencies as web_dependencies
    web_dependencies.init_pwm_controller(pwm_controller)
    web_dependencies.init_dht_sensor(
        dht_sensor,
        DHT_AVAILABLE and dht_sensor is not None
    )
    web_dependencies.init_data_logger(data_logger, db)
    web_dependencies.init_curve_controller(
        curve_controller,
        curve_controller is not None
    )
    web_dependencies.init_mode_manager(
        mode_manager if MODE_MANAGER_AVAILABLE else None,
        MODE_MANAGER_AVAILABLE and mode_manager is not None
    )
    logger.info("Blueprint dependencies initialized")
except Exception as e:
    logger.warning(f"Failed to initialize blueprint dependencies: {e}")

# Initialize DehumidifierController and inject into blueprint
dehumidifier_controller = None
try:
    try:
        from ..utils.dehumidifier_controller import get_dehumidifier_controller
    except ImportError:
        from grow_pi.utils.dehumidifier_controller import get_dehumidifier_controller

    dehumidifier_controller = get_dehumidifier_controller()

    # Inject dependencies into dehumidifier blueprint
    try:
        from .blueprints.dehumidifier_bp import set_dehumidifier_controller, set_humidity_reader
        set_dehumidifier_controller(dehumidifier_controller)

        # Note: humidity_reader will be set after read_dht22 is defined
        logger.info("DehumidifierController initialized and injected into blueprint")
    except ImportError as e:
        logger.warning(f"Could not inject dehumidifier dependencies: {e}")
except ImportError as e:
    logger.warning(f"DehumidifierController not available: {e}")
except Exception as e:
    logger.error(f"Failed to initialize DehumidifierController: {e}")


# ============================================================================
# Helper Functions
# ============================================================================

def create_response(success: bool, data: Dict = None, error: str = None) -> Dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# Shared Sensor Cache (v6.22.2)
# ============================================================================
# Use shared sensor cache to ensure consistent values across all endpoints
try:
    from ..utils.sensor_cache import read_dht22, get_cached_values, init_sensor, init_data_logger
except ImportError:
    from grow_pi.utils.sensor_cache import read_dht22, get_cached_values, init_sensor, init_data_logger

# Initialize sensor cache with DHT sensor instance
init_sensor(dht_sensor, DHT_AVAILABLE)
logger.info(f"Shared sensor cache initialized (DHT available: {DHT_AVAILABLE})")


# Set humidity reader for dehumidifier - BOTH controller AND blueprint need it!
if dehumidifier_controller is not None:
    # BUGFIX 2025-12-07: Controller needs humidity_reader for automation loop
    dehumidifier_controller.set_humidity_reader(read_dht22)
    logger.info("Humidity reader set for DehumidifierController")
    try:
        from .blueprints.dehumidifier_bp import set_humidity_reader
        set_humidity_reader(read_dht22)
        logger.info("Humidity reader set for dehumidifier blueprint")
    except ImportError:
        pass


def get_lamp_states() -> Dict[int, Dict]:
    """Get current lamp states for logging."""
    states = {}
    if pwm_controller:
        current = pwm_controller.get_current_state()
        for channel_id, config in LAMP_CHANNELS.items():
            states[channel_id] = {
                'name': config.name,
                'intensity': current.get(channel_id, 0)
            }
    return states


# ============================================================================
# DataLogger Setup
# ============================================================================

def start_data_logger():
    """Start the data logger with sensor and lamp readers."""
    global data_logger
    if data_logger:
        # Set up readers
        data_logger.set_sensor_reader(read_dht22)
        data_logger.set_lamp_reader(get_lamp_states)

        # Log startup states
        data_logger.log_startup_states(get_lamp_states())

        # Start background logging
        data_logger.start()
        logger.info("DataLogger started")


def start_dehumidifier_controller():
    """Start the dehumidifier controller with automatic humidity control."""
    controller = _get_dehumidifier()
    if controller:
        # Start automatic control loop (checks every 10 seconds)
        controller.start(check_interval=10)
        logger.info("DehumidifierController started (check_interval: 10s)")
    else:
        logger.warning("DehumidifierController not available - skipping startup")


def stop_data_logger():
    """Stop the data logger gracefully."""
    global data_logger
    if data_logger:
        # Log shutdown states
        channels = list(LAMP_CHANNELS.keys())
        names = {ch: cfg.name for ch, cfg in LAMP_CHANNELS.items()}
        data_logger.log_shutdown_states(channels, names)

        data_logger.stop()
        logger.info("DataLogger stopped")


def stop_dehumidifier_controller():
    """Stop the dehumidifier controller gracefully."""
    controller = _get_dehumidifier()
    if controller:
        controller.stop()
        logger.info("DehumidifierController stopped")


def get_runtime_health() -> Dict[str, Any]:
    """
    Export runtime health of critical background components.

    Used by the main controller watchdog to detect partial failures where the
    process is alive but worker threads have died.
    """
    components: Dict[str, Any] = {}
    issues = []

    if data_logger is not None:
        try:
            if hasattr(data_logger, "get_runtime_health"):
                logger_health = data_logger.get_runtime_health()
            else:
                logger_health = {
                    "healthy": bool(data_logger._running),
                    "running": bool(data_logger._running),
                    "issues": ["runtime_health_not_implemented"]
                }
            components["data_logger"] = logger_health
            if not logger_health.get("healthy", True):
                issues.append("data_logger_unhealthy")
        except Exception as exc:
            components["data_logger"] = {"healthy": False, "error": str(exc)}
            issues.append("data_logger_check_failed")

    if dehumidifier_controller is not None:
        try:
            if hasattr(dehumidifier_controller, "get_runtime_health"):
                dehumidifier_health = dehumidifier_controller.get_runtime_health()
            else:
                dehumidifier_health = {
                    "healthy": True,
                    "issues": ["runtime_health_not_implemented"]
                }
            components["dehumidifier"] = dehumidifier_health
            if not dehumidifier_health.get("healthy", True):
                issues.append("dehumidifier_unhealthy")
        except Exception as exc:
            components["dehumidifier"] = {"healthy": False, "error": str(exc)}
            issues.append("dehumidifier_check_failed")

    return {
        "healthy": len(issues) == 0,
        "issues": issues,
        "components": components
    }


# Register shutdown handlers
atexit.register(stop_data_logger)
atexit.register(stop_dehumidifier_controller)


# ============================================================================
# API Routes
# ============================================================================

@app.route('/')
def serve_frontend():
    """Serve the frontend HTML"""
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/<path:path>')
def serve_static(path):
    """Serve static files or fallback to index.html for SPA routing"""
    if os.path.exists(os.path.join(STATIC_DIR, path)):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, 'index.html')


@app.route('/api/status', methods=['GET'])
def get_status():
    """Get current system status including all lamp intensities and sensor data"""
    try:
        # Get lamp intensities
        lamps = []
        for channel_id, config in LAMP_CHANNELS.items():
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
        temp, humidity = read_dht22()

        return jsonify(create_response(True, {
            "lamps": lamps,
            "temperature": temp,
            "humidity": humidity,
            "timestamp": datetime.now().isoformat(),
            "version": API_VERSION,
            "logging_enabled": data_logger is not None and data_logger._running
        }))

    except Exception as e:
        logger.error(f"Error in get_status: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/lamp/<int:channel>', methods=['POST'])
def set_lamp(channel: int):
    """Set intensity for a specific lamp channel"""
    try:
        # Validate channel
        if channel not in LAMP_CHANNELS:
            return jsonify(create_response(False, error=f"Invalid channel: {channel}. Must be 1-4")), 400

        # Check PWM controller
        if pwm_controller is None:
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
        if not pwm_controller.set_intensity(channel, intensity):
            logger.error(
                f"Failed to set lamp {channel} ({LAMP_CHANNELS[channel].name}) to {intensity}%"
            )
            return jsonify(create_response(False, error="Failed to set PWM intensity")), 500
        logger.info(f"Set lamp {channel} ({LAMP_CHANNELS[channel].name}) to {intensity}%")

        # Log the change
        if data_logger:
            data_logger.log_lamp_change(
                channel=channel,
                name=LAMP_CHANNELS[channel].name,
                intensity=intensity,
                source='api'
            )

        return jsonify(create_response(True, {
            "channel": channel,
            "name": LAMP_CHANNELS[channel].name,
            "intensity": intensity
        }))

    except Exception as e:
        logger.error(f"Error in set_lamp: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/temperature', methods=['GET'])
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


# ============================================================================
# Logging API Routes
# ============================================================================

# MIGRATED to logs_bp.py - see blueprints/logs_bp.py
# Old route with limit=1000 caused missing data - new version uses intelligent downsampling
# @app.route('/api/logs/sensors', methods=['GET'])
# def get_sensor_logs():
#     """Get sensor reading history"""
#     if not DB_AVAILABLE or not data_logger:
#         return jsonify(create_response(False, error="Logging not available")), 503
#
#     try:
#         sensor_type = request.args.get('type')
#         hours = int(request.args.get('hours', 24))
#         limit = int(request.args.get('limit', 1000))
#
#         db = get_database()
#         readings = db.get_sensor_readings(sensor_type=sensor_type, hours=hours, limit=limit)
#
#         return jsonify(create_response(True, {
#             "readings": [r.to_dict() for r in readings],
#             "count": len(readings),
#             "hours": hours
#         }))
#
#     except Exception as e:
#         logger.error(f"Error in get_sensor_logs: {e}")
#         return jsonify(create_response(False, error=str(e))), 500


# MIGRATED to logs_bp.py - see blueprints/logs_bp.py
# Old route with limit=1000 caused missing data - new version uses intelligent downsampling
# @app.route('/api/logs/lamps', methods=['GET'])
# def get_lamp_logs():
#     """Get lamp state history"""
#     if not DB_AVAILABLE or not data_logger:
#         return jsonify(create_response(False, error="Logging not available")), 503
#
#     try:
#         channel = request.args.get('channel', type=int)
#         hours = int(request.args.get('hours', 24))
#         limit = int(request.args.get('limit', 1000))
#
#         db = get_database()
#         logs = db.get_lamp_state_log(channel=channel, hours=hours, limit=limit)
#
#         return jsonify(create_response(True, {
#             "logs": [l.to_dict() for l in logs],
#             "count": len(logs),
#             "hours": hours
#         }))
#
#     except Exception as e:
#         logger.error(f"Error in get_lamp_logs: {e}")
#         return jsonify(create_response(False, error=str(e))), 500


# MIGRATED to logs_bp.py - see blueprints/logs_bp.py
# Old route with limit=100 caused missing data - new version includes all events
# @app.route('/api/logs/events', methods=['GET'])
# def get_event_logs():
#     """Get system event history"""
#     if not DB_AVAILABLE or not data_logger:
#         return jsonify(create_response(False, error="Logging not available")), 503
#
#     try:
#         event_type = request.args.get('type')
#         severity = request.args.get('severity')
#         hours = int(request.args.get('hours', 24))
#         limit = int(request.args.get('limit', 100))
#
#         db = get_database()
#         events = db.get_system_events(
#             event_type=event_type,
#             severity=severity,
#             hours=hours,
#             limit=limit
#         )
#
#         return jsonify(create_response(True, {
#             "events": [e.to_dict() for e in events],
#             "count": len(events),
#             "hours": hours
#         }))
#
#     except Exception as e:
#         logger.error(f"Error in get_event_logs: {e}")
#         return jsonify(create_response(False, error=str(e))), 500


# NOTE: /api/logs/plugs route has been migrated to logs_bp.py blueprint
# The blueprint version uses intelligent downsampling instead of hard limit
# Old route with limit=1000 caused issues with multiple devices (only ~2.7h data for 6 devices)


# MIGRATED to logs_bp.py - see blueprints/logs_bp.py
# Moved to blueprint for consistency with other log routes
# @app.route('/api/logs/stats', methods=['GET'])
# def get_log_stats():
#     """Get logging statistics"""
#     if not DB_AVAILABLE or not data_logger:
#         return jsonify(create_response(False, error="Logging not available")), 503
#
#     try:
#         status = data_logger.get_status()
#         return jsonify(create_response(True, status))
#
#     except Exception as e:
#         logger.error(f"Error in get_log_stats: {e}")
#         return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Curve API Routes - DEPRECATED v6.16.0
# ============================================================================

# DEPRECATED v6.16.0: Moved to blueprints/curves_bp.py
# These routes are now handled by the curves blueprint (registered at line 166)
# The blueprint also includes additional preset management endpoints
# @app.route('/api/curves', methods=['GET'])
# def get_all_curves():
#     """Get all lamp curves"""
#     ...
#
# @app.route('/api/curves/<int:channel>', methods=['GET'])
# def get_curve(channel: int):
#     """Get curve for a specific channel"""
#     ...
#
# @app.route('/api/curves/<int:channel>', methods=['PUT'])
# def update_curve(channel: int):
#     """Update curve for a specific channel"""
#     ...
#
# @app.route('/api/curves/preview', methods=['GET'])
# def get_curve_preview():
#     """Get 24h preview of all curve intensities"""
#     ...
#
# @app.route('/api/curves/intensities', methods=['GET'])
# def get_current_intensities():
#     """Get current interpolated intensities for all channels"""
#     ...


# ============================================================================
# Mode API Routes
# ============================================================================

def _apply_curve_values() -> dict:
    """Apply current curve values to lamps. Returns applied intensities."""
    applied = {}
    if curve_controller and pwm_controller:
        intensities = curve_controller.get_current_intensities()
        for channel, intensity in intensities.items():
            if pwm_controller.set_intensity(channel, intensity):
                applied[channel] = intensity
            else:
                logger.warning(
                    "Failed to apply curve intensity on mode switch for channel %s: target=%s%%",
                    channel,
                    intensity,
                )
        logger.info(f"Applied curve intensities: {applied}")
    return applied


def _get_current_mode() -> str:
    """Get current mode from ModeManager or fallback."""
    if mode_manager:
        return mode_manager.get_mode()
    return "auto"


@app.route('/api/mode', methods=['GET'])
def get_mode():
    """Get current operating mode"""
    current = _get_current_mode()
    return jsonify(create_response(True, {
        "mode": current,
        "modes": {
            "auto": "Zeitsteuerung (Kurven aktiv)",
            "manual": "Manuell (Slider aktiv)"
        }
    }))


@app.route('/api/mode', methods=['POST'])
def set_mode():
    """Set operating mode"""
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
        if mode_manager:
            mode_manager.set_mode(mode)

        # When switching to auto mode, immediately apply curve values
        if mode == 'auto':
            applied_intensities = _apply_curve_values()

        # When switching to manual mode, keep current lamp values (no change needed)
        # The sliders in UI will show current values and user can adjust from there

        # Log the change
        if data_logger and old_mode != mode:
            try:
                data_logger.log_event(
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


# ============================================================================
# Camera API Routes
# ============================================================================

# Try to import camera service
CAMERA_AVAILABLE = False
camera_service = None
try:
    try:
        from ..utils.camera import get_camera_service
    except ImportError:
        from grow_pi.utils.camera import get_camera_service
    CAMERA_AVAILABLE = True
except ImportError as e:
    logging.warning(f"CameraService not available: {e}")


def _get_camera():
    """Get or initialize camera service."""
    global camera_service
    if CAMERA_AVAILABLE and camera_service is None:
        camera_service = get_camera_service()
    return camera_service


@app.route('/api/camera/snapshot', methods=['GET'])
def get_camera_snapshot():
    """Get a JPEG snapshot from the camera"""
    camera = _get_camera()
    if not camera or not camera.is_available:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        jpeg_data = camera.capture_snapshot()
        if jpeg_data is None:
            return jsonify(create_response(False, error="Failed to capture image")), 500

        from flask import Response
        return Response(
            jpeg_data,
            mimetype='image/jpeg',
            headers={
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        )

    except Exception as e:
        logger.error(f"Error in get_camera_snapshot: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/status', methods=['GET'])
def get_camera_status():
    """Get camera status and availability"""
    camera = _get_camera()

    try:
        if camera:
            status = camera.get_status()
        else:
            status = {
                'available': False,
                'opencv_available': False,
                'error': 'Camera service not initialized'
            }

        return jsonify(create_response(True, status))

    except Exception as e:
        logger.error(f"Error in get_camera_status: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/config', methods=['POST'])
def update_camera_config():
    """Update camera configuration"""
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        status = camera.update_config(**data)

        return jsonify(create_response(True, {
            "message": "Camera configuration updated",
            "status": status
        }))

    except Exception as e:
        logger.error(f"Error in update_camera_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/config', methods=['GET'])
def get_timelapse_config():
    """Get timelapse configuration"""
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        from dataclasses import asdict
        return jsonify(create_response(True, {
            "config": asdict(camera.timelapse_config)
        }))

    except Exception as e:
        logger.error(f"Error in get_timelapse_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/config', methods=['POST'])
def update_timelapse_config():
    """Update timelapse configuration"""
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        config = camera.update_timelapse_config(**data)

        return jsonify(create_response(True, {
            "message": "Timelapse configuration updated",
            "config": config
        }))

    except Exception as e:
        logger.error(f"Error in update_timelapse_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/images', methods=['GET'])
def get_timelapse_images():
    """
    Get list of timelapse images.

    v6.17.0: Added date folder filtering support.

    Query params:
        limit (int): Maximum images to return (default 50)
        date (str): Optional date filter (YYYY-MM-DD format)
    """
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        import re

        limit = int(request.args.get('limit', 50))
        date_folder = request.args.get('date', None, type=str)

        # Validate date format if provided
        if date_folder:
            if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_folder):
                return jsonify(create_response(False, error="Invalid date format. Use YYYY-MM-DD")), 400

        images = camera.get_timelapse_images(limit=limit, date_folder=date_folder)

        return jsonify(create_response(True, {
            "images": images,
            "count": len(images),
            "date_filter": date_folder
        }))

    except Exception as e:
        logger.error(f"Error in get_timelapse_images: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Camera Timelapse API - v6.17.0
# ============================================================================

@app.route('/api/camera/timelapse/stats', methods=['GET'])
def get_timelapse_stats():
    """
    Get timelapse capture statistics.

    Returns config, storage info, and image counts.
    """
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        stats = camera.get_timelapse_stats()
        return jsonify(create_response(True, stats))
    except Exception as e:
        logger.error(f"Error in get_timelapse_stats: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/folders', methods=['GET'])
def get_timelapse_folders():
    """
    Get list of timelapse date folders.

    Returns list of folders with image counts.
    """
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        folders = camera.get_timelapse_folders()
        return jsonify(create_response(True, {
            "folders": folders,
            "count": len(folders)
        }))
    except Exception as e:
        logger.error(f"Error in get_timelapse_folders: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/image/<date_folder>/<filename>', methods=['GET'])
def get_timelapse_image(date_folder: str, filename: str):
    """
    Serve a specific timelapse image.

    Security: Validates date_folder and filename format to prevent directory traversal.

    Args:
        date_folder: Date folder in YYYY-MM-DD format
        filename: Image filename in timelapse_YYYYMMDD_HHMMSS.jpg format
    """
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        import re

        # Sanitize inputs to prevent directory traversal attacks
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_folder):
            return jsonify(create_response(False, error="Invalid date format")), 400
        if not re.match(r'^timelapse_\d{8}_\d{6}\.jpg$', filename):
            return jsonify(create_response(False, error="Invalid filename")), 400

        filepath = os.path.join(
            camera.timelapse_config.output_dir,
            date_folder,
            filename
        )

        if not os.path.exists(filepath):
            return jsonify(create_response(False, error="Image not found")), 404

        return send_file(
            filepath,
            mimetype='image/jpeg',
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Error serving timelapse image: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/camera/timelapse/test-brightness', methods=['GET'])
def test_timelapse_brightness():
    """
    Test brightness detection with current camera frame.

    Returns brightness analysis and whether an image would be saved
    with current darkness filter settings.

    Useful for calibrating brightness_threshold value.
    """
    camera = _get_camera()
    if not camera or not camera.is_available:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        result = camera.test_brightness()

        if result.get('success'):
            return jsonify(create_response(True, {
                "brightness": result['brightness'],
                "would_save": result['would_save']
            }))
        else:
            return jsonify(create_response(False, error=result.get('error', 'Unknown error'))), 500

    except Exception as e:
        logger.error(f"Error in test_brightness: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Health & Info
# ============================================================================
# NOTE: /api/health moved to status_bp.py (v6.22.0 - Health Monitoring)
# ============================================================================


@app.route('/api/version', methods=['GET'])
def get_version_info():
    """
    Get GrowPi version information.

    Returns:
        JSON with version details
    """
    return jsonify({
        "success": True,
        "version": get_version(),
        "version_display": get_version_display(),
        "api_version": API_VERSION
    })


# ============================================================================
# Room API Routes (Dehumidifier Control)
# ============================================================================

# Try to import dehumidifier controller
DEHUMIDIFIER_AVAILABLE = False
dehumidifier_controller = None
try:
    try:
        from ..utils.dehumidifier_controller import get_dehumidifier_controller
    except ImportError:
        from grow_pi.utils.dehumidifier_controller import get_dehumidifier_controller
    DEHUMIDIFIER_AVAILABLE = True
except ImportError as e:
    logging.warning(f"DehumidifierController not available: {e}")


def _get_dehumidifier():
    """Get or initialize dehumidifier controller with humidity reader."""
    global dehumidifier_controller
    if DEHUMIDIFIER_AVAILABLE and dehumidifier_controller is None:
        dehumidifier_controller = get_dehumidifier_controller()
        # Set humidity reader (using shared sensor cache)
        def humidity_reader():
            # BUGFIX v6.22.3: Use sensor_cache instead of temperature_bp.read_dht22()
            from grow_pi.utils.sensor_cache import read_dht22
            _, humidity = read_dht22()
            return humidity
        dehumidifier_controller.set_humidity_reader(humidity_reader)
    return dehumidifier_controller


# DEPRECATED v6.16.0: Moved to blueprints/dehumidifier_bp.py
# These routes are now handled by the dehumidifier blueprint (registered at line 165)
# @app.route('/api/room', methods=['GET'])
# def get_room_status():
#     """Get room status including temperature, humidity, and dehumidifier state"""
#     try:
#         temp, humidity = read_dht22()
#
#         response_data = {
#             "temperature": temp,
#             "humidity": humidity,
#             "timestamp": datetime.now().isoformat()
#         }
#
#         # Add dehumidifier status if available
#         controller = _get_dehumidifier()
#         if controller:
#             response_data["dehumidifier"] = controller.get_status()
#         else:
#             response_data["dehumidifier"] = {"available": False}
#
#         return jsonify(create_response(True, response_data))
#
#     except Exception as e:
#         logger.error(f"Error in get_room_status: {e}")
#         return jsonify(create_response(False, error=str(e))), 500
#
#
# @app.route('/api/room/config', methods=['GET'])
# def get_room_config():
#     """Get room/dehumidifier configuration"""
#     controller = _get_dehumidifier()
#     if not controller:
#         return jsonify(create_response(False, error="Dehumidifier not available")), 503
#
#     try:
#         return jsonify(create_response(True, {
#             "config": controller.get_config()
#         }))
#     except Exception as e:
#         logger.error(f"Error in get_room_config: {e}")
#         return jsonify(create_response(False, error=str(e))), 500
#
#
# @app.route('/api/room/config', methods=['POST'])
# def update_room_config():
#     """Update dehumidifier configuration"""
#     controller = _get_dehumidifier()
#     if not controller:
#         return jsonify(create_response(False, error="Dehumidifier not available")), 503
#
#     if not request.is_json:
#         return jsonify(create_response(False, error="Request must be JSON")), 400
#
#     try:
#         data = request.get_json()
#
#         updated = controller.update_config(
#             enabled=data.get('enabled'),
#             target=data.get('target'),
#             threshold_high=data.get('threshold_high'),
#             threshold_low=data.get('threshold_low'),
#             min_run_time=data.get('min_run_time'),
#             min_off_time=data.get('min_off_time'),
#             schedule_enabled=data.get('schedule_enabled'),
#             schedule_start_time=data.get('schedule_start_time'),
#             schedule_duration_minutes=data.get('schedule_duration_minutes')
#         )
#
#         logger.info(f"Room config updated: {updated}")
#
#         # If auto mode was just enabled, immediately run check_and_control
#         # This ensures the dehumidifier state matches the current humidity
#         control_result = None
#         if data.get('enabled') is True:
#             control_result = controller.check_and_control()
#             if control_result is not None:
#                 logger.info(f"Auto-control triggered: {'ON' if control_result else 'OFF'}")
#
#         return jsonify(create_response(True, {
#             "config": updated,
#             "message": "Configuration updated",
#             "auto_control_applied": control_result
#         }))
#
#     except Exception as e:
#         logger.error(f"Error in update_room_config: {e}")
#         return jsonify(create_response(False, error=str(e))), 500
#
#
# @app.route('/api/room/dehumidifier', methods=['POST'])
# def control_dehumidifier():
#     """Manually control dehumidifier (on/off)"""
#     controller = _get_dehumidifier()
#     if not controller:
#         return jsonify(create_response(False, error="Dehumidifier not available")), 503
#
#     if not request.is_json:
#         return jsonify(create_response(False, error="Request must be JSON")), 400
#
#     try:
#         data = request.get_json()
#         action = data.get('action')
#
#         if action == 'on':
#             success = controller.switch_on()
#             message = "Dehumidifier turned ON" if success else "Failed to turn ON"
#         elif action == 'off':
#             success = controller.switch_off()
#             message = "Dehumidifier turned OFF" if success else "Failed to turn OFF"
#         else:
#             return jsonify(create_response(False, error="Action must be 'on' or 'off'")), 400
#
#         return jsonify(create_response(success, {
#             "action": action,
#             "message": message,
#             "status": controller.get_status()
#         }))
#
#     except Exception as e:
#         logger.error(f"Error in control_dehumidifier: {e}")
#         return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Costs API - DEPRECATED v6.16.0
# ============================================================================

# DEPRECATED v6.16.0: Moved to blueprints/costs_bp.py
# These routes are now handled by the costs blueprint (registered at line 164)
# Helper functions _load_costs_config and _save_costs_config moved to costs_bp.py
#
# @app.route('/api/costs', methods=['GET'])
# def get_costs():
#     """Get power costs summary for all devices"""
#     ...
#
# @app.route('/api/costs/config', methods=['GET'])
# def get_costs_config():
#     """Get costs configuration (kWh price)"""
#     ...
#
# @app.route('/api/costs/config', methods=['POST'])
# def update_costs_config():
#     """Update kWh price"""
#     ...


# ============================================================================
# Error Handlers
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify(create_response(False, error="Endpoint not found")), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify(create_response(False, error="Internal server error")), 500


# ============================================================================
# Main Entry Point
# ============================================================================

def run_server(host: str = API_HOST, port: int = API_PORT, debug: bool = False):
    """Run the Flask server"""
    logger.info(f"Starting GrowPi Web API v{API_VERSION}")
    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"PWM Controller: {'Available' if pwm_controller else 'Not available'}")
    logger.info(f"DHT22 Sensor: {'Available' if dht_sensor else 'Mock mode'}")
    logger.info(f"DataLogger: {'Available' if data_logger else 'Not available'}")

    # Start data logger
    start_data_logger()

    # Start dehumidifier controller
    start_dehumidifier_controller()

    app.run(host=host, port=port, debug=debug, threaded=True, use_reloader=False)


if __name__ == '__main__':
    run_server(debug=False)
