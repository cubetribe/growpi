#!/usr/bin/env python3
"""
Fixed PWM Intensity Script for GrowPi
--------------------------------------
Sets a fixed PWM intensity on GPIO-18 and keeps it running.

Usage: python3 pwm_set_fixed.py <intensity>
Example: python3 pwm_set_fixed.py 40

Hardware: Raspberry Pi 3B+
PWM Channel: GPIO-18 (Pin 12) - Warm White LED
"""

import sys
import signal
import pigpio

# Configuration
PWM_PIN = 18  # GPIO-18 = Pin 12 = Warm White (Hardware PWM0)
PWM_FREQUENCY = 1000  # 1 kHz

# Global pigpio instance for cleanup
pi = None


def cleanup(signum=None, frame=None):
    """Turn off PWM and disconnect"""
    global pi
    if pi:
        print("\n\nShutting down...")
        pi.set_PWM_dutycycle(PWM_PIN, 0)
        pi.stop()
        print("✓ PWM turned off")
    sys.exit(0)


def main():
    global pi

    # Parse intensity argument
    if len(sys.argv) != 2:
        print("Usage: python3 pwm_set_fixed.py <intensity>")
        print("Example: python3 pwm_set_fixed.py 40")
        print("Intensity range: 0-100")
        sys.exit(1)

    try:
        intensity = float(sys.argv[1])
    except ValueError:
        print(f"ERROR: Invalid intensity value '{sys.argv[1]}'")
        print("Intensity must be a number between 0 and 100")
        sys.exit(1)

    # Validate intensity
    if intensity < 0 or intensity > 100:
        print(f"ERROR: Intensity {intensity} out of range")
        print("Intensity must be between 0 and 100")
        sys.exit(1)

    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Connect to pigpio
    pi = pigpio.pi()

    if not pi.connected:
        print("ERROR: Failed to connect to pigpio daemon")
        print("Run: sudo pigpiod")
        sys.exit(1)

    # Configure PWM
    pi.set_PWM_frequency(PWM_PIN, PWM_FREQUENCY)
    pi.set_PWM_range(PWM_PIN, 100)  # 0-100 range
    pi.set_PWM_dutycycle(PWM_PIN, int(intensity))

    print("\n" + "="*50)
    print("GrowPi Fixed PWM Controller")
    print("="*50)
    print(f"GPIO Pin:    {PWM_PIN} (Pin 12)")
    print(f"Frequency:   {PWM_FREQUENCY} Hz")
    print(f"Intensity:   {intensity}%")
    print("="*50)
    print("\nPWM is now running continuously.")
    print("Press Ctrl+C to stop and turn off.\n")

    # Keep running until interrupted
    try:
        signal.pause()
    except AttributeError:
        # signal.pause() not available on Windows
        import time
        while True:
            time.sleep(1)


if __name__ == "__main__":
    main()
