#!/usr/bin/env python3
"""
GrowPi Controller - Main Entry Point

Level 5: Per-Channel Kurven mit Web-API.

Usage:
    python -m grow_pi.main
    python -m grow_pi.main --config /path/to/config.yaml
    python -m grow_pi.main --mode fixed    # Feste Werte aus Config
    python -m grow_pi.main --mode curve    # Per-Channel Kurven (default)
    python -m grow_pi.main --preview       # Zeige 24h Kurven-Vorschau
    python -m grow_pi.main --no-web        # Ohne Web-API starten

Per-Channel Kurven (Standard):
    Far Red:     05:45-06:30 → 0-100%
    Cool White:  06:00-07:00 → 15-50%
    Warm White:  05:30-06:30 → 0-50%
    UV:          Immer 0%
"""

import argparse
import logging
import signal
import sys
import time
import threading
from datetime import datetime
from typing import Optional

from .config import load_config, GrowPiConfig
from .lamps import PWMController
from .lamps.pwm_controller import get_pwm_controller

# Try to import curve controller
CURVE_CONTROLLER_AVAILABLE = False
try:
    from .utils.curve_controller import CurveController, get_curve_controller
    CURVE_CONTROLLER_AVAILABLE = True
except ImportError:
    pass

# Try to import mode manager
MODE_MANAGER_AVAILABLE = False
mode_manager = None
try:
    from .utils.mode_manager import get_mode_manager
    MODE_MANAGER_AVAILABLE = True
except ImportError:
    pass

# Try to import PWM state persistence (Zero-Downtime Feature #0)
STATE_PERSISTENCE_AVAILABLE = False
try:
    from .utils.pwm_state import save_state, load_state, state_exists
    STATE_PERSISTENCE_AVAILABLE = True
except ImportError:
    pass

# Try to import web API
WEB_API_AVAILABLE = False
try:
    from .web.api import app, run_server, start_data_logger
    WEB_API_AVAILABLE = True
except ImportError:
    pass


def _get_current_mode() -> str:
    """Get current mode from ModeManager (single source of truth)."""
    if MODE_MANAGER_AVAILABLE and mode_manager:
        return mode_manager.get_mode()
    return 'auto'

# Fallback to old sun_curve if new controller not available
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
    - curve: Per-channel curve interpolation
    """

    def __init__(self, config: GrowPiConfig, mode: str = "curve", enable_web: bool = True):
        global mode_manager
        self.config = config
        self.mode = mode
        self.enable_web = enable_web
        self.pwm_controller = get_pwm_controller()  # Use singleton
        self.running = False
        self.curve_controller: Optional[CurveController] = None
        self.sun_curve = get_default_sun_curve()  # Fallback
        self.last_intensities = {}  # Track last intensities per channel
        self.web_thread: Optional[threading.Thread] = None

        # Initialize ModeManager (single source of truth for mode)
        if MODE_MANAGER_AVAILABLE:
            mode_manager = get_mode_manager()

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

        # Zero-Downtime: Check for saved state (warm restart)
        # Wenn State existiert, wurden PWM-Werte bereits von pigpiod gehalten
        # Wir stellen nur die internen Tracking-Variablen wieder her
        warm_restart = False
        if STATE_PERSISTENCE_AVAILABLE and state_exists():
            logger.info("=" * 30)
            logger.info("WARM RESTART DETECTED")
            logger.info("=" * 30)
            saved_state = load_state()
            if saved_state:
                logger.info("Restoring PWM tracking from saved state...")
                for ch_str, ch_data in saved_state.get('channels', {}).items():
                    channel = int(ch_str)
                    intensity = ch_data.get('intensity', 0)
                    # PWM ist bereits von pigpiod gehalten - nur Tracking wiederherstellen
                    if channel in self.pwm_controller.channels:
                        self.pwm_controller.channels[channel].current_intensity = intensity
                        self.last_intensities[channel] = intensity
                        logger.info(f"  Channel {channel}: {intensity}% (preserved)")
                warm_restart = True
                logger.info("PWM state restored - no flickering!")

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
            # Curve mode - initialize curve controller
            if CURVE_CONTROLLER_AVAILABLE:
                logger.info("Mode: CURVE - Using per-channel curve interpolation")
                try:
                    channel_names = {ch.channel: ch.name for ch in channels}
                    self.curve_controller = get_curve_controller()
                    self.curve_controller.initialize(channel_names)
                    logger.info("CurveController initialized with per-channel curves")
                except Exception as e:
                    logger.warning(f"CurveController init failed: {e}, using fallback")
                    self.curve_controller = None
            else:
                logger.info("Mode: CURVE - Using legacy single sun curve (fallback)")

            # Apply curve values on startup
            # Bei Warm Restart: Werte sind bereits korrekt von pigpiod gehalten
            # Bei Cold Boot: Kurven müssen angewendet werden
            current_mode = _get_current_mode()
            logger.info(f"Startup mode: {current_mode}")

            if warm_restart:
                logger.info("Warm restart - PWM already correct, skipping curve application")
            elif current_mode == "auto":
                logger.info("Cold boot - Applying curve values...")
                self._update_intensity_from_curve()
            else:
                logger.info("Manual mode active - not applying curves on startup")

        # Start Web API in background thread
        if self.enable_web and WEB_API_AVAILABLE:
            self._start_web_api()

        logger.info("=" * 50)
        logger.info("Initialization complete!")
        logger.info("=" * 50)

        return True

    def _start_web_api(self) -> None:
        """Start Flask Web API in background thread."""
        logger = logging.getLogger(__name__)

        def run_flask():
            try:
                # Start data logger first
                start_data_logger()
                # Run Flask (without debug, threaded)
                app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
            except Exception as e:
                logger.error(f"Web API error: {e}")

        self.web_thread = threading.Thread(target=run_flask, name="WebAPI", daemon=True)
        self.web_thread.start()
        logger.info("Web API started on http://0.0.0.0:5000")

    def _update_intensity_from_curve(self) -> bool:
        """
        Update lamp intensity based on current time and curves.

        Returns:
            True if any intensity was changed
        """
        logger = logging.getLogger(__name__)
        now = datetime.now()
        changed = False

        # Use per-channel curve controller if available
        if self.curve_controller:
            intensities = self.curve_controller.get_current_intensities(now)

            for channel, intensity in intensities.items():
                last = self.last_intensities.get(channel, -1)
                if intensity != last:
                    self.pwm_controller.set_intensity(channel, intensity)
                    self.last_intensities[channel] = intensity
                    changed = True

            if changed:
                state_str = ", ".join(
                    f"Ch{ch}:{i}%"
                    for ch, i in sorted(intensities.items())
                )
                logger.info(f"Kurve Update [{now.strftime('%H:%M')}]: [{state_str}]")

        else:
            # Fallback: Legacy single curve for all channels
            intensity = interpolate_intensity(self.sun_curve, now)
            last = self.last_intensities.get(0, -1)

            if intensity != last:
                for ch in self.config.lamps.channels:
                    if ch.name == "UV":
                        self.pwm_controller.set_intensity(ch.channel, ch.default_intensity)
                    else:
                        self.pwm_controller.set_intensity(ch.channel, intensity)

                logger.info(
                    f"Kurve Update [{now.strftime('%H:%M')}]: "
                    f"Intensität {last}% → {intensity}%"
                )
                self.last_intensities[0] = intensity
                changed = True

        return changed

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
            last_known_mode = _get_current_mode()  # Track mode changes

            while self.running:
                time.sleep(5)  # CPU-Optimierung: 5s statt 1s (Mode-Wechsel max 5s Verzögerung)
                now = time.time()

                # Get current mode from ModeManager (single source of truth)
                current_mode = _get_current_mode()

                # CRITICAL: Detect mode change from manual to auto
                # Clear the intensity cache to force a fresh update
                if current_mode == "auto" and last_known_mode != "auto":
                    logger.info("Mode change detected (manual -> auto) - forcing curve update")
                    self.last_intensities = {}  # Clear cache to force update!
                    last_update = 0  # Force immediate update

                last_known_mode = current_mode

                # Curve mode: Update intensity periodically (only if mode is 'auto')
                # This is the ONLY place where curves update lamp values
                if self.mode == "curve" and current_mode == "auto" and (now - last_update >= update_interval):
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
                    logger.info(f"Heartbeat [{current_time}] Mode={current_mode} - Lamps: [{state_str}]")
                    last_heartbeat = now

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")

    def stop(self) -> None:
        """
        Stop the controller gracefully.

        PWM-Werte bleiben IMMER erhalten (User-Entscheidung 2025-12-06).
        Lampen werden nur über explizite API-Calls ausgeschaltet.

        Siehe: Feature #0 PWM Zero-Downtime (ROADMAP.md)
        """
        logger = logging.getLogger(__name__)
        logger.info("Stopping GrowPi Controller...")

        self.running = False

        # Speichere State für schnellen Restart (Zero-Downtime)
        if STATE_PERSISTENCE_AVAILABLE:
            current_mode = _get_current_mode()
            save_state(self.pwm_controller, current_mode)
            logger.info("PWM state saved for warm restart")

        # Nur trennen, PWM bleibt via pigpiod aktiv!
        # NICHT cleanup() aufrufen - das würde all_off() triggern
        self.pwm_controller.disconnect()

        logger.info("GrowPi Controller stopped (PWM preserved).")


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
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Disable Web API (run controller only)"
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
        controller = GrowPiController(config, mode=args.mode, enable_web=not args.no_web)

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
