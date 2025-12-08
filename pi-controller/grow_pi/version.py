#!/usr/bin/env python3
"""
GrowPi Version Management

Single Source of Truth: /VERSION file
This module provides cached version access for the entire application.
"""
from pathlib import Path
import re
import logging

logger = logging.getLogger(__name__)

_VERSION_CACHE = None

def get_version() -> str:
    """
    Get version from VERSION file (cached).

    Returns:
        Version string (e.g., "6.16.0")
    """
    global _VERSION_CACHE

    if _VERSION_CACHE is None:
        version_file = Path(__file__).parent.parent / "VERSION"

        if not version_file.exists():
            logger.warning("VERSION file not found, using fallback")
            _VERSION_CACHE = "0.0.0"
        else:
            version = version_file.read_text().strip()

            # Validate semantic versioning
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                logger.error(f"Invalid version format: {version}")
                _VERSION_CACHE = "0.0.0"
            else:
                _VERSION_CACHE = version
                logger.info(f"Version loaded: {_VERSION_CACHE}")

    return _VERSION_CACHE

def get_version_display() -> str:
    """Get version with 'v' prefix (e.g., v6.16.0)."""
    return f"v{get_version()}"

# Module-level version for easy import
__version__ = get_version()
