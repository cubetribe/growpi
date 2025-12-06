#!/usr/bin/env python3
"""
GrowPi Flask Application Factory
Creates and configures the Flask application with all blueprints and extensions.
"""

import os
import logging
import atexit
from typing import Optional
from flask import Flask, send_from_directory
from flask_cors import CORS

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config: Optional[dict] = None) -> Flask:
    """
    Flask Application Factory.

    Creates and configures the Flask application with all necessary
    blueprints, extensions, and middleware.

    Args:
        config: Optional configuration dictionary to override defaults

    Returns:
        Configured Flask application instance
    """
    # Determine static files directory
    static_dir = os.path.join(os.path.dirname(__file__), 'static')

    # Create Flask app
    app = Flask(__name__, static_folder=static_dir)

    # Load default configuration
    app.config.update({
        'API_VERSION': '2.0.0',  # Bumped for refactored architecture
        'API_HOST': '0.0.0.0',
        'API_PORT': 5000,
        'DEBUG': False,
        'THREADED': True,
        'JSON_SORT_KEYS': False,
        'JSONIFY_PRETTYPRINT_REGULAR': False
    })

    # Apply custom configuration if provided
    if config:
        app.config.update(config)

    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })

    # ========================================================================
    # Initialize Core Services
    # ========================================================================

    # Initialize hardware controllers
    _initialize_hardware(app)

    # Initialize data logger
    _initialize_data_logger(app)

    # Initialize curve controller
    _initialize_curve_controller(app)

    # Initialize mode manager
    _initialize_mode_manager(app)

    # Initialize dehumidifier controller
    _initialize_dehumidifier_controller(app)

    # Initialize dependencies module AFTER all services (for blueprint access)
    _initialize_dependencies(app)

    # ========================================================================
    # Register Blueprints
    # ========================================================================

    # Register all API blueprints
    _register_blueprints(app)

    # ========================================================================
    # Static File Serving
    # ========================================================================

    @app.route('/')
    def serve_frontend():
        """Serve the frontend HTML"""
        return send_from_directory(static_dir, 'index.html')

    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files or fallback to index.html for SPA routing"""
        file_path = os.path.join(static_dir, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_from_directory(static_dir, path)
        return send_from_directory(static_dir, 'index.html')

    # ========================================================================
    # Error Handlers
    # ========================================================================

    @app.errorhandler(404)
    def not_found(error):
        from flask import jsonify
        return jsonify({
            "success": False,
            "error": "Endpoint not found"
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        from flask import jsonify
        logger.error(f"Internal server error: {error}")
        return jsonify({
            "success": False,
            "error": "Internal server error"
        }), 500

    # ========================================================================
    # Shutdown Handlers
    # ========================================================================

    @atexit.register
    def cleanup():
        """Clean up resources on application shutdown"""
        logger.info("Application shutting down - cleaning up resources")

        # Stop data logger
        if hasattr(app, 'data_logger') and app.data_logger:
            try:
                from .services.lamp_config import get_lamp_channels
                channels = list(get_lamp_channels().keys())
                names = {ch: cfg.name for ch, cfg in get_lamp_channels().items()}
                app.data_logger.log_shutdown_states(channels, names)
                app.data_logger.stop()
                logger.info("DataLogger stopped")
            except Exception as e:
                logger.error(f"Error stopping DataLogger: {e}")

        # Cleanup PWM controller
        if hasattr(app, 'pwm_controller') and app.pwm_controller:
            try:
                # PWM controller cleanup is handled by its own destructor
                logger.info("PWM Controller cleanup initiated")
            except Exception as e:
                logger.error(f"Error cleaning up PWM Controller: {e}")

        # Stop dehumidifier controller
        if hasattr(app, 'dehumidifier_controller') and app.dehumidifier_controller:
            try:
                app.dehumidifier_controller.stop()
                logger.info("DehumidifierController stopped")
            except Exception as e:
                logger.error(f"Error stopping DehumidifierController: {e}")

    logger.info(f"GrowPi Web API v{app.config['API_VERSION']} initialized successfully")

    return app


def _initialize_hardware(app: Flask) -> None:
    """
    Initialize hardware controllers (PWM, sensors).

    Args:
        app: Flask application instance
    """
    # Initialize PWM Controller
    app.pwm_controller = None
    try:
        try:
            from ..lamps.pwm_controller import get_pwm_controller
        except ImportError:
            from grow_pi.lamps.pwm_controller import get_pwm_controller

        app.pwm_controller = get_pwm_controller()

        # Initialize with channel configs if not already initialized
        if not app.pwm_controller._initialized:
            try:
                from ..config import load_config
            except ImportError:
                from grow_pi.config import load_config

            config = load_config()
            app.pwm_controller.initialize(config.lamps.channels)

        logger.info("PWM Controller initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize PWM Controller: {e}")

    # Initialize DHT22 Sensor
    app.dht_sensor = None
    app.dht_available = False

    try:
        import board
        import adafruit_dht
        app.dht_available = True

        try:
            app.dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            logger.info("DHT22 Sensor initialized on GPIO-4")
        except Exception as e:
            logger.error(f"Failed to initialize DHT22: {e}")
    except ImportError:
        logger.warning("adafruit_dht not available - sensor will return mock data")


def _initialize_data_logger(app: Flask) -> None:
    """
    Initialize database and data logger.

    Args:
        app: Flask application instance
    """
    app.data_logger = None
    app.db = None
    app.db_available = False

    try:
        try:
            from ..database import get_database, get_logger
        except ImportError:
            from grow_pi.database import get_database, get_logger

        app.db_available = True

        try:
            app.db = get_database()
            app.data_logger = get_logger(db=app.db, sensor_interval=60, lamp_interval=60)
            logger.info("DataLogger initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DataLogger: {e}")
    except ImportError:
        logger.warning("Database module not available - logging disabled")


def _initialize_curve_controller(app: Flask) -> None:
    """
    Initialize curve controller for automated lamp scheduling.

    Args:
        app: Flask application instance
    """
    app.curve_controller = None
    app.curve_available = False

    try:
        try:
            from ..utils.curve_controller import get_curve_controller
        except ImportError:
            from grow_pi.utils.curve_controller import get_curve_controller

        app.curve_available = True

        try:
            from .services.lamp_config import get_lamp_channels
            channels = {ch: cfg.name for ch, cfg in get_lamp_channels().items()}

            app.curve_controller = get_curve_controller()
            app.curve_controller.initialize(channels)
            logger.info("CurveController initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize CurveController: {e}")
    except ImportError as e:
        logger.warning(f"CurveController not available - curve features disabled: {e}")


def _initialize_mode_manager(app: Flask) -> None:
    """
    Initialize mode manager for auto/manual mode switching.

    Args:
        app: Flask application instance
    """
    app.mode_manager = None
    app.mode_manager_available = False

    try:
        try:
            from ..utils.mode_manager import get_mode_manager
        except ImportError:
            from grow_pi.utils.mode_manager import get_mode_manager

        app.mode_manager_available = True

        try:
            app.mode_manager = get_mode_manager()
            logger.info(f"ModeManager initialized (current mode: {app.mode_manager.get_mode()})")
        except Exception as e:
            logger.error(f"Failed to initialize ModeManager: {e}")
    except ImportError as e:
        logger.warning(f"ModeManager not available: {e}")


def _initialize_dehumidifier_controller(app: Flask) -> None:
    """
    Initialize dehumidifier controller for automatic humidity control.

    Args:
        app: Flask application instance
    """
    app.dehumidifier_controller = None
    app.dehumidifier_available = False

    try:
        try:
            from ..utils.dehumidifier_controller import get_dehumidifier_controller
        except ImportError:
            from grow_pi.utils.dehumidifier_controller import get_dehumidifier_controller

        app.dehumidifier_available = True

        try:
            app.dehumidifier_controller = get_dehumidifier_controller()
            logger.info("DehumidifierController initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DehumidifierController: {e}")
    except ImportError as e:
        logger.warning(f"DehumidifierController not available: {e}")


def _initialize_dependencies(app: Flask) -> None:
    """
    Initialize the dependencies module with all app singletons.
    This allows blueprints to access services via the dependencies module.

    Args:
        app: Flask application instance
    """
    try:
        from . import dependencies

        # Register all singletons in the dependencies module
        dependencies.init_pwm_controller(app.pwm_controller)
        dependencies.init_dht_sensor(app.dht_sensor, app.dht_available)
        dependencies.init_data_logger(app.data_logger, app.db)
        dependencies.init_curve_controller(
            app.curve_controller,
            app.curve_available
        )
        dependencies.init_mode_manager(
            app.mode_manager,
            app.mode_manager_available
        )

        logger.info("Dependencies module initialized successfully")

    except Exception as e:
        logger.error(f"Failed to initialize dependencies module: {e}")


def _register_blueprints(app: Flask) -> None:
    """
    Register all API blueprints.

    Args:
        app: Flask application instance
    """
    try:
        # Import all blueprints and their initialization functions
        from .blueprints import (
            status_bp,
            temperature_bp, init_temperature_bp,
            logs_bp, init_logs_bp,
            lamps_bp, init_lamps_blueprint,
            mode_bp, init_mode_blueprint
        )
        from .blueprints.curves_bp import curves_bp, init_blueprint as init_curves_blueprint
        from .blueprints.costs_bp import costs_bp
        from .blueprints.dehumidifier_bp import (
            dehumidifier_bp,
            set_dehumidifier_controller,
            set_humidity_reader
        )

        # Get lamp channels configuration
        from .services.lamp_config import get_lamp_channels
        lamp_channels = get_lamp_channels()

        # Initialize blueprints with their dependencies
        # Temperature Blueprint (DHT22 sensor)
        init_temperature_bp(app.dht_sensor)
        logger.info("Temperature blueprint initialized")

        # Logs Blueprint (database and logger)
        init_logs_bp(app.db_available, app.data_logger, None)
        logger.info("Logs blueprint initialized")

        # Lamps Blueprint (PWM controller, channels, logger)
        init_lamps_blueprint(app.pwm_controller, lamp_channels, app.data_logger)
        logger.info("Lamps blueprint initialized")

        # Mode Blueprint (mode manager, curve controller, PWM controller)
        init_mode_blueprint(
            app.mode_manager if app.mode_manager_available else None,
            app.curve_controller if app.curve_available else None,
            app.pwm_controller,
            app.data_logger
        )
        logger.info("Mode blueprint initialized")

        # Curves Blueprint (curve controller, data logger, lamp channels)
        init_curves_blueprint(
            app.curve_controller if app.curve_available else None,
            app.data_logger,
            lamp_channels
        )
        logger.info("Curves blueprint initialized")

        # Dehumidifier Blueprint (requires dehumidifier controller + humidity reader)
        # Initialize dehumidifier controller if available
        if hasattr(app, 'dehumidifier_controller') and app.dehumidifier_controller:
            set_dehumidifier_controller(app.dehumidifier_controller)

            # Set humidity reader function
            def humidity_reader():
                """Read humidity from DHT22 sensor"""
                if app.dht_sensor is None:
                    import random
                    return 60.0 + random.uniform(-5, 5)

                from .blueprints.temperature_bp import read_dht22 as bp_read_dht22
                _, humidity = bp_read_dht22()
                return humidity

            set_humidity_reader(humidity_reader)
            logger.info("Dehumidifier blueprint initialized")

        # Register all blueprints
        app.register_blueprint(status_bp)
        app.register_blueprint(temperature_bp)
        app.register_blueprint(logs_bp)
        app.register_blueprint(lamps_bp)
        app.register_blueprint(mode_bp)
        app.register_blueprint(curves_bp)
        app.register_blueprint(costs_bp)
        app.register_blueprint(dehumidifier_bp)

        logger.info("All blueprints registered successfully")

    except ImportError as e:
        logger.warning(f"Could not import blueprints: {e}")
        logger.info("Blueprints will be added in Phase 2")
    except Exception as e:
        logger.error(f"Error registering blueprints: {e}")
        raise


def run_server(app: Flask = None, host: str = None, port: int = None, debug: bool = False) -> None:
    """
    Run the Flask development server.

    Args:
        app: Flask application instance (creates new if None)
        host: Host address to bind to (uses app config if None)
        port: Port to bind to (uses app config if None)
        debug: Enable debug mode
    """
    if app is None:
        app = create_app({'DEBUG': debug})

    host = host or app.config['API_HOST']
    port = port or app.config['API_PORT']

    logger.info(f"Starting GrowPi Web API v{app.config['API_VERSION']}")
    logger.info(f"Server: http://{host}:{port}")
    logger.info(f"PWM Controller: {'Available' if app.pwm_controller else 'Not available'}")
    logger.info(f"DHT22 Sensor: {'Available' if app.dht_sensor else 'Mock mode'}")
    logger.info(f"DataLogger: {'Available' if app.data_logger else 'Not available'}")
    logger.info(f"CurveController: {'Available' if app.curve_controller else 'Not available'}")
    logger.info(f"ModeManager: {'Available' if app.mode_manager else 'Not available'}")
    logger.info(f"DehumidifierController: {'Available' if hasattr(app, 'dehumidifier_controller') and app.dehumidifier_controller else 'Not available'}")

    # Start data logger
    if app.data_logger:
        try:
            from .services.lamp_config import get_lamp_channels

            # Define sensor reader function
            def read_dht22():
                """Read DHT22 sensor with caching"""
                if app.dht_sensor is None:
                    # Return mock data
                    import random
                    return (22.0 + random.uniform(-2, 2), 60.0 + random.uniform(-5, 5))

                # Use the sensor reader from temperature blueprint
                from .blueprints.temperature_bp import read_dht22 as bp_read_dht22
                return bp_read_dht22()

            # Define lamp reader function
            def get_lamp_states():
                """Get current lamp states for logging"""
                states = {}
                if app.pwm_controller:
                    lamp_channels = get_lamp_channels()
                    current = app.pwm_controller.get_current_state()
                    for channel_id, config in lamp_channels.items():
                        states[channel_id] = {
                            'name': config.name,
                            'intensity': current.get(channel_id, 0)
                        }
                return states

            app.data_logger.set_sensor_reader(read_dht22)
            app.data_logger.set_lamp_reader(get_lamp_states)
            app.data_logger.log_startup_states(get_lamp_states())
            app.data_logger.start()
            logger.info("DataLogger started")
        except Exception as e:
            logger.error(f"Failed to start DataLogger: {e}")

    # Start dehumidifier controller
    if hasattr(app, 'dehumidifier_controller') and app.dehumidifier_controller:
        try:
            # Start automatic control loop (checks every 10 seconds)
            app.dehumidifier_controller.start(check_interval=10)
            logger.info("DehumidifierController started (check_interval: 10s)")
        except Exception as e:
            logger.error(f"Failed to start DehumidifierController: {e}")

    # Run the application
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=app.config['THREADED']
    )


if __name__ == '__main__':
    # Create and run the application
    application = create_app({'DEBUG': True})
    run_server(application, debug=True)
