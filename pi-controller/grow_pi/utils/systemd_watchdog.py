"""
Helpers for systemd watchdog integration.
"""

import os


def get_watchdog_ping_interval(default_seconds: float = 30.0) -> float:
    """
    Derive watchdog ping interval from systemd environment.

    systemd sets WATCHDOG_USEC when WatchdogSec is configured.
    Best practice is to ping at half of the timeout.
    """
    watchdog_usec = os.environ.get("WATCHDOG_USEC")
    watchdog_pid = os.environ.get("WATCHDOG_PID")

    if not watchdog_usec:
        return default_seconds

    if watchdog_pid and watchdog_pid != str(os.getpid()):
        return default_seconds

    try:
        watchdog_seconds = int(watchdog_usec) / 1_000_000.0
        return max(1.0, watchdog_seconds / 2.0)
    except (TypeError, ValueError):
        return default_seconds
