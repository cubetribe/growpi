#!/usr/bin/env python3
"""
Logs Blueprint
Provides endpoints for historical data logging queries.

Endpoints:
    GET /api/logs/sensors - Sensor reading history
    GET /api/logs/lamps   - Lamp state history
    GET /api/logs/events  - System event history
    GET /api/logs/plugs   - Smart plug history
    GET /api/logs/stats   - Logging statistics
"""

from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

# Create blueprint
logs_bp = Blueprint('logs', __name__)


# ============================================================================
# Shared Instances (injected from api.py)
# ============================================================================

DB_AVAILABLE = False
data_logger = None
get_database = None


def init_logs_bp(db_available: bool, logger_instance, db_getter):
    """Initialize blueprint with database and logger instances."""
    global DB_AVAILABLE, data_logger, get_database
    DB_AVAILABLE = db_available
    data_logger = logger_instance
    get_database = db_getter


# ============================================================================
# Helper Functions
# ============================================================================

def create_response(success: bool, data: dict = None, error: str = None) -> dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# API Routes
# ============================================================================

@logs_bp.route('/api/logs/sensors', methods=['GET'])
def get_sensor_logs():
    """Get sensor reading history

    Query Parameters:
        type (str, optional): Sensor type filter
        hours (int, default=24): Hours of history to retrieve
        limit (int, default=1000): Maximum number of records
    """
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        sensor_type = request.args.get('type')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        readings = db.get_sensor_readings(sensor_type=sensor_type, hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "readings": [r.to_dict() for r in readings],
            "count": len(readings),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_sensor_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@logs_bp.route('/api/logs/lamps', methods=['GET'])
def get_lamp_logs():
    """Get lamp state history

    Query Parameters:
        channel (int, optional): Lamp channel filter (1-4)
        hours (int, default=24): Hours of history to retrieve
        limit (int, default=1000): Maximum number of records
    """
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        channel = request.args.get('channel', type=int)
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        logs = db.get_lamp_state_log(channel=channel, hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "logs": [l.to_dict() for l in logs],
            "count": len(logs),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_lamp_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@logs_bp.route('/api/logs/events', methods=['GET'])
def get_event_logs():
    """Get system event history

    Query Parameters:
        type (str, optional): Event type filter
        severity (str, optional): Severity filter (info, warning, error)
        hours (int, default=24): Hours of history to retrieve
        limit (int, default=100): Maximum number of records
    """
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        event_type = request.args.get('type')
        severity = request.args.get('severity')
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 100))

        db = get_database()
        events = db.get_system_events(
            event_type=event_type,
            severity=severity,
            hours=hours,
            limit=limit
        )

        return jsonify(create_response(True, {
            "events": [e.to_dict() for e in events],
            "count": len(events),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_event_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@logs_bp.route('/api/logs/plugs', methods=['GET'])
def get_plug_logs():
    """Get smart plug history

    Query Parameters:
        hours (int, default=24): Hours of history to retrieve
        limit (int, default=1000): Maximum number of records
    """
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        hours = int(request.args.get('hours', 24))
        limit = int(request.args.get('limit', 1000))

        db = get_database()
        logs = db.get_plug_logs(hours=hours, limit=limit)

        return jsonify(create_response(True, {
            "data": [l.to_dict() for l in logs],
            "count": len(logs),
            "hours": hours
        }))

    except Exception as e:
        logger.error(f"Error in get_plug_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@logs_bp.route('/api/logs/stats', methods=['GET'])
def get_log_stats():
    """Get logging statistics

    Returns database statistics including row counts and status.
    """
    if not DB_AVAILABLE or not data_logger:
        return jsonify(create_response(False, error="Logging not available")), 503

    try:
        status = data_logger.get_status()
        return jsonify(create_response(True, status))

    except Exception as e:
        logger.error(f"Error in get_log_stats: {e}")
        return jsonify(create_response(False, error=str(e))), 500
