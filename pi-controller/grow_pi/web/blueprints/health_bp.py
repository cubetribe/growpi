#!/usr/bin/env python3
"""
Health Check Blueprint

Provides comprehensive health check endpoints for external monitoring,
Kubernetes-style probes, and system metrics.

Version: 6.22.5
"""

import time
import os
import logging
from flask import Blueprint, jsonify
from typing import Dict, Any

logger = logging.getLogger(__name__)

health_bp = Blueprint('health', __name__, url_prefix='/api/health')

# Track application start time
START_TIME = time.time()


@health_bp.route('/', methods=['GET'])
def health_check() -> tuple:
    """
    Comprehensive health check endpoint.

    Returns detailed status of all subsystems including:
    - Application version and uptime
    - Database connectivity
    - Sensor health (including circuit breaker state)
    - System metrics (CPU, memory, disk)
    - Active threads

    Returns:
        JSON response with health status and 200/503 status code
    """
    from grow_pi.version import __version__

    health = {
        "status": "healthy",
        "version": __version__,
        "timestamp": time.time(),
        "uptime_seconds": round(time.time() - START_TIME, 2),
        "checks": {}
    }

    # Database health check
    try:
        from grow_pi.database.db import get_database
        db = get_database()

        # Test database connection with a simple query
        start = time.time()
        db.get_connection()  # Will raise if connection fails
        response_time = (time.time() - start) * 1000

        health["checks"]["database"] = {
            "status": "healthy",
            "response_time_ms": round(response_time, 2)
        }
    except Exception as e:
        health["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
        logger.error(f"Database health check failed: {e}")

    # Sensor health check
    try:
        from grow_pi.utils.sensor_cache import get_cache_status
        sensor_status = get_cache_status()

        # Determine sensor health based on error count and cache freshness
        sensor_healthy = True
        sensor_issues = []

        if sensor_status.get("error_count", 0) > 5:
            sensor_healthy = False
            sensor_issues.append(f"High error count: {sensor_status['error_count']}")

        if sensor_status.get("cache_age", 0) > 60:
            sensor_healthy = False
            sensor_issues.append(f"Stale cache: {sensor_status['cache_age']:.1f}s old")

        health["checks"]["sensors"] = {
            "status": "healthy" if sensor_healthy else "degraded",
            "error_count": sensor_status.get("error_count", 0),
            "cache_age": round(sensor_status.get("cache_age", 0), 2),
            "temp": sensor_status.get("temp"),
            "humidity": sensor_status.get("humidity")
        }

        if sensor_issues:
            health["checks"]["sensors"]["issues"] = sensor_issues
            health["status"] = "degraded"

    except Exception as e:
        health["checks"]["sensors"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health["status"] = "degraded"
        logger.error(f"Sensor health check failed: {e}")

    # System metrics
    try:
        import psutil

        health["system"] = {
            "cpu_percent": round(psutil.cpu_percent(interval=0.1), 1),
            "memory_percent": round(psutil.virtual_memory().percent, 1),
            "disk_percent": round(psutil.disk_usage('/').percent, 1),
            "load_average_1m": round(os.getloadavg()[0], 2)
        }

        # Check for critical system issues
        if health["system"]["memory_percent"] > 90:
            health["status"] = "degraded"
            logger.warning(f"High memory usage: {health['system']['memory_percent']}%")

        if health["system"]["disk_percent"] > 90:
            health["status"] = "degraded"
            logger.warning(f"High disk usage: {health['system']['disk_percent']}%")

    except Exception as e:
        health["system"] = {"error": str(e)}
        logger.error(f"System metrics check failed: {e}")

    # Thread health
    try:
        import threading

        health["threads"] = {
            "active_count": threading.active_count(),
            "thread_names": [t.name for t in threading.enumerate()]
        }
    except Exception as e:
        health["threads"] = {"error": str(e)}
        logger.error(f"Thread check failed: {e}")

    # Return 503 if unhealthy, 200 otherwise
    status_code = 503 if health["status"] == "unhealthy" else 200

    return jsonify(health), status_code


@health_bp.route('/ready', methods=['GET'])
def readiness_check() -> tuple:
    """
    Kubernetes-style readiness probe.

    Quick check if service can handle requests.
    Checks database connectivity only.

    Returns:
        JSON response with ready status and 200/503 status code
    """
    ready = True
    checks = {}

    # Check database is accessible
    try:
        from grow_pi.database.db import get_database
        db = get_database()
        db.get_connection()
        checks["database"] = "ready"
    except Exception as e:
        ready = False
        checks["database"] = f"not ready: {str(e)}"

    status_code = 200 if ready else 503

    return jsonify({
        "ready": ready,
        "checks": checks
    }), status_code


@health_bp.route('/live', methods=['GET'])
def liveness_check() -> tuple:
    """
    Kubernetes-style liveness probe.

    Simple check if service is alive and responding.
    Always returns 200 unless application is completely broken.

    Returns:
        JSON response with alive status and 200 status code
    """
    return jsonify({
        "alive": True,
        "timestamp": time.time()
    }), 200


@health_bp.route('/metrics', methods=['GET'])
def metrics() -> tuple:
    """
    Prometheus-style metrics endpoint.

    Returns system and application metrics in a structured format.

    Returns:
        JSON response with detailed metrics
    """
    try:
        import psutil
        from grow_pi.version import __version__

        # System metrics
        cpu_times = psutil.cpu_times()
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        net = psutil.net_io_counters()

        metrics_data = {
            "version": __version__,
            "uptime_seconds": round(time.time() - START_TIME, 2),
            "timestamp": time.time(),

            "cpu": {
                "percent": round(psutil.cpu_percent(interval=0.1), 1),
                "user_time": round(cpu_times.user, 2),
                "system_time": round(cpu_times.system, 2),
                "load_average": {
                    "1m": round(os.getloadavg()[0], 2),
                    "5m": round(os.getloadavg()[1], 2),
                    "15m": round(os.getloadavg()[2], 2)
                }
            },

            "memory": {
                "percent": round(mem.percent, 1),
                "total_mb": round(mem.total / (1024 * 1024), 1),
                "available_mb": round(mem.available / (1024 * 1024), 1),
                "used_mb": round(mem.used / (1024 * 1024), 1)
            },

            "disk": {
                "percent": round(disk.percent, 1),
                "total_gb": round(disk.total / (1024**3), 2),
                "used_gb": round(disk.used / (1024**3), 2),
                "free_gb": round(disk.free / (1024**3), 2)
            },

            "network": {
                "bytes_sent": net.bytes_sent,
                "bytes_recv": net.bytes_recv,
                "packets_sent": net.packets_sent,
                "packets_recv": net.packets_recv,
                "errors_in": net.errin,
                "errors_out": net.errout
            },

            "process": {
                "threads": threading.active_count() if 'threading' in dir() else 0,
                "open_files": len(psutil.Process().open_files()),
                "connections": len(psutil.Process().connections())
            }
        }

        # Add sensor metrics if available
        try:
            from grow_pi.utils.sensor_cache import get_cache_status
            sensor_status = get_cache_status()
            metrics_data["sensors"] = {
                "error_count": sensor_status.get("error_count", 0),
                "cache_age": round(sensor_status.get("cache_age", 0), 2),
                "temperature": sensor_status.get("temp"),
                "humidity": sensor_status.get("humidity")
            }
        except Exception:
            pass

        return jsonify(metrics_data), 200

    except Exception as e:
        logger.error(f"Metrics endpoint failed: {e}")
        return jsonify({"error": str(e)}), 500
