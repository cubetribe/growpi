#!/usr/bin/env python3
"""
GrowPi Controller - Main Entry Point

Level 4: Sonnenkurven-Modus mit zeitbasierter Intensität.

Usage:
    python -m grow_pi.main
    python -m grow_pi.main --config /path/to/config.yaml
    python -m grow_pi.main --mode fixed    # Feste Werte aus Config
    python -m grow_pi.main --mode curve    # Sonnenkurve (default)
    python -m grow_pi.main --preview       # Zeige 24h Kurven-Vorschau

Sonnenkurve:
    05:00 - 08:00  → Sonnenaufgang: 10% → 60%
    08:00 - 20:00  → Tageslicht: 60%
    20:00 - 23:00  → Sonnenuntergang: 60% → 10%
    23:00 - 05:00  → Nacht: 0%
"""

import argparse
import logging
import signal
import sys
import time
from datetime import datetime
from typing import Optional

from .config import load_config, GrowPiConfig
from .lamps import PWMController
from .utils.sun_curve import (
    interpolate_intensity,
    get_default_sun_curve,
    print_curve_preview,
    CurvePoint,
)


class GrowPiController:
    """
    Main GrowPi Controller

    Supports two modes:
    - fixed: Static intensities from config file
    - curve: Dynamic sun curve interpolation
    """

    def __init__(self, config: GrowPiConfig, mode: str = "curve"):
        self.config = config
        self.mode = mode
        self.pwm_controller = PWMController()
        self.running = False
        self.sun_curve = get_default_sun_curve()
        self.last_intensity = -1  # Track last intensity to avoid unnecessary updates
        self._setup_logging()

    def _setup_logging(self) -> None:
        """Configure logging based on config"""
        level = getattr(logging, self.config.logging.level.upper(), logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Reduce noise from third-party libs
        logging.getLogger("urllib3").setLevel(logging.WARNING)

    def initialize(self) -> bool:
        """
        Initialize all controller components.

        Returns:
            True if initialization successful
        """
        logger = logging.getLogger(__name__)
        logger.info("=" * 50)
        logger.info(f"GrowPi Controller - Starting (Mode: {self.mode})")
        logger.info("=" * 50)

        # Initialize PWM controller with lamp channels
        channels = self.config.lamps.channels
        if not channels:
            logger.error("No lamp channels configured!")
            return False

        if not self.pwm_controller.initialize(channels):
            logger.error("Failed to initialize PWM controller")
            return False

        if self.mode == "fixed":
            # Set initial intensities from config
            logger.info("Mode: FIXED - Setting lamp intensities from configuration...")
            for ch in channels:
                intensity = ch.default_intensity
                self.pwm_controller.set_intensity(ch.channel, intensity)
                logger.info(
                    f"  Channel {ch.channel} ({ch.name}): {intensity}% "
                    f"[GPIO-{ch.gpio_pin}]"
                )
        else:
            # Curve mode - calculate current intensity
            logger.info("Mode: CURVE - Using sun curve interpolation")
            logger.info("Kurve: 05:00-08:00 Aufgang, 08:00-20:00 Tag, 20:00-23:00 Untergang, 23:00-05:00 Nacht")
            self._update_intensity_from_curve()

        logger.info("=" * 50)
        logger.info("Initialization complete!")
        logger.info("=" * 50)

        return True

    def _update_intensity_from_curve(self) -> bool:
        """
        Update lamp intensity based on current time and sun curve.

        Returns:
            True if intensity was changed
        """
        logger = logging.getLogger(__name__)

        now = datetime.now()
        intensity = interpolate_intensity(self.sun_curve, now)

        # Only update if intensity changed
        if intensity != self.last_intensity:
            # Set same intensity for all channels (except UV which stays at config value)
            for ch in self.config.lamps.channels:
                if ch.name == "UV":
                    # UV stays at configured value
                    self.pwm_controller.set_intensity(ch.channel, ch.default_intensity)
                else:
                    self.pwm_controller.set_intensity(ch.channel, intensity)

            logger.info(
                f"Kurve Update [{now.strftime('%H:%M')}]: "
                f"Intensität {self.last_intensity}% → {intensity}%"
            )
            self.last_intensity = intensity
            return True

        return False

    def run(self) -> None:
        """
        Main run loop.

        In curve mode: Updates intensity every minute based on time.
        In fixed mode: Just keeps the process alive.
        """
        logger = logging.getLogger(__name__)
        self.running = True

        if self.mode == "curve":
            logger.info("Controller running with SUN CURVE. Press Ctrl+C to stop.")
            logger.info("Intensität wird jede Minute aktualisiert.")
        else:
            logger.info("Controller running with FIXED values. Press Ctrl+C to stop.")

        update_interval = 60  # Check curve every 60 seconds
        heartbeat_interval = 300  # Log status every 5 minutes

        try:
            last_update = 0
            last_heartbeat = time.time()

            while self.running:
                time.sleep(1)
                now = time.time()

                # Curve mode: Update intensity periodically
                if self.mode == "curve" and (now - last_update >= update_interval):
                    self._update_intensity_from_curve()
                    last_update = now

                # Periodic status log
                if now - last_heartbeat >= heartbeat_interval:
                    state = self.pwm_controller.get_current_state()
                    current_time = datetime.now().strftime('%H:%M')
                    state_str = ", ".join(
                        f"Ch{ch}:{intensity}%"
                        for ch, intensity in sorted(state.items())
                    )
                    logger.info(f"Heartbeat [{current_time}] - Lamps: [{state_str}]")
                    last_heartbeat = now

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

    def stop(self) -> None:
        """Stop the controller gracefully."""
        logger = logging.getLogger(__name__)
        logger.info("Stopping GrowPi Controller...")

        self.running = False

        # Cleanup PWM (turns off lamps)
        self.pwm_controller.cleanup()

        logger.info("GrowPi Controller stopped.")


def main(config_path: Optional[str] = None) -> int:
    """
    Main entry point.

    Args:
        config_path: Optional path to config file

    Returns:
        Exit code (0 = success, 1 = error)
    """
    logger = logging.getLogger(__name__)

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="GrowPi Controller - Raspberry Pi Greenhouse Management"
    )
    parser.add_argument(
        "--config", "-c",
        type=str,
        default=config_path,
        help="Path to configuration file (default: auto-detect)"
    )
    parser.add_argument(
        "--mode", "-m",
        type=str,
        choices=["fixed", "curve"],
        default="curve",
        help="Operating mode: fixed (static values) or curve (sun curve)"
    )
    parser.add_argument(
        "--test",
        action="store_true",
        help="Test mode: Initialize, show status, then exit"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Show 24h curve preview and exit"
    )
    args = parser.parse_args()

    # Preview mode: Just show curve and exit
    if args.preview:
        print_curve_preview()
        now = datetime.now()
        current_intensity = interpolate_intensity(get_default_sun_curve())
        print(f"Aktuelle Zeit: {now.strftime('%H:%M')}")
        print(f"Aktuelle Intensität: {current_intensity}%")
        return 0

    controller: Optional[GrowPiController] = None

    try:
        # Load configuration
        config = load_config(args.config)

        # Create controller with selected mode
        controller = GrowPiController(config, mode=args.mode)

        # Setup signal handlers for graceful shutdown
        def signal_handler(sig, frame):
            logger.info(f"Signal {sig} received")
            if controller:
                controller.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        # Initialize
        if not controller.initialize():
            logger.error("Initialization failed!")
            return 1

        # Test mode: Just show status and exit
        if args.test:
            logger.info("Test mode: Initialization successful, exiting.")
            state = controller.pwm_controller.get_current_state()
            logger.info(f"Current lamp states: {state}")
            controller.stop()
            return 0

        # Run main loop
        controller.run()

        return 0

    except FileNotFoundError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        if controller and controller.running:
            controller.stop()


if __name__ == "__main__":
    sys.exit(main())
