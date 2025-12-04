#!/usr/bin/env python3
"""
Basic PWM Test Script for GrowPi
---------------------------------
Tests SINGLE PWM channel (GPIO-18 / Warm White) by cycling
between 0% and 50% intensity over a 10-second interval.

Hardware: Raspberry Pi 3B+
PWM Channel: GPIO-18 (Pin 12) - Warm White LED
"""

import time
import sys
from typing import List

try:
    import pigpio
except ImportError:
    print("ERROR: pigpio library not installed")
    print("Install with: sudo apt-get install pigpio python3-pigpio")
    sys.exit(1)


class PWMController:
    """Simple PWM controller for single LED channel"""

    # GPIO Pin Configuration (BCM numbering)
    TEST_PIN = 18  # GPIO-18 = Pin 12 = Warm White (Hardware PWM0)
    PWM_FREQUENCY = 1000  # 1 kHz

    def __init__(self):
        """Initialize pigpio connection"""
        self.pi = pigpio.pi()

        if not self.pi.connected:
            raise RuntimeError("Failed to connect to pigpio daemon. Run: sudo pigpiod")

        # Configure single PWM pin
        self.pi.set_PWM_frequency(self.TEST_PIN, self.PWM_FREQUENCY)
        self.pi.set_PWM_range(self.TEST_PIN, 100)  # 0-100 range
        self.pi.set_PWM_dutycycle(self.TEST_PIN, 0)  # Start at 0%

        print(f"✓ PWM Controller initialized")
        print(f"  GPIO Pin: {self.TEST_PIN} (Pin 12)")
        print(f"  Frequency: {self.PWM_FREQUENCY} Hz")
        print(f"  Range: 0-100%")

    def set_intensity(self, intensity: float):
        """
        Set PWM intensity for the test channel

        Args:
            intensity: Intensity 0.0 - 100.0
        """
        # Clamp intensity
        intensity = max(0.0, min(100.0, intensity))
        self.pi.set_PWM_dutycycle(self.TEST_PIN, int(intensity))

    def cleanup(self):
        """Turn off channel and disconnect"""
        self.pi.set_PWM_dutycycle(self.TEST_PIN, 0)
        self.pi.stop()
        print("✓ PWM Controller cleaned up")


def run_cycle_test(controller: PWMController, duration_sec: float = 10.0):
    """
    Run one test cycle: 0% -> 50% -> 0%

    Args:
        controller: PWM controller instance
        duration_sec: Total cycle duration in seconds
    """
    steps = 50  # Number of steps for smooth transition
    step_delay = duration_sec / steps

    print(f"\n{'='*50}")
    print(f"Starting cycle: 0% -> 50% -> 0% (duration: {duration_sec}s)")
    print(f"{'='*50}\n")

    # Phase 1: Ramp up 0% -> 50%
    print("Phase 1: Ramping up 0% -> 50%")
    for i in range(steps + 1):
        intensity = (i / steps) * 50.0  # 0 to 50
        controller.set_intensity(intensity)
        print(f"  Intensity: {intensity:5.1f}%", end='\r')
        time.sleep(step_delay / 2)  # Half the cycle for up

    print(f"\n  Peak reached: 50.0%\n")

    # Phase 2: Ramp down 50% -> 0%
    print("Phase 2: Ramping down 50% -> 0%")
    for i in range(steps, -1, -1):
        intensity = (i / steps) * 50.0  # 50 to 0
        controller.set_intensity(intensity)
        print(f"  Intensity: {intensity:5.1f}%", end='\r')
        time.sleep(step_delay / 2)  # Half the cycle for down

    print(f"\n  Cycle complete: 0.0%\n")


def main():
    """Main test loop"""
    print("\n" + "="*50)
    print("GrowPi PWM Test Script")
    print("="*50)
    print("Test: Cycle between 0% and 50% intensity")
    print("Interval: 10 seconds per cycle")
    print("Press Ctrl+C to stop")
    print("="*50 + "\n")

    controller = None

    try:
        # Initialize controller
        controller = PWMController()

        # Run continuous cycles
        cycle_count = 0
        while True:
            cycle_count += 1
            print(f"\n>>> Cycle #{cycle_count} <<<")
            run_cycle_test(controller, duration_sec=10.0)

            # Pause between cycles
            print("\nWaiting 2 seconds before next cycle...")
            time.sleep(2)

    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")

    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

    finally:
        if controller:
            controller.cleanup()
        print("\n✓ Test script finished\n")


if __name__ == "__main__":
    main()
