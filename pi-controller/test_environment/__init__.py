"""
GrowPi Test Environment Package
Provides mock hardware components for testing without Raspberry Pi.

Usage:
    from test_environment.mock_hardware import MockPWMController, MockDHT22
    from test_environment import run_local

    # Or run directly:
    python -m test_environment.run_local
"""

__version__ = "1.0.0"
__author__ = "Dennis Westermann <d.westermann@ol-mg.de>"

from .mock_hardware import (
    MockPWMController,
    MockDHT22,
    MockDatabase,
    MockDataLogger,
    MockSmartPlugController,
    get_mock_pwm_controller,
    get_mock_database
)

__all__ = [
    'MockPWMController',
    'MockDHT22',
    'MockDatabase',
    'MockDataLogger',
    'MockSmartPlugController',
    'get_mock_pwm_controller',
    'get_mock_database'
]
