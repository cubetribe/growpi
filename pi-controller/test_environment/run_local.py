#!/usr/bin/env python3
"""
GrowPi Local Test Runner
Starts Flask API in simulation mode WITHOUT Raspberry Pi hardware.

Usage:
    python run_local.py
    python run_local.py --port 8000
    python run_local.py --debug
"""

import os
import sys
import logging
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Enable simulation mode BEFORE any imports
os.environ['GROWPI_SIMULATION_MODE'] = '1'

# Import mock hardware components
from test_environment.mock_hardware import (
    MockPWMController,
    MockDHT22,
    MockDatabase,
    MockDataLogger,
    MockSmartPlugController,
    get_mock_pwm_controller,
    get_mock_database
)

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def patch_imports():
    """
    Monkey-patch imports to use mock hardware.
    This allows the real API code to run without modification.
    """
    import sys

    # Mock pigpio module
    class MockPigpio:
        """Mock pigpio module."""
        OUTPUT = 1
        PWM = 2

        class pi:
            """Mock pi class."""
            def __init__(self):
                pass

            def set_mode(self, pin, mode):
                pass

            def set_PWM_frequency(self, pin, freq):
                pass

            def set_PWM_range(self, pin, range_val):
                pass

            def set_PWM_dutycycle(self, pin, duty):
                pass

            def stop(self):
                pass

    sys.modules['pigpio'] = MockPigpio()

    # Mock adafruit_dht module
    class MockAdafruitDHT:
        """Mock adafruit_dht module."""
        class DHT22:
            def __init__(self, pin, use_pulseio=False):
                self._mock_sensor = MockDHT22()

            @property
            def temperature(self):
                return self._mock_sensor.temperature

            @property
            def humidity(self):
                return self._mock_sensor.humidity

    sys.modules['adafruit_dht'] = MockAdafruitDHT()

    # Mock board module
    class MockBoard:
        """Mock board module."""
        D4 = 4

    sys.modules['board'] = MockBoard()

    logger.info("Patched hardware imports (SIMULATION MODE)")


def setup_test_environment():
    """Setup test environment with mock components."""
    logger.info("=" * 60)
    logger.info("GROWPI TEST ENVIRONMENT")
    logger.info("=" * 60)
    logger.info("Simulation Mode: ENABLED")
    logger.info("Hardware: ALL MOCKED")
    logger.info("Database: IN-MEMORY")
    logger.info("=" * 60)

    # Patch imports first
    patch_imports()

    # Replace real components with mocks in grow_pi modules
    try:
        # Replace PWM Controller
        import grow_pi.lamps.pwm_controller as pwm_module
        pwm_module.PWMController = MockPWMController
        pwm_module.get_pwm_controller = get_mock_pwm_controller
        logger.info("Patched: PWMController -> MockPWMController")

        # Replace Database
        import grow_pi.database.db as db_module
        db_module.Database = MockDatabase
        db_module.get_database = get_mock_database
        logger.info("Patched: Database -> MockDatabase")

        # Replace DataLogger
        import grow_pi.database.logger as logger_module
        logger_module.DataLogger = MockDataLogger
        logger.info("Patched: DataLogger -> MockDataLogger")

        # Replace SmartPlugController
        import grow_pi.lamps.smart_plug_controller as plug_module
        plug_module.SmartPlugController = MockSmartPlugController
        logger.info("Patched: SmartPlugController -> MockSmartPlugController")

    except ImportError as e:
        logger.warning(f"Could not patch some modules: {e}")
        logger.warning("This is normal if modules don't exist yet")


def start_server(host='0.0.0.0', port=5000, debug=True):
    """
    Start Flask server with mock hardware.

    Args:
        host: Host address
        port: Port number
        debug: Enable debug mode
    """
    setup_test_environment()

    # Import API module AFTER patching
    from grow_pi.web import api

    # Override config path to use test config
    test_config_path = Path(__file__).parent / 'config_test.yaml'
    if test_config_path.exists():
        os.environ['GROWPI_CONFIG_PATH'] = str(test_config_path)
        logger.info(f"Using test config: {test_config_path}")

    # Start server
    logger.info(f"Starting server on http://{host}:{port}")
    logger.info("Press Ctrl+C to stop")
    logger.info("=" * 60)

    try:
        api.run_server(host=host, port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info("\nServer stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        sys.exit(1)


def run_tests():
    """Run basic functionality tests."""
    logger.info("Running basic tests...")

    # Test MockPWMController
    pwm = MockPWMController()
    pwm.initialize([type('Ch', (), {'channel': i}) for i in range(1, 5)])
    pwm.set_intensity(1, 50)
    assert pwm.get_intensity(1) == 50, "PWM test failed"
    logger.info("✓ MockPWMController test passed")

    # Test MockDHT22
    dht = MockDHT22()
    temp, humidity = dht.read()
    assert 15 <= temp <= 30, "DHT22 temp out of range"
    assert 30 <= humidity <= 90, "DHT22 humidity out of range"
    logger.info(f"✓ MockDHT22 test passed (temp={temp}, humidity={humidity})")

    # Test MockDatabase
    db = MockDatabase()
    reading = type('Reading', (), {
        'sensor_type': 'temperature',
        'value': 22.5,
        'unit': '°C'
    })()
    reading_id = db.insert_sensor_reading(reading)
    assert reading_id == 1, "Database insert failed"
    readings = db.get_sensor_readings()
    assert len(readings) == 1, "Database query failed"
    logger.info("✓ MockDatabase test passed")

    logger.info("All tests passed!")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='GrowPi Local Test Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host address')
    parser.add_argument('--port', type=int, default=5000, help='Port number')
    parser.add_argument('--debug', action='store_true', default=True, help='Debug mode')
    parser.add_argument('--test', action='store_true', help='Run tests only')

    args = parser.parse_args()

    if args.test:
        run_tests()
    else:
        start_server(host=args.host, port=args.port, debug=args.debug)


if __name__ == '__main__':
    main()
