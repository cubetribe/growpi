#!/usr/bin/env python3
"""
GrowPi Controller - Main Entry Point

MVP Level 1: Startet automatisch und setzt Lampen auf feste Werte.

Usage:
    python -m grow_pi.main
    python -m grow_pi.main --config /path/to/config.yaml

Future Levels:
    Level 2: Logging to journald/file
    Level 3: Sensor reading (DHT22)
    Level 4: Curve interpolation
    Level 5: API client (server communication)
    Level 6: Offline mode with buffering
    Level 7: RS485 soil sensors
"""

import argparse
import logging
import signal
import sys
import time
from typing import Optional

from .config import load_config, GrowPiConfig
from .lamps import PWMController


class GrowPiController:
    """
    Main GrowPi Controller - MVP Version

    Handles startup, lamp initialization, and graceful shutdown.
    """

    def __init__(self, config: GrowPiConfig):
        self.config = config
        self.pwm_controller = PWMController()
        self.running = False
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
        logger.info("GrowPi Controller - Starting (MVP Level 1)")
        logger.info("=" * 50)

        # Initialize PWM controller with lamp channels
        channels = self.config.lamps.channels
        if not channels:
            logger.error("No lamp channels configured!")
            return False

        if not self.pwm_controller.initialize(channels):
            logger.error("Failed to initialize PWM controller")
            return False

        # Set initial intensities from config
        logger.info("Setting lamp intensities from configuration...")
        for ch in channels:
            intensity = ch.default_intensity
            self.pwm_controller.set_intensity(ch.channel, intensity)
            logger.info(
                f"  Channel {ch.channel} ({ch.name}): {intensity}% "
                f"[GPIO-{ch.gpio_pin}]"
            )

        logger.info("=" * 50)
        logger.info("Initialization complete!")
        logger.info("=" * 50)

        return True

    def run(self) -> None:
        """
        Main run loop.

        MVP: Just keeps the process alive and maintains lamp states.
        Future: Will handle sensor reading, curve updates, API communication.
        """
        logger = logging.getLogger(__name__)
        self.running = True

        logger.info("Controller running. Press Ctrl+C to stop.")
        logger.info("Lamp intensities are set and will maintain current values.")

        # MVP: Simple keepalive loop
        # Future levels will add sensor reading, curve updates, etc.
        heartbeat_interval = 60  # Log status every 60 seconds

        try:
            last_heartbeat = time.time()

            while self.running:
                time.sleep(1)

                # Periodic status log
                if time.time() - last_heartbeat >= heartbeat_interval:
                    state = self.pwm_controller.get_current_state()
                    state_str = ", ".join(
                        f"Ch{ch}:{intensity}%"
                        for ch, intensity in sorted(state.items())
                    )
                    logger.info(f"Heartbeat - Lamps: [{state_str}]")
                    last_heartbeat = time.time()

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
        "--test",
        action="store_true",
        help="Test mode: Initialize, show status, then exit"
    )
    args = parser.parse_args()

    controller: Optional[GrowPiController] = None

    try:
        # Load configuration
        config = load_config(args.config)

        # Create controller
        controller = GrowPiController(config)

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
