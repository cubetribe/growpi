#!/usr/bin/env python3
"""
GrowPi Flask REST API
Provides HTTP endpoints for lamp control, sensor reading, and data logging.

Endpoints:
    GET  /api/status      - Get all lamp values and temperature
    POST /api/lamp/<ch>   - Set lamp intensity (1-4)
    GET  /api/temperature - Get current temperature/humidity
    GET  /api/logs/sensors - Get sensor history
    GET  /api/logs/lamps   - Get lamp state history
    GET  /api/logs/stats   - Get logging statistics
    GET  /               - Serve frontend HTML
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os
import sys
import atexit
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

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
            3: LampChannel(3, "Cool White", 12, "#88ddff"),
            4: LampChannel(4, "UV", 18, "#cc66ff")
        }

load_lamp_channels()

# API Configuration
API_VERSION = "6.8.0"  # GrowPi production version
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
    app.register_blueprint(costs_bp)
    app.register_blueprint(dehumidifier_bp)
    app.register_blueprint(curves_bp)
    logging.info("Registered costs_bp, dehumidifier_bp, and curves_bp blueprints")
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
    try:
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        logger.info("DHT22 Sensor initialized on GPIO-4")
    except Exception as e:
        logger.error(f"Failed to initialize DHT22: {e}")

# Initialize DataLogger
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

# Initialize ModeManager
if MODE_MANAGER_AVAILABLE:
    try:
        mode_manager = get_mode_manager()
        logger.info(f"ModeManager initialized (current mode: {mode_manager.get_mode()})")
    except Exception as e:
        logger.error(f"Failed to initialize ModeManager: {e}")

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


# Cache for DHT22 readings (sensor needs 2s between reads)
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0}
DHT_CACHE_SECONDS = 30  # Minimum seconds between sensor reads (erhöht für CPU-Optimierung)


def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    """Read temperature and humidity from DHT22 with caching and retry"""
    global _dht_cache
    import time

    if dht_sensor is None:
        # Return mock data for testing
        import random
        return (22.0 + random.uniform(-2, 2), 60.0 + random.uniform(-5, 5))

    # Return cached value if recent enough
    now = time.time()
    if now - _dht_cache["timestamp"] < DHT_CACHE_SECONDS:
        if _dht_cache["temp"] is not None:
            return (_dht_cache["temp"], _dht_cache["humidity"])

    # Try up to 3 times to read the sensor
    for attempt in range(3):
        try:
            temp = dht_sensor.temperature
            humidity = dht_sensor.humidity
            if temp is not None and humidity is not None:
                _dht_cache["temp"] = round(temp, 1)
                _dht_cache["humidity"] = round(humidity, 1)
                _dht_cache["timestamp"] = now
                return (_dht_cache["temp"], _dht_cache["humidity"])
        except RuntimeError as e:
            logger.warning(f"DHT22 read attempt {attempt+1}/3: {e}")
            if attempt < 2:
                time.sleep(0.5)

    # Return last known good value if available
    if _dht_cache["temp"] is not None:
        logger.info("Returning cached DHT22 value")
        return (_dht_cache["temp"], _dht_cache["humidity"])

    return (None, None)


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


# Register shutdown handler
atexit.register(stop_data_logger)


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
        pwm_controller.set_intensity(channel, intensity)
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

@app.route('/api/logs/sensors', methods=['GET'])
def get_sensor_logs():
    """Get sensor reading history"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        sensor_type = request.args.get('type')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        readings = db.get_sensor_readings(sensor_type=sensor_type, hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "readings": [r.to_dict() for r in readings],
            "count": len(readings),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_sensor_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/logs/lamps', methods=['GET'])
def get_lamp_logs():
    """Get lamp state history"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        channel = request.args.get('channel', type=int)
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        logs = db.get_lamp_state_log(channel=channel, hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "logs": [l.to_dict() for l in logs],
            "count": len(logs),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_lamp_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/logs/events', methods=['GET'])
def get_event_logs():
    """Get system event history"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        event_type = request.args.get('type')
        severity = request.args.get('severity')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))

        db = get_database()
        events = db.get_system_events(
            event_type=event_type,
            severity=severity,
            hours=hours,
            limit=limit
        )

        return jsonify(create_response(True, {
            "events": [e.to_dict() for e in events],
            "count": len(events),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_event_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/logs/plugs', methods=['GET'])
def get_plug_logs():
    """Get smart plug history"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        logs = db.get_plug_logs(hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "data": [l.to_dict() for l in logs],
            "count": len(logs),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_plug_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/logs/stats', methods=['GET'])
def get_log_stats():
    """Get logging statistics"""
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        status = data_logger.get_status()
        return jsonify(create_response(True, status))

    except Exception as e:
        logger.error(f"Error in get_log_stats: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Curve API Routes
# ============================================================================

@app.route('/api/curves', methods=['GET'])
def get_all_curves():
    """Get all lamp curves"""
    if not CURVE_AVAILABLE or not curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        curves = []
        for channel in range(1, 5):
            curve_data = curve_controller.get_curve(channel)
            curves.append({
                "channel": channel,
                "name": curve_controller.get_channel_name(channel),
                "enabled": curve_controller.is_enabled(channel),
                "curve": curve_data or [],
                "current_intensity": curve_controller.get_intensity(channel)
            })

        return jsonify(create_response(True, {
            "curves": curves,
            "status": curve_controller.get_status()
        }))

    except Exception as e:
        logger.error(f"Error in get_all_curves: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/curves/<int:channel>', methods=['GET'])
def get_curve(channel: int):
    """Get curve for a specific channel"""
    if not CURVE_AVAILABLE or not curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    if channel not in LAMP_CHANNELS:
        return jsonify(create_response(False, error=f"Invalid channel: {channel}")), 400

    try:
        curve_data = curve_controller.get_curve(channel)
        return jsonify(create_response(True, {
            "channel": channel,
            "name": curve_controller.get_channel_name(channel),
            "enabled": curve_controller.is_enabled(channel),
            "curve": curve_data or [],
            "current_intensity": curve_controller.get_intensity(channel)
        }))

    except Exception as e:
        logger.error(f"Error in get_curve: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/curves/<int:channel>', methods=['PUT'])
def update_curve(channel: int):
    """Update curve for a specific channel"""
    if not CURVE_AVAILABLE or not curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    if channel not in LAMP_CHANNELS:
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
        success = curve_controller.update_curve(channel, curve_points, enabled)
        if not success:
            return jsonify(create_response(False, error="Failed to update curve")), 500

        # Log the change
        if data_logger:
            data_logger.log_event(
                'curve_update',
                'info',
                f'Curve updated for {curve_controller.get_channel_name(channel)}',
                {'channel': channel, 'points': len(curve_points), 'enabled': enabled}
            )

        logger.info(f"Updated curve for channel {channel}: {len(curve_points)} points")

        return jsonify(create_response(True, {
            "channel": channel,
            "name": curve_controller.get_channel_name(channel),
            "enabled": enabled,
            "curve": curve_points,
            "current_intensity": curve_controller.get_intensity(channel)
        }))

    except Exception as e:
        logger.error(f"Error in update_curve: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/curves/preview', methods=['GET'])
def get_curve_preview():
    """Get 24h preview of all curve intensities"""
    if not CURVE_AVAILABLE or not curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        from datetime import datetime

        preview = []
        for hour in range(24):
            test_time = datetime.now().replace(hour=hour, minute=0, second=0, microsecond=0)
            intensities = curve_controller.get_current_intensities(test_time)
            preview.append({
                "hour": hour,
                "time": f"{hour:02d}:00",
                "intensities": intensities
            })

        return jsonify(create_response(True, {
            "preview": preview,
            "channels": {
                ch: curve_controller.get_channel_name(ch)
                for ch in range(1, 5)
            }
        }))

    except Exception as e:
        logger.error(f"Error in get_curve_preview: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@app.route('/api/curves/intensities', methods=['GET'])
def get_current_intensities():
    """Get current interpolated intensities for all channels"""
    if not CURVE_AVAILABLE or not curve_controller:
        return jsonify(create_response(False, error="Curves not available")), 503

    try:
        intensities = curve_controller.get_current_intensities()
        return jsonify(create_response(True, {
            "intensities": intensities,
            "channels": {
                ch: {
                    "name": curve_controller.get_channel_name(ch),
                    "enabled": curve_controller.is_enabled(ch),
                    "intensity": intensities.get(ch, 0)
                }
                for ch in range(1, 5)
            },
            "timestamp": datetime.now().isoformat()
        }))

    except Exception as e:
        logger.error(f"Error in get_current_intensities: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Mode API Routes
# ============================================================================

def _apply_curve_values() -> dict:
    """Apply current curve values to lamps. Returns applied intensities."""
    applied = {}
    if curve_controller and pwm_controller:
        intensities = curve_controller.get_current_intensities()
        for channel, intensity in intensities.items():
            pwm_controller.set_intensity(channel, intensity)
            applied[channel] = intensity
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
    """Get list of timelapse images"""
    camera = _get_camera()
    if not camera:
        return jsonify(create_response(False, error="Camera not available")), 503

    try:
        limit = int(request.args.get('limit', 50))
        images = camera.get_timelapse_images(limit)

        return jsonify(create_response(True, {
            "images": images,
            "count": len(images)
        }))

    except Exception as e:
        logger.error(f"Error in get_timelapse_images: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# Health & Info
# ============================================================================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": API_VERSION,
        "pwm_available": pwm_controller is not None,
        "sensor_available": dht_sensor is not None or not DHT_AVAILABLE,
        "logging_available": DB_AVAILABLE and data_logger is not None,
        "logging_running": data_logger._running if data_logger else False,
        "curves_available": CURVE_AVAILABLE and curve_controller is not None
    })


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

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_server(debug=True)
