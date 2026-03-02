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
import os
import signal
import socket
import sys
import time
import threading
from datetime import datetime
from typing import Optional, List, Tuple

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

# Web API components are imported lazily to support process splitting.
WEB_API_AVAILABLE = False
_WEB_API_IMPORT_ATTEMPTED = False
app = None
run_server = None
start_data_logger = None
start_dehumidifier_controller = None
get_web_runtime_health = None


def _ensure_web_api_loaded() -> bool:
    """
    Import web API components only when needed.

    This prevents the controller process from initializing the full web stack
    when running in split-process mode (`--no-web`).
    """
    global WEB_API_AVAILABLE
    global _WEB_API_IMPORT_ATTEMPTED
    global app
    global run_server
    global start_data_logger
    global start_dehumidifier_controller
    global get_web_runtime_health

    if _WEB_API_IMPORT_ATTEMPTED:
        return WEB_API_AVAILABLE

    _WEB_API_IMPORT_ATTEMPTED = True

    try:
        from .web.api import (
            app as web_app,
            run_server as web_run_server,
            start_data_logger as web_start_data_logger,
            start_dehumidifier_controller as web_start_dehumidifier_controller,
            get_runtime_health as web_get_runtime_health,
        )
    except ImportError:
        WEB_API_AVAILABLE = False
        return False

    app = web_app
    run_server = web_run_server
    start_data_logger = web_start_data_logger
    start_dehumidifier_controller = web_start_dehumidifier_controller
    get_web_runtime_health = web_get_runtime_health
    WEB_API_AVAILABLE = True
    return True


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
from .utils.systemd_watchdog import get_watchdog_ping_interval


# ============================================================================
# SYSTEMD WATCHDOG INTEGRATION (Tank-Mode)
# ============================================================================

def sd_notify(state: str) -> bool:
    """
    Send notification to systemd.

    Args:
        state: Notification string (e.g., "READY=1", "WATCHDOG=1", "STOPPING=1")

    Returns:
        True if notification was sent successfully

    Reference: systemd.notify(3)
    """
    notify_socket = os.environ.get("NOTIFY_SOCKET")
    if not notify_socket:
        return False

    try:
        # Abstract socket notation
        if notify_socket.startswith("@"):
            notify_socket = "\0" + notify_socket[1:]

        sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
        sock.connect(notify_socket)
        sock.sendall(state.encode())
        sock.close()
        return True
    except Exception as e:
        # Don't spam logs - only warn at startup
        logger = logging.getLogger(__name__)
        logger.debug(f"sd_notify failed: {e}")
        return False


def notify_ready() -> None:
    """Signal systemd that service is ready."""
    if sd_notify("READY=1"):
        logger = logging.getLogger(__name__)
        logger.info("Systemd notified: Service ready")


def notify_watchdog() -> None:
    """Send watchdog ping to systemd."""
    sd_notify("WATCHDOG=1")


def notify_watchdog_trigger() -> None:
    """Request immediate watchdog action from systemd."""
    sd_notify("WATCHDOG=trigger")


def notify_stopping() -> None:
    """Signal systemd that service is stopping."""
    if sd_notify("STOPPING=1"):
        logger = logging.getLogger(__name__)
        logger.info("Systemd notified: Service stopping")


def notify_status(status: str) -> None:
    """Publish current service status to systemd."""
    sd_notify(f"STATUS={status}")


# ============================================================================


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
        self._web_api_active = False
        self.watchdog_thread: Optional[threading.Thread] = None
        self._watchdog_stop_event = threading.Event()
        self._watchdog_ping_interval = get_watchdog_ping_interval()
        self._watchdog_startup_grace_seconds = 120.0
        self._max_main_loop_stall_seconds = max(45.0, self._watchdog_ping_interval * 1.5)
        self._watchdog_started_at = time.monotonic()
        self._last_main_loop_heartbeat = self._watchdog_started_at
        self._last_watchdog_failure: Optional[str] = None

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

        # Zero-Downtime: Check for saved state BEFORE initializing PWM
        # BUGFIX 2025-12-07: Bei Warm-Restart darf PWM nicht auf 0 gesetzt werden!
        warm_restart = False
        saved_state = None
        if STATE_PERSISTENCE_AVAILABLE and state_exists():
            logger.info("=" * 30)
            logger.info("WARM RESTART DETECTED")
            logger.info("=" * 30)
            saved_state = load_state()
            if saved_state:
                warm_restart = True
                logger.info("State file found - will preserve PWM values")

        # Initialize PWM controller (skip zero-init on warm restart)
        if not self.pwm_controller.initialize(channels, skip_zero_init=warm_restart):
            logger.error("Failed to initialize PWM controller")
            return False

        # Restore PWM values from saved state
        if warm_restart and saved_state:
            logger.info("Restoring PWM values from saved state...")
            for ch_str, ch_data in saved_state.get('channels', {}).items():
                channel = int(ch_str)
                intensity = ch_data.get('intensity', 0)
                if channel in self.pwm_controller.channels:
                    # Setze PWM-Wert UND Tracking
                    self.pwm_controller.set_intensity(channel, intensity)
                    self.last_intensities[channel] = intensity
                    logger.info(f"  Channel {channel}: {intensity}% (restored)")
            logger.info("PWM state restored - Zero-Downtime active!")

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
        if self.enable_web:
            if _ensure_web_api_loaded():
                self._start_web_api()
            else:
                logger.warning("Web API requested but not available - continuing without web")
        else:
            logger.info("Web API disabled (--no-web) - controller running in split-process mode")

        logger.info("=" * 50)
        logger.info("Initialization complete!")
        logger.info("=" * 50)

        # Notify systemd that service is ready (Tank-Mode)
        notify_ready()

        return True

    def _start_web_api(self) -> None:
        """Start Flask Web API in background thread."""
        logger = logging.getLogger(__name__)

        if not _ensure_web_api_loaded():
            logger.error("Cannot start Web API - module import failed")
            return

        def run_flask():
            try:
                # Start data logger first
                start_data_logger()
                # Start dehumidifier controller
                start_dehumidifier_controller()
                # Run Flask (without debug, threaded)
                app.run(host='0.0.0.0', port=5000, debug=False, threaded=True, use_reloader=False)
            except Exception as e:
                logger.error(f"Web API error: {e}")

        self.web_thread = threading.Thread(target=run_flask, name="WebAPI", daemon=True)
        self.web_thread.start()
        self._web_api_active = True
        logger.info("Web API started on http://0.0.0.0:5000")

    def _touch_main_loop_heartbeat(self) -> None:
        """Update monotonic heartbeat timestamp for the main loop."""
        self._last_main_loop_heartbeat = time.monotonic()

    def _evaluate_runtime_health(self, now_monotonic: float) -> Tuple[bool, List[str]]:
        """
        Evaluate whether critical runtime components are healthy.

        Returns:
            tuple: (healthy, reasons)
        """
        reasons: List[str] = []
        startup_grace_active = (
            now_monotonic - self._watchdog_started_at < self._watchdog_startup_grace_seconds
        )

        main_loop_age = now_monotonic - self._last_main_loop_heartbeat
        if main_loop_age > self._max_main_loop_stall_seconds:
            reasons.append(
                f"main loop stalled for {main_loop_age:.1f}s "
                f"(limit: {self._max_main_loop_stall_seconds:.1f}s)"
            )

        if self.enable_web:
            if not WEB_API_AVAILABLE and not _ensure_web_api_loaded():
                if not startup_grace_active:
                    reasons.append("web api unavailable")
            elif self._web_api_active:
                if self.web_thread is None or not self.web_thread.is_alive():
                    if not startup_grace_active:
                        reasons.append("web thread not alive")

                if get_web_runtime_health:
                    try:
                        web_health = get_web_runtime_health()
                        if web_health and not web_health.get("healthy", True):
                            if not startup_grace_active:
                                web_issues = web_health.get("issues", [])
                                if web_issues:
                                    reasons.append(f"web runtime unhealthy: {', '.join(web_issues)}")
                                else:
                                    reasons.append("web runtime unhealthy")
                    except Exception as exc:
                        if not startup_grace_active:
                            reasons.append(f"web runtime check failed: {exc}")

        return len(reasons) == 0, reasons

    def _start_watchdog_monitor(self) -> None:
        """Start dedicated watchdog monitor thread."""
        logger = logging.getLogger(__name__)

        if self.watchdog_thread and self.watchdog_thread.is_alive():
            return

        self._watchdog_stop_event.clear()
        self._watchdog_started_at = time.monotonic()
        self._touch_main_loop_heartbeat()

        def watchdog_loop() -> None:
            logger.info(
                "Runtime watchdog started (ping interval: %.1fs, startup grace: %.0fs)",
                self._watchdog_ping_interval,
                self._watchdog_startup_grace_seconds,
            )
            next_ping = time.monotonic() + self._watchdog_ping_interval
            triggered_for_current_failure = False

            while self.running and not self._watchdog_stop_event.wait(timeout=1.0):
                now = time.monotonic()
                healthy, reasons = self._evaluate_runtime_health(now)

                if healthy:
                    if self._last_watchdog_failure:
                        logger.info("Runtime watchdog recovered")
                        self._last_watchdog_failure = None
                        triggered_for_current_failure = False

                    if now >= next_ping:
                        notify_watchdog()
                        logger.debug("Watchdog ping sent to systemd")
                        next_ping = now + self._watchdog_ping_interval
                    continue

                failure_reason = "; ".join(reasons)
                if failure_reason != self._last_watchdog_failure:
                    self._last_watchdog_failure = failure_reason
                    logger.error(f"Runtime watchdog unhealthy: {failure_reason}")
                    notify_status(f"Runtime unhealthy: {failure_reason}")
                    triggered_for_current_failure = False

                if not triggered_for_current_failure:
                    notify_watchdog_trigger()
                    triggered_for_current_failure = True

            logger.info("Runtime watchdog stopped")

        self.watchdog_thread = threading.Thread(
            target=watchdog_loop,
            name="RuntimeWatchdog",
            daemon=True,
        )
        self.watchdog_thread.start()

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
            # In split-process mode curve edits are made by the web service.
            # Refresh from DB before applying current intensities.
            try:
                self.curve_controller.reload_from_database()
            except Exception as e:
                logger.warning(f"Failed to refresh curves from database: {e}")

            intensities = self.curve_controller.get_current_intensities(now)

            for channel, intensity in intensities.items():
                last = self.last_intensities.get(channel, -1)
                if intensity != last:
                    applied = self.pwm_controller.set_intensity(channel, intensity)
                    if applied:
                        self.last_intensities[channel] = intensity
                        changed = True
                    else:
                        logger.warning(
                            "Failed to apply curve intensity for channel %s: target=%s%%",
                            channel,
                            intensity,
                        )

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
            self._start_watchdog_monitor()

            while self.running:
                time.sleep(5)  # CPU-Optimierung: 5s statt 1s (Mode-Wechsel max 5s Verzögerung)
                self._touch_main_loop_heartbeat()
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

        ROBUSTNESS FIX 2025-12-20:
        - Sauberes DHT22 Sensor Cleanup
        - GPIO ordnungsgemäß freigeben
        """
        logger = logging.getLogger(__name__)
        logger.info("Stopping GrowPi Controller...")

        # Notify systemd that we're stopping gracefully (Tank-Mode)
        notify_stopping()

        self.running = False
        self._watchdog_stop_event.set()

        if self.watchdog_thread and self.watchdog_thread.is_alive():
            self.watchdog_thread.join(timeout=5)

        # Speichere State für schnellen Restart (Zero-Downtime)
        if STATE_PERSISTENCE_AVAILABLE:
            current_mode = _get_current_mode()
            save_state(self.pwm_controller, current_mode)
            logger.info("PWM state saved for warm restart")

        # DHT22 Sensor Cleanup (ROBUSTNESS FIX 2025-12-20)
        if self._web_api_active and _ensure_web_api_loaded():
            try:
                # Import DHT sensor from api module to ensure we cleanup the same instance
                from .web.api import dht_sensor, DHT_AVAILABLE
                if DHT_AVAILABLE and dht_sensor is not None:
                    try:
                        dht_sensor.exit()
                        logger.info("DHT22 sensor cleaned up successfully")
                    except AttributeError:
                        # Older versions might not have .exit() method
                        logger.debug("DHT22 sensor does not have .exit() method - skipping cleanup")
                    except Exception as e:
                        logger.warning(f"DHT22 cleanup warning: {e}")
            except Exception as e:
                logger.warning(f"Unexpected error during sensor cleanup: {e}")

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
