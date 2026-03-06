#!/usr/bin/env python3
"""
Raspberry Pi power and throttling helpers.

Reads vcgencmd throttling flags so low-voltage events surface in the API
instead of hiding only in kernel logs.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from typing import Any, Dict

logger = logging.getLogger(__name__)

_THROTTLED_BITS = {
    "under_voltage_now": 0,
    "arm_frequency_capped_now": 1,
    "currently_throttled": 2,
    "soft_temperature_limit_now": 3,
    "under_voltage_occurred": 16,
    "arm_frequency_capped_occurred": 17,
    "throttling_occurred": 18,
    "soft_temperature_limit_occurred": 19,
}


def parse_throttled_response(raw_value: str) -> Dict[str, Any]:
    """Parse `vcgencmd get_throttled` output into a structured dict."""
    value_text = raw_value.strip()
    if "=" in value_text:
        _, value_text = value_text.split("=", 1)

    throttled_value = int(value_text, 16)
    result: Dict[str, Any] = {
        "raw": f"0x{throttled_value:x}",
        "value": throttled_value,
    }

    for key, bit in _THROTTLED_BITS.items():
        result[key] = bool(throttled_value & (1 << bit))

    result["issues_now"] = [
        issue
        for issue in (
            "under_voltage_now",
            "arm_frequency_capped_now",
            "currently_throttled",
            "soft_temperature_limit_now",
        )
        if result[issue]
    ]
    result["issues_occurred"] = [
        issue
        for issue in (
            "under_voltage_occurred",
            "arm_frequency_capped_occurred",
            "throttling_occurred",
            "soft_temperature_limit_occurred",
        )
        if result[issue]
    ]
    result["healthy"] = not result["issues_now"]
    return result


def read_power_status() -> Dict[str, Any]:
    """Return current Raspberry Pi throttling/power status."""
    if shutil.which("vcgencmd") is None:
        return {
            "available": False,
            "healthy": True,
            "error": "vcgencmd not found",
        }

    try:
        completed = subprocess.run(
            ["vcgencmd", "get_throttled"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        parsed = parse_throttled_response(completed.stdout)
        parsed["available"] = True
        return parsed
    except subprocess.TimeoutExpired:
        logger.warning("vcgencmd get_throttled timed out")
        return {
            "available": False,
            "healthy": False,
            "error": "vcgencmd timeout",
        }
    except (subprocess.CalledProcessError, ValueError) as exc:
        logger.warning(f"Failed to read throttled state: {exc}")
        return {
            "available": False,
            "healthy": False,
            "error": str(exc),
        }
