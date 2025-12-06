"""
Pytest Integration Example
Demonstrates how to use pytest with the test environment.

Install:
    pip install pytest pytest-cov

Run:
    pytest pytest_example.py -v
    pytest pytest_example.py -v --cov=grow_pi
"""

import pytest
from mock_hardware import (
    MockPWMController,
    MockDHT22,
    MockDatabase,
    MockDataLogger
)


class TestMockPWMController:
    """Test suite for MockPWMController."""

    def test_initialization(self):
        """Test controller initialization."""
        controller = MockPWMController()
        assert controller._channels == {}
        assert not controller._initialized

    def test_channel_setup(self):
        """Test channel initialization."""
        controller = MockPWMController()
        channels = [type('Ch', (), {'channel': i})() for i in range(1, 5)]
        controller.initialize(channels)

        assert controller._initialized
        assert len(controller._channels) == 4
        assert all(v == 0 for v in controller._channels.values())

    def test_set_intensity(self):
        """Test setting channel intensity."""
        controller = MockPWMController()
        controller.initialize([type('Ch', (), {'channel': 1})()])

        controller.set_intensity(1, 50)
        assert controller.get_intensity(1) == 50

    def test_intensity_clamping(self):
        """Test intensity is clamped to 0-100."""
        controller = MockPWMController()
        controller.initialize([type('Ch', (), {'channel': 1})()])

        # Test over 100
        controller.set_intensity(1, 150)
        assert controller.get_intensity(1) == 100

        # Test under 0
        controller.set_intensity(1, -50)
        assert controller.get_intensity(1) == 0

    def test_get_current_state(self):
        """Test getting all channel states."""
        controller = MockPWMController()
        channels = [type('Ch', (), {'channel': i})() for i in range(1, 5)]
        controller.initialize(channels)

        controller.set_intensity(1, 25)
        controller.set_intensity(2, 50)
        controller.set_intensity(3, 75)
        controller.set_intensity(4, 100)

        state = controller.get_current_state()
        assert state == {1: 25, 2: 50, 3: 75, 4: 100}

    def test_cleanup(self):
        """Test cleanup resets state."""
        controller = MockPWMController()
        controller.initialize([type('Ch', (), {'channel': 1})()])
        controller.set_intensity(1, 50)

        controller.cleanup()
        assert controller._channels == {}
        assert not controller._initialized


class TestMockDHT22:
    """Test suite for MockDHT22."""

    def test_initialization(self):
        """Test sensor initialization with defaults."""
        sensor = MockDHT22()
        assert sensor.base_temp == 22.0
        assert sensor.base_humidity == 60.0

    def test_custom_initialization(self):
        """Test sensor initialization with custom values."""
        sensor = MockDHT22(base_temp=25.0, base_humidity=70.0)
        assert sensor.base_temp == 25.0
        assert sensor.base_humidity == 70.0

    def test_read_returns_tuple(self):
        """Test read() returns (temp, humidity) tuple."""
        sensor = MockDHT22()
        temp, humidity = sensor.read()

        assert isinstance(temp, float)
        assert isinstance(humidity, float)

    def test_read_realistic_range(self):
        """Test readings are in realistic ranges."""
        sensor = MockDHT22()
        temp, humidity = sensor.read()

        # Temperature should be within reasonable bounds
        assert 15 <= temp <= 30

        # Humidity should be within valid range
        assert 20 <= humidity <= 95

    def test_temperature_property(self):
        """Test temperature property."""
        sensor = MockDHT22()
        temp = sensor.temperature
        assert isinstance(temp, float)
        assert 15 <= temp <= 30

    def test_humidity_property(self):
        """Test humidity property."""
        sensor = MockDHT22()
        humidity = sensor.humidity
        assert isinstance(humidity, float)
        assert 20 <= humidity <= 95

    def test_variation_over_time(self):
        """Test that readings vary over multiple calls."""
        sensor = MockDHT22()
        readings = [sensor.read() for _ in range(10)]

        # Not all readings should be identical (due to noise)
        temps = [r[0] for r in readings]
        assert len(set(temps)) > 1  # At least some variation


class TestMockDatabase:
    """Test suite for MockDatabase."""

    def test_initialization(self):
        """Test database initialization."""
        db = MockDatabase()
        assert db.sensor_readings == []
        assert db.lamp_logs == []
        assert db.system_events == []

    def test_insert_sensor_reading(self):
        """Test inserting sensor reading."""
        db = MockDatabase()
        reading = type('Reading', (), {
            'sensor_type': 'temperature',
            'value': 22.5,
            'unit': '°C'
        })()

        reading_id = db.insert_sensor_reading(reading)
        assert reading_id == 1
        assert len(db.sensor_readings) == 1
        assert db.sensor_readings[0].value == 22.5

    def test_insert_lamp_state(self):
        """Test inserting lamp state."""
        db = MockDatabase()
        state = type('State', (), {
            'channel': 1,
            'name': 'Far Red',
            'intensity': 50,
            'source': 'api',
            'curve_time': None
        })()

        log_id = db.insert_lamp_state(state)
        assert log_id == 1
        assert len(db.lamp_logs) == 1
        assert db.lamp_logs[0].intensity == 50

    def test_get_sensor_readings_filter(self):
        """Test filtering sensor readings."""
        db = MockDatabase()

        # Insert multiple readings
        for i in range(5):
            reading = type('Reading', (), {
                'sensor_type': 'temperature',
                'value': 20.0 + i,
                'unit': '°C'
            })()
            db.insert_sensor_reading(reading)

        readings = db.get_sensor_readings(sensor_type='temperature')
        assert len(readings) == 5

    def test_get_sensor_readings_limit(self):
        """Test limiting sensor readings."""
        db = MockDatabase()

        # Insert 10 readings
        for i in range(10):
            reading = type('Reading', (), {
                'sensor_type': 'temperature',
                'value': 20.0,
                'unit': '°C'
            })()
            db.insert_sensor_reading(reading)

        # Request only 5
        readings = db.get_sensor_readings(limit=5)
        assert len(readings) == 5

    def test_should_log_lamp_state_deduplication(self):
        """Test lamp state deduplication."""
        db = MockDatabase()

        # First log should always be allowed
        assert db.should_log_lamp_state(1, 50, dedupe_seconds=5)

        # Insert a log
        state = type('State', (), {
            'channel': 1,
            'name': 'Test',
            'intensity': 50,
            'source': 'test',
            'curve_time': None
        })()
        db.insert_lamp_state(state)

        # Same value within dedupe window should be blocked
        assert not db.should_log_lamp_state(1, 50, dedupe_seconds=5)

        # Different value should be allowed
        assert db.should_log_lamp_state(1, 75, dedupe_seconds=5)

    def test_get_stats(self):
        """Test database statistics."""
        db = MockDatabase()
        stats = db.get_stats()

        assert 'sensor_readings_count' in stats
        assert 'lamp_logs_count' in stats
        assert stats['storage_type'] == 'in-memory'


class TestMockDataLogger:
    """Test suite for MockDataLogger."""

    def test_initialization(self):
        """Test logger initialization."""
        logger = MockDataLogger()
        assert logger.sensor_interval == 60
        assert logger.lamp_interval == 60
        assert not logger._running

    def test_custom_intervals(self):
        """Test custom logging intervals."""
        logger = MockDataLogger(sensor_interval=30, lamp_interval=45)
        assert logger.sensor_interval == 30
        assert logger.lamp_interval == 45

    def test_set_readers(self):
        """Test setting reader callbacks."""
        logger = MockDataLogger()

        def sensor_reader():
            return (22.0, 60.0)

        def lamp_reader():
            return {1: {'name': 'Test', 'intensity': 50}}

        logger.set_sensor_reader(sensor_reader)
        logger.set_lamp_reader(lamp_reader)

        assert logger._sensor_reader is not None
        assert logger._lamp_reader is not None

    def test_start_stop(self):
        """Test starting and stopping logger."""
        logger = MockDataLogger()

        logger.start()
        assert logger._running

        logger.stop()
        assert not logger._running

    def test_log_lamp_change(self):
        """Test logging lamp change."""
        logger = MockDataLogger()
        logger.log_lamp_change(1, 'Test', 50, 'api')

        logs = logger.db.lamp_logs
        assert len(logs) == 1
        assert logs[0].channel == 1
        assert logs[0].intensity == 50

    def test_get_status(self):
        """Test getting logger status."""
        logger = MockDataLogger()
        status = logger.get_status()

        assert 'running' in status
        assert 'sensor_interval' in status
        assert 'database' in status


# Fixture examples
@pytest.fixture
def mock_controller():
    """Provide a fresh MockPWMController for each test."""
    controller = MockPWMController()
    channels = [type('Ch', (), {'channel': i})() for i in range(1, 5)]
    controller.initialize(channels)
    yield controller
    controller.cleanup()


@pytest.fixture
def mock_sensor():
    """Provide a MockDHT22 sensor."""
    return MockDHT22()


@pytest.fixture
def mock_db():
    """Provide a fresh MockDatabase."""
    return MockDatabase()


# Example tests using fixtures
def test_controller_with_fixture(mock_controller):
    """Example test using controller fixture."""
    mock_controller.set_intensity(1, 50)
    assert mock_controller.get_intensity(1) == 50


def test_sensor_with_fixture(mock_sensor):
    """Example test using sensor fixture."""
    temp, humidity = mock_sensor.read()
    assert isinstance(temp, float)
    assert isinstance(humidity, float)


def test_database_with_fixture(mock_db):
    """Example test using database fixture."""
    reading = type('Reading', (), {
        'sensor_type': 'temperature',
        'value': 22.5,
        'unit': '°C'
    })()
    reading_id = mock_db.insert_sensor_reading(reading)
    assert reading_id == 1
