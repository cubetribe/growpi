import os

from grow_pi.utils.systemd_watchdog import get_watchdog_ping_interval


def test_watchdog_interval_defaults_without_env(monkeypatch):
    monkeypatch.delenv("WATCHDOG_USEC", raising=False)
    monkeypatch.delenv("WATCHDOG_PID", raising=False)
    assert get_watchdog_ping_interval(30.0) == 30.0


def test_watchdog_interval_uses_half_timeout(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "60000000")  # 60s
    monkeypatch.setenv("WATCHDOG_PID", str(os.getpid()))
    assert get_watchdog_ping_interval(30.0) == 30.0


def test_watchdog_interval_ignores_mismatched_pid(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "60000000")
    monkeypatch.setenv("WATCHDOG_PID", "999999")
    assert get_watchdog_ping_interval(11.0) == 11.0


def test_watchdog_interval_handles_invalid_usec(monkeypatch):
    monkeypatch.setenv("WATCHDOG_USEC", "invalid")
    monkeypatch.delenv("WATCHDOG_PID", raising=False)
    assert get_watchdog_ping_interval(9.0) == 9.0
