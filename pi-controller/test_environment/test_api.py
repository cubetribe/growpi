#!/usr/bin/env python3
"""
API Test Suite for GrowPi
Tests all API endpoints with mock hardware.

Usage:
    # Start server first: python run_local.py
    # Then run tests: python test_api.py
    # Or use pytest: pytest test_api.py -v
"""

import requests
import time
import json
from typing import Dict, Any

# API Base URL
BASE_URL = "http://localhost:5000"


class TestAPI:
    """API test suite."""

    @staticmethod
    def test_health():
        """Test health check endpoint."""
        print("\n[TEST] Health Check")
        response = requests.get(f"{BASE_URL}/api/health")
        assert response.status_code == 200
        data = response.json()
        print(f"  Status: {data['status']}")
        print(f"  Version: {data['version']}")
        assert data['status'] == 'healthy'
        print("  ✓ PASSED")

    @staticmethod
    def test_status():
        """Test system status endpoint."""
        print("\n[TEST] System Status")
        response = requests.get(f"{BASE_URL}/api/status")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        assert 'lamps' in data
        assert 'temperature' in data
        assert 'humidity' in data
        print(f"  Temperature: {data['temperature']}°C")
        print(f"  Humidity: {data['humidity']}%")
        print(f"  Lamps: {len(data['lamps'])} channels")
        print("  ✓ PASSED")

    @staticmethod
    def test_set_lamp():
        """Test setting lamp intensity."""
        print("\n[TEST] Set Lamp Intensity")
        for channel in range(1, 5):
            intensity = channel * 25  # 25, 50, 75, 100
            response = requests.post(
                f"{BASE_URL}/api/lamp/{channel}",
                json={'intensity': intensity}
            )
            assert response.status_code == 200
            data = response.json()
            assert data['success']
            assert data['channel'] == channel
            assert data['intensity'] == intensity
            print(f"  Channel {channel}: {intensity}% ✓")
        print("  ✓ PASSED")

    @staticmethod
    def test_temperature():
        """Test temperature endpoint."""
        print("\n[TEST] Temperature Reading")
        response = requests.get(f"{BASE_URL}/api/temperature")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        assert 'temperature' in data
        assert 'humidity' in data
        print(f"  Temperature: {data['temperature']}{data['unit_temperature']}")
        print(f"  Humidity: {data['humidity']}{data['unit_humidity']}")
        print("  ✓ PASSED")

    @staticmethod
    def test_invalid_lamp_channel():
        """Test invalid lamp channel."""
        print("\n[TEST] Invalid Lamp Channel")
        response = requests.post(
            f"{BASE_URL}/api/lamp/99",
            json={'intensity': 50}
        )
        assert response.status_code == 400
        data = response.json()
        assert not data['success']
        assert 'error' in data
        print(f"  Error: {data['error']}")
        print("  ✓ PASSED")

    @staticmethod
    def test_invalid_intensity():
        """Test invalid intensity value."""
        print("\n[TEST] Invalid Intensity")
        response = requests.post(
            f"{BASE_URL}/api/lamp/1",
            json={'intensity': 150}  # > 100
        )
        assert response.status_code == 400
        data = response.json()
        assert not data['success']
        print(f"  Error: {data['error']}")
        print("  ✓ PASSED")

    @staticmethod
    def test_mode_switching():
        """Test mode switching."""
        print("\n[TEST] Mode Switching")

        # Get current mode
        response = requests.get(f"{BASE_URL}/api/mode")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        print(f"  Current mode: {data['mode']}")

        # Switch to manual
        response = requests.post(
            f"{BASE_URL}/api/mode",
            json={'mode': 'manual'}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        assert data['mode'] == 'manual'
        print("  Switched to manual ✓")

        # Switch back to auto
        response = requests.post(
            f"{BASE_URL}/api/mode",
            json={'mode': 'auto'}
        )
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        assert data['mode'] == 'auto'
        print("  Switched to auto ✓")
        print("  ✓ PASSED")

    @staticmethod
    def test_sensor_logs():
        """Test sensor logging endpoints."""
        print("\n[TEST] Sensor Logs")

        # Wait for some data to be logged
        print("  Waiting 5s for data logging...")
        time.sleep(5)

        response = requests.get(f"{BASE_URL}/api/logs/sensors?hours=1")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        print(f"  Sensor readings: {data['count']}")

        if data['count'] > 0:
            latest = data['readings'][0]
            print(f"  Latest: {latest['sensor_type']} = {latest['value']}{latest['unit']}")

        print("  ✓ PASSED")

    @staticmethod
    def test_lamp_logs():
        """Test lamp logging endpoints."""
        print("\n[TEST] Lamp Logs")
        response = requests.get(f"{BASE_URL}/api/logs/lamps?hours=1")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        print(f"  Lamp logs: {data['count']}")

        if data['count'] > 0:
            latest = data['logs'][0]
            print(f"  Latest: ch{latest['channel']} = {latest['intensity']}% [{latest['source']}]")

        print("  ✓ PASSED")

    @staticmethod
    def test_log_stats():
        """Test logging statistics."""
        print("\n[TEST] Logging Statistics")
        response = requests.get(f"{BASE_URL}/api/logs/stats")
        assert response.status_code == 200
        data = response.json()
        assert data['success']
        print(f"  Running: {data['running']}")
        print(f"  Sensor interval: {data['sensor_interval']}s")
        print(f"  Database: {data['database']}")
        print("  ✓ PASSED")


def run_all_tests():
    """Run all tests."""
    print("=" * 60)
    print("GROWPI API TEST SUITE")
    print("=" * 60)
    print(f"Testing: {BASE_URL}")

    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/health", timeout=2)
        if response.status_code != 200:
            print("\n❌ ERROR: Server not responding correctly")
            print("   Start server first: python run_local.py")
            return False
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Cannot connect to server")
        print("   Start server first: python run_local.py")
        return False

    # Run tests
    tests = [
        TestAPI.test_health,
        TestAPI.test_status,
        TestAPI.test_set_lamp,
        TestAPI.test_temperature,
        TestAPI.test_invalid_lamp_channel,
        TestAPI.test_invalid_intensity,
        TestAPI.test_mode_switching,
        TestAPI.test_sensor_logs,
        TestAPI.test_lamp_logs,
        TestAPI.test_log_stats
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"  ❌ FAILED: {e}")
        except Exception as e:
            failed += 1
            print(f"  ❌ ERROR: {e}")

    # Summary
    print("\n" + "=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    exit(0 if success else 1)
