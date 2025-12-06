"""
GrowPi Web Interface Module

This module provides backward compatibility for existing code.
Main entry point is main.py which uses web.api directly.

For new modular implementation, use:
    from grow_pi.web.app import create_app
    app = create_app()
"""

# Keep backward compatibility - main.py imports from web.api directly
# Don't auto-create app here to avoid double initialization

# Export new app factory for explicit use
try:
    from .app import create_app
    NEW_APP_AVAILABLE = True
except ImportError:
    NEW_APP_AVAILABLE = False
    create_app = None

# Legacy imports from api.py (used by main.py)
from .api import app, run_server

__all__ = ["app", "run_server", "create_app", "NEW_APP_AVAILABLE"]
