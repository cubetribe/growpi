#!/usr/bin/env python3
"""
Validation Script for Test Environment
Verifies that all mock components work correctly.

Usage:
    python validate.py
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from test_environment.mock_hardware import (
    MockPWMController,
    MockDHT22,
    MockDatabase,
    MockDataLogger,
    MockSmartPlugController
)


def validate_pwm_controller():
    """Validate MockPWMController."""
    print("\n[1/5] Validating MockPWMController...")

    try:
        # Initialize
        controller = MockPWMController()
        channels = [type('Ch', (), {'channel': i})() for i in range(1, 5)]
        controller.initialize(channels)
        assert controller._initialized, "Failed: Not initialized"

        # Set intensities
        controller.set_intensity(1, 50)
        controller.set_intensity(2, 75)
        assert controller.get_intensity(1) == 50, "Failed: Wrong intensity"
        assert controller.get_intensity(2) == 75, "Failed: Wrong intensity"

        # Get state
        state = controller.get_current_state()
        assert len(state) == 4, "Failed: Wrong number of channels"

        # Cleanup
        controller.cleanup()
        assert not controller._initialized, "Failed: Still initialized after cleanup"

        print("  ✓ PASSED")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def validate_dht22():
    """Validate MockDHT22."""
    print("\n[2/5] Validating MockDHT22...")

    try:
        # Initialize
        sensor = MockDHT22()

        # Read data
        temp, humidity = sensor.read()
        assert isinstance(temp, float), "Failed: Temp not float"
        assert isinstance(humidity, float), "Failed: Humidity not float"
        assert 15 <= temp <= 30, f"Failed: Temp out of range ({temp})"
        assert 20 <= humidity <= 95, f"Failed: Humidity out of range ({humidity})"

        # Test properties
        temp2 = sensor.temperature
        humidity2 = sensor.humidity
        assert isinstance(temp2, float), "Failed: Property not float"

        # Test variation
        readings = [sensor.read() for _ in range(5)]
        temps = [r[0] for r in readings]
        assert len(set(temps)) > 1, "Failed: No variation in readings"

        print(f"  Sample reading: {temp:.1f}°C, {humidity:.1f}%")
        print("  ✓ PASSED")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def validate_database():
    """Validate MockDatabase."""
    print("\n[3/5] Validating MockDatabase...")

    try:
        # Initialize
        db = MockDatabase()

        # Insert sensor reading
        reading = type('Reading', (), {
            'sensor_type': 'temperature',
            'value': 22.5,
            'unit': '°C'
        })()
        reading_id = db.insert_sensor_reading(reading)
        assert reading_id == 1, "Failed: Wrong reading ID"

        # Insert lamp state
        state = type('State', (), {
            'channel': 1,
            'name': 'Test',
            'intensity': 50,
            'source': 'test',
            'curve_time': None
        })()
        state_id = db.insert_lamp_state(state)
        assert state_id == 1, "Failed: Wrong state ID"

        # Query data
        readings = db.get_sensor_readings()
        assert len(readings) == 1, "Failed: Wrong number of readings"

        states = db.get_lamp_state_log()
        assert len(states) == 1, "Failed: Wrong number of states"

        # Test deduplication
        assert db.should_log_lamp_state(1, 50, 5) == False, "Failed: Deduplication not working"
        assert db.should_log_lamp_state(1, 75, 5) == True, "Failed: Deduplication blocking different value"

        # Get stats
        stats = db.get_stats()
        assert stats['sensor_readings_count'] == 1, "Failed: Wrong stats"
        assert stats['storage_type'] == 'in-memory', "Failed: Wrong storage type"

        print(f"  Database stats: {stats}")
        print("  ✓ PASSED")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def validate_data_logger():
    """Validate MockDataLogger."""
    print("\n[4/5] Validating MockDataLogger...")

    try:
        # Initialize
        logger = MockDataLogger(sensor_interval=30, lamp_interval=45)
        assert logger.sensor_interval == 30, "Failed: Wrong sensor interval"
        assert logger.lamp_interval == 45, "Failed: Wrong lamp interval"

        # Set readers
        def sensor_reader():
            return (22.0, 60.0)

        def lamp_reader():
            return {1: {'name': 'Test', 'intensity': 50}}

        logger.set_sensor_reader(sensor_reader)
        logger.set_lamp_reader(lamp_reader)
        assert logger._sensor_reader is not None, "Failed: Sensor reader not set"

        # Start/stop
        logger.start()
        assert logger._running, "Failed: Not running after start"

        logger.stop()
        assert not logger._running, "Failed: Still running after stop"

        # Log event
        logger.log_lamp_change(1, 'Test', 50, 'api')
        logs = logger.db.lamp_logs
        assert len(logs) == 1, "Failed: Event not logged"

        # Get status
        status = logger.get_status()
        assert 'running' in status, "Failed: No status"
        assert 'database' in status, "Failed: No database stats"

        print(f"  Logger status: running={status['running']}, db_entries={len(logs)}")
        print("  ✓ PASSED")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def validate_smart_plug_controller():
    """Validate MockSmartPlugController."""
    print("\n[5/5] Validating MockSmartPlugController...")

    try:
        # Initialize
        controller = MockSmartPlugController()

        # Get plugs
        plugs = controller.get_plugs()
        assert len(plugs) > 0, "Failed: No plugs found"
        assert plugs[0]['device_id'] == 'mock_plug_1', "Failed: Wrong device ID"

        # Get status
        device_id = plugs[0]['device_id']
        status = controller.get_status(device_id)
        assert status is not None, "Failed: No status"
        assert 'power' in status, "Failed: No power in status"
        assert 'voltage' in status, "Failed: No voltage in status"

        # Turn on/off
        assert controller.turn_on(device_id), "Failed: Turn on failed"
        assert controller.turn_off(device_id), "Failed: Turn off failed"

        print(f"  Sample status: {status['power']:.1f}W, {status['voltage']:.1f}V")
        print("  ✓ PASSED")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def validate_imports():
    """Validate that all imports work."""
    print("\n[BONUS] Validating imports...")

    try:
        from test_environment import (
            MockPWMController,
            MockDHT22,
            MockDatabase,
            MockDataLogger,
            get_mock_pwm_controller,
            get_mock_database
        )

        # Test singletons
        pwm1 = get_mock_pwm_controller()
        pwm2 = get_mock_pwm_controller()
        assert pwm1 is pwm2, "Failed: Singleton not working for PWM"

        db1 = get_mock_database()
        db2 = get_mock_database()
        assert db1 is db2, "Failed: Singleton not working for DB"

        print("  ✓ All imports working")
        print("  ✓ Singletons working correctly")
        return True

    except Exception as e:
        print(f"  ✗ FAILED: {e}")
        return False


def main():
    """Run all validations."""
    print("=" * 60)
    print("GROWPI TEST ENVIRONMENT VALIDATION")
    print("=" * 60)

    results = {
        'PWM Controller': validate_pwm_controller(),
        'DHT22 Sensor': validate_dht22(),
        'Database': validate_database(),
        'Data Logger': validate_data_logger(),
        'Smart Plug Controller': validate_smart_plug_controller(),
        'Imports': validate_imports()
    }

    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {name:25} {status}")

    print("=" * 60)
    print(f"RESULT: {passed}/{total} components validated")
    print("=" * 60)

    if passed == total:
        print("\n🎉 All validations PASSED! Test environment is ready to use.")
        print("\nNext steps:")
        print("  1. python run_local.py              # Start server")
        print("  2. python test_api.py               # Run API tests")
        print("  3. pytest pytest_example.py -v      # Run unit tests")
        return 0
    else:
        print("\n❌ Some validations FAILED. Please check the errors above.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
