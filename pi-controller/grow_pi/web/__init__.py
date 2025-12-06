"""
GrowPi Web Interface Module
"""

# Import both old and new implementations for backward compatibility
try:
    # New modular implementation (Phase 1 Refactoring)
    from .app import create_app, run_server

    # Create default app instance for backward compatibility
    app = create_app()

    __all__ = ["app", "create_app", "run_server"]

except ImportError as e:
    # Fallback to old implementation if new modules not available
    import warnings
    warnings.warn(f"Failed to import new app implementation: {e}. Using legacy api.py")

    from .api import app, run_server
    __all__ = ["app", "run_server"]
