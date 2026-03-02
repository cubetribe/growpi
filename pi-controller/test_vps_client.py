#!/usr/bin/env python3
"""
Test Script für GrowPi VPS Client
==================================

Testet die Kommunikation mit dem VPS-Server.

Usage:
    python test_vps_client.py              # Test gegen Production-Server
    python test_vps_client.py --local      # Test gegen localhost:3001
"""

import argparse
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from grow_pi.api.client import GrowPiClient, SyncConfig


def test_registration(client: GrowPiClient) -> bool:
    """Test Registration Endpoint"""
    print("\n" + "=" * 50)
    print("TEST 1: REGISTRATION")
    print("=" * 50)

    try:
        result = client.register(
            serial='test-pi-12345',
            hostname='test-growpi',
            version='1.0.0'
        )

        print(f"✅ Registration successful!")
        print(f"   Pi ID: {result.get('pi_id')}")
        print(f"   Token: {result.get('api_token', 'N/A')[:20]}...")
        print(f"   Zone: {result.get('zone', {}).get('name', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Registration failed: {e}")
        return False


def test_heartbeat(client: GrowPiClient) -> bool:
    """Test Heartbeat Endpoint"""
    print("\n" + "=" * 50)
    print("TEST 2: HEARTBEAT")
    print("=" * 50)

    try:
        result = client.send_heartbeat(
            uptime_seconds=3600,
            version='1.0.0',
            ip_local='<DEVICE_IP>',
            last_sensor_read=datetime.now()
        )

        print(f"✅ Heartbeat successful!")
        print(f"   Status: {result.get('status')}")
        print(f"   Commands Pending: {result.get('commands_pending', False)}")
        print(f"   Server Time: {result.get('server_time', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Heartbeat failed: {e}")
        return False


def test_sensor_upload(client: GrowPiClient) -> bool:
    """Test Sensor Upload Endpoint"""
    print("\n" + "=" * 50)
    print("TEST 3: SENSOR UPLOAD")
    print("=" * 50)

    try:
        readings = [
            {
                'timestamp': datetime.now().isoformat(),
                'temperature': 22.5,
                'humidity': 65.0,
                'soil_moisture': 45.0
            },
            {
                'timestamp': datetime.now().isoformat(),
                'temperature': 22.6,
                'humidity': 64.5,
                'soil_moisture': 44.8
            }
        ]

        result = client.send_readings(readings)

        print(f"✅ Sensor upload successful!")
        print(f"   Synced: {result.get('synced')}")
        print(f"   Skipped: {result.get('skipped')}")
        print(f"   Last Sync: {result.get('last_sync', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Sensor upload failed: {e}")
        return False


def test_lamp_status(client: GrowPiClient) -> bool:
    """Test Lamp Status Endpoint"""
    print("\n" + "=" * 50)
    print("TEST 4: LAMP STATUS")
    print("=" * 50)

    try:
        channels = [
            {'channel': 1, 'name': 'Far Red', 'intensity': 75, 'enabled': True},
            {'channel': 2, 'name': 'Cool White', 'intensity': 50, 'enabled': True},
            {'channel': 3, 'name': 'Warm White', 'intensity': 50, 'enabled': True},
            {'channel': 4, 'name': 'UV', 'intensity': 0, 'enabled': False}
        ]

        result = client.send_lamp_status(channels, 'test-hash-abc123')

        print(f"✅ Lamp status sent!")
        print(f"   Status: {result.get('status')}")
        print(f"   Timestamp: {result.get('timestamp', 'N/A')}")

        return True

    except Exception as e:
        print(f"❌ Lamp status failed: {e}")
        return False


def test_command_polling(client: GrowPiClient) -> bool:
    """Test Command Polling Endpoint"""
    print("\n" + "=" * 50)
    print("TEST 5: COMMAND POLLING")
    print("=" * 50)

    try:
        commands = client.get_commands()

        print(f"✅ Command polling successful!")
        print(f"   Commands: {len(commands)}")

        for i, cmd in enumerate(commands, 1):
            print(f"\n   Command {i}:")
            print(f"     ID: {cmd.get('id')}")
            print(f"     Type: {cmd.get('type')}")
            print(f"     Payload: {cmd.get('payload')}")
            print(f"     Created: {cmd.get('created_at')}")

        # Test ACK für erstes Command (falls vorhanden)
        if commands:
            cmd_id = commands[0]['id']
            print(f"\n   Testing ACK for command {cmd_id}...")

            ack_result = client.ack_command(
                cmd_id,
                success=True,
                result={'test': 'executed'}
            )

            print(f"   ✅ ACK successful: {ack_result.get('status')}")

        return True

    except Exception as e:
        print(f"❌ Command polling failed: {e}")
        return False


def main():
    """Run all tests"""
    parser = argparse.ArgumentParser(description='Test GrowPi VPS Client')
    parser.add_argument(
        '--local',
        action='store_true',
        help='Test against localhost:3001 instead of production'
    )
    parser.add_argument(
        '--server',
        type=str,
        help='Custom server URL'
    )
    args = parser.parse_args()

    # Configure server
    if args.server:
        server_url = args.server
    elif args.local:
        server_url = 'http://localhost:3001'
    else:
        server_url = 'https://your-growpi-host.example.com'

    print("=" * 50)
    print("GrowPi VPS Client Test Suite")
    print("=" * 50)
    print(f"Server: {server_url}")
    print()

    # Create client
    config = SyncConfig(
        server_url=server_url,
        timeout=10
    )
    client = GrowPiClient(config)

    # Run tests
    results = []

    # Test 1: Registration
    results.append(('Registration', test_registration(client)))

    # Nur weitermachen wenn Registration erfolgreich war
    if not results[0][1]:
        print("\n❌ Registration failed - skipping remaining tests")
        sys.exit(1)

    # Test 2: Heartbeat
    results.append(('Heartbeat', test_heartbeat(client)))

    # Test 3: Sensor Upload
    results.append(('Sensor Upload', test_sensor_upload(client)))

    # Test 4: Lamp Status
    results.append(('Lamp Status', test_lamp_status(client)))

    # Test 5: Command Polling
    results.append(('Command Polling', test_command_polling(client)))

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")

    total = len(results)
    passed = sum(1 for _, success in results if success)

    print(f"\nTotal: {passed}/{total} tests passed")

    # Exit code
    sys.exit(0 if passed == total else 1)


if __name__ == '__main__':
    main()
