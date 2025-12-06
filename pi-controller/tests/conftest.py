"""
pytest Configuration and Fixtures

Provides common test fixtures for GrowPi tests.
"""

import pytest
from datetime import datetime, time


@pytest.fixture
def simple_curve():
    """Simple 2-point curve for basic testing."""
    return [
        {"time": "06:00", "intensity": 0},
        {"time": "20:00", "intensity": 100},
    ]


@pytest.fixture
def full_day_curve():
    """Realistic full-day grow light curve."""
    return [
        {"time": "05:00", "intensity": 0},
        {"time": "06:00", "intensity": 30},
        {"time": "08:00", "intensity": 80},
        {"time": "12:00", "intensity": 100},
        {"time": "18:00", "intensity": 80},
        {"time": "20:00", "intensity": 30},
        {"time": "21:00", "intensity": 0},
    ]


@pytest.fixture
def midnight_wraparound_curve():
    """Curve that wraps around midnight."""
    return [
        {"time": "22:00", "intensity": 50},
        {"time": "23:30", "intensity": 20},
        {"time": "01:00", "intensity": 10},
        {"time": "03:00", "intensity": 30},
    ]


@pytest.fixture
def single_point_curve():
    """Curve with only one point."""
    return [{"time": "12:00", "intensity": 50}]


@pytest.fixture
def empty_curve():
    """Empty curve (edge case)."""
    return []


@pytest.fixture
def dawn_curve():
    """Sunrise simulation curve."""
    return [
        {"time": "04:00", "intensity": 0},
        {"time": "05:00", "intensity": 10},
        {"time": "06:00", "intensity": 40},
        {"time": "07:00", "intensity": 70},
        {"time": "08:00", "intensity": 100},
    ]


@pytest.fixture
def dusk_curve():
    """Sunset simulation curve."""
    return [
        {"time": "18:00", "intensity": 100},
        {"time": "19:00", "intensity": 70},
        {"time": "20:00", "intensity": 40},
        {"time": "21:00", "intensity": 10},
        {"time": "22:00", "intensity": 0},
    ]


def make_datetime(hour: int, minute: int = 0, second: int = 0) -> datetime:
    """
    Helper to create datetime for testing.

    Args:
        hour: Hour (0-23)
        minute: Minute (0-59)
        second: Second (0-59)

    Returns:
        datetime with today's date and specified time
    """
    return datetime.now().replace(hour=hour, minute=minute, second=second, microsecond=0)
