#!/usr/bin/env python3
"""
GrowPi Flask REST API
Provides HTTP endpoints for lamp control and sensor reading.

Endpoints:
    GET  /api/status      - Get all lamp values and temperature
    POST /api/lamp/<ch>   - Set lamp intensity (1-4)
    GET  /api/temperature - Get current temperature/humidity
    GET  /               - Serve frontend HTML
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import logging
import os
import sys
from typing import Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lamps.pwm_controller import PWMController

# Try to import DHT22 sensor
DHT_AVAILABLE = False
try:
    import board
    import adafruit_dht
    DHT_AVAILABLE = True
except ImportError:
    logging.warning("adafruit_dht not available - sensor will return mock data")


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
        from config import load_config
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
API_VERSION = "1.0.0"
API_PORT = 5000
API_HOST = "0.0.0.0"

# Static files directory
STATIC_DIR = os.path.join(os.path.dirname(__file__), 'static')


# ============================================================================
# Flask Application Setup
# ============================================================================

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Hardware Initialization
# ============================================================================

# Initialize PWM Controller
pwm_controller = None
try:
    pwm_controller = PWMController()
    # Initialize with channel configs
    from config import load_config
    config = load_config()
    pwm_controller.initialize(config.lamps.channels)
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
DHT_CACHE_SECONDS = 3  # Minimum seconds between sensor reads


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


# ============================================================================
# API Routes
# ============================================================================

@app.route('/')
def serve_frontend():
    """Serve the frontend HTML"""
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
            "version": API_VERSION
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


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "version": API_VERSION,
        "pwm_available": pwm_controller is not None,
        "sensor_available": dht_sensor is not None or not DHT_AVAILABLE
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

    app.run(host=host, port=port, debug=debug, threaded=True)


if __name__ == '__main__':
    run_server(debug=True)
