import sys
import types

# DataLogger imports SmartPlugController, which imports tinytuya.
# Stub tinytuya for unit tests so we can test logger health logic in isolation.
if "tinytuya" not in sys.modules:
    sys.modules["tinytuya"] = types.SimpleNamespace(OutletDevice=object, Cloud=object)
if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

from grow_pi.database.logger import DataLogger


class DummyThread:
    def __init__(self, alive: bool):
        self._alive = alive

    def is_alive(self) -> bool:
        return self._alive


def build_logger(
    *,
    running: bool,
    sensor_reader: bool,
    lamp_reader: bool,
    sensor_alive: bool,
    lamp_alive: bool,
    plug_alive: bool,
) -> DataLogger:
    logger = DataLogger.__new__(DataLogger)
    logger._running = running
    logger._sensor_reader = (lambda: (20.0, 50.0)) if sensor_reader else None
    logger._lamp_reader = (lambda: {}) if lamp_reader else None
    logger._sensor_thread = DummyThread(sensor_alive)
    logger._lamp_thread = DummyThread(lamp_alive)
    logger._plug_thread = DummyThread(plug_alive)
    return logger


def test_runtime_health_is_healthy_when_threads_alive():
    logger = build_logger(
        running=True,
        sensor_reader=True,
        lamp_reader=True,
        sensor_alive=True,
        lamp_alive=True,
        plug_alive=True,
    )

    health = logger.get_runtime_health()
    assert health["healthy"] is True
    assert health["issues"] == []


def test_runtime_health_reports_dead_required_thread():
    logger = build_logger(
        running=True,
        sensor_reader=True,
        lamp_reader=True,
        sensor_alive=False,
        lamp_alive=True,
        plug_alive=True,
    )

    health = logger.get_runtime_health()
    assert health["healthy"] is False
    assert "sensor_thread_dead" in health["issues"]


def test_runtime_health_does_not_flag_when_logger_stopped():
    logger = build_logger(
        running=False,
        sensor_reader=True,
        lamp_reader=True,
        sensor_alive=False,
        lamp_alive=False,
        plug_alive=False,
    )

    health = logger.get_runtime_health()
    assert health["healthy"] is True
    assert health["issues"] == []
