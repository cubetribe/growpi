#!/usr/bin/env python3
"""
DHT22 Hardware Diagnostic Script
=================================

Purpose: Test DHT22 sensor directly without GrowPi system running.
Run this on the Raspberry Pi to diagnose sensor hardware issues.

Usage:
    1. SSH to Pi: ssh admin@192.168.0.86
    2. Stop GrowPi: sudo systemctl stop grow-pi
    3. Copy this file to Pi
    4. Run: python3 test_dht22_hardware.py

Version: 1.0.0
Date: 2025-12-26
"""

import time
import sys

try:
    import board
    import adafruit_dht
except ImportError as e:
    print(f"ERROR: Required libraries not found: {e}")
    print("Install with: pip3 install adafruit-circuitpython-dht")
    sys.exit(1)

# Test configuration
GPIO_PIN = board.D4
NUM_TESTS = 10
DELAY_BETWEEN_TESTS = 2.0

# Statistics
success_count = 0
fail_count = 0
errors = []

print("=" * 60)
print("DHT22 SENSOR HARDWARE DIAGNOSTIC")
print("=" * 60)
print(f"GPIO Pin: D4 (GPIO 4)")
print(f"Tests: {NUM_TESTS}")
print(f"Delay: {DELAY_BETWEEN_TESTS}s")
print("=" * 60)
print()

# Initialize sensor
print("Initializing DHT22 sensor...")
try:
    dht = adafruit_dht.DHT22(GPIO_PIN, use_pulseio=False)
    print("✓ Sensor initialized successfully")
    print()
except Exception as e:
    print(f"✗ CRITICAL: Failed to initialize sensor: {e}")
    sys.exit(1)

# Run tests
print("Starting read tests...")
print("-" * 60)

for i in range(NUM_TESTS):
    test_num = i + 1
    print(f"[{test_num}/{NUM_TESTS}] ", end="", flush=True)

    try:
        temp = dht.temperature
        hum = dht.humidity

        if temp is None or hum is None:
            print(f"FAIL: Sensor returned None (temp={temp}, hum={hum})")
            fail_count += 1
            errors.append(f"Test {test_num}: None values")
        else:
            print(f"OK: {temp:.1f}°C, {hum:.1f}%")
            success_count += 1
    except RuntimeError as e:
        print(f"FAIL: RuntimeError - {e}")
        fail_count += 1
        errors.append(f"Test {test_num}: {e}")
    except Exception as e:
        print(f"FAIL: {type(e).__name__} - {e}")
        fail_count += 1
        errors.append(f"Test {test_num}: {e}")

    if test_num < NUM_TESTS:
        time.sleep(DELAY_BETWEEN_TESTS)

# Cleanup
try:
    dht.exit()
    print("\n✓ Sensor cleanup complete")
except Exception:
    pass

# Results
print()
print("=" * 60)
print("DIAGNOSTIC RESULTS")
print("=" * 60)
print(f"Total Tests:     {NUM_TESTS}")
print(f"Successful:      {success_count} ({success_count/NUM_TESTS*100:.1f}%)")
print(f"Failed:          {fail_count} ({fail_count/NUM_TESTS*100:.1f}%)")
print()

# Analysis
if success_count == NUM_TESTS:
    print("✓ STATUS: SENSOR WORKING PERFECTLY")
    print("  → Hardware is OK")
    print("  → Problem likely in GrowPi software/config")
    print("  → Check Circuit Breaker configuration")

elif success_count == 0:
    print("✗ STATUS: SENSOR COMPLETELY FAILED")
    print("  → Hardware likely defective")
    print("  → Check wiring (VCC, Data, GND)")
    print("  → Check pull-up resistor (10kΩ between Data and VCC)")
    print("  → Consider replacing DHT22 sensor")

elif success_count < NUM_TESTS * 0.5:
    print("⚠ STATUS: SENSOR INTERMITTENT FAILURE")
    print("  → Wiring issue (loose connection)")
    print("  → Weak pull-up resistor")
    print("  → Sensor aging/degradation")
    print("  → Power supply unstable")

else:
    print("⚠ STATUS: SENSOR MOSTLY WORKING")
    print("  → Minor communication issues")
    print("  → Check cable quality")
    print("  → May work with longer retry logic")

print()

# Error summary
if errors:
    print("ERROR DETAILS:")
    print("-" * 60)
    for err in errors[:5]:  # Show max 5 errors
        print(f"  • {err}")
    if len(errors) > 5:
        print(f"  ... and {len(errors) - 5} more errors")
    print()

# Recommendations
print("NEXT STEPS:")
print("-" * 60)

if success_count == 0:
    print("1. Power off Raspberry Pi: sudo shutdown -h now")
    print("2. Check physical connections:")
    print("   - DHT22 Pin 1 (VCC)  → Pi Pin 1 (3.3V)")
    print("   - DHT22 Pin 2 (Data) → Pi Pin 7 (GPIO 4)")
    print("   - DHT22 Pin 4 (GND)  → Pi Pin 6 (GND)")
    print("3. Verify 10kΩ pull-up resistor between Data and VCC")
    print("4. Replace DHT22 sensor if wiring is correct")

elif success_count < NUM_TESTS:
    print("1. Check cable connections (re-seat connectors)")
    print("2. Measure voltage: multimeter between VCC and GND should show 3.3V")
    print("3. Try shorter cables (max 20cm recommended)")
    print("4. Consider shielded cable if near power lines")

else:
    print("1. Restart GrowPi service: sudo systemctl start grow-pi")
    print("2. Monitor logs: sudo journalctl -u grow-pi -f")
    print("3. Check /api/status endpoint for sensor data")
    print("4. Review Circuit Breaker configuration in sensor_cache.py")

print("=" * 60)

# Exit code for scripting
sys.exit(0 if success_count == NUM_TESTS else 1)
