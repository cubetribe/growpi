from flask import Flask

from grow_pi.web.blueprints.health_bp import health_bp
from grow_pi.web.blueprints.status_bp import evaluate_health_status, status_bp


def _base_system_metrics():
    return {
        "cpu_temp_status": "normal",
        "memory_status": "normal",
        "disk_status": "normal",
        "power": {
            "issues_now": [],
            "issues_occurred": [],
            "under_voltage_now": False,
            "arm_frequency_capped_now": False,
            "currently_throttled": False,
            "soft_temperature_limit_now": False,
            "under_voltage_occurred": False,
            "arm_frequency_capped_occurred": False,
            "throttling_occurred": False,
            "soft_temperature_limit_occurred": False,
        },
    }


def test_evaluate_health_status_reports_healthy_when_clean():
    status, issues = evaluate_health_status(_base_system_metrics(), {"state": "closed"})

    assert status == "healthy"
    assert issues == []


def test_evaluate_health_status_marks_current_power_fault_critical():
    metrics = _base_system_metrics()
    metrics["power"]["under_voltage_now"] = True

    status, issues = evaluate_health_status(metrics, {"state": "closed"})

    assert status == "critical"
    assert "power.under_voltage_now" in issues


def test_evaluate_health_status_marks_historical_power_fault_warning():
    metrics = _base_system_metrics()
    metrics["power"]["throttling_occurred"] = True

    status, issues = evaluate_health_status(metrics, {"state": "closed"})

    assert status == "warning"
    assert "power.throttling_occurred" in issues


def test_evaluate_health_status_marks_power_read_failure_warning():
    metrics = _base_system_metrics()
    metrics["power"] = {
        "available": False,
        "healthy": False,
        "error": "vcgencmd timeout",
        "issues_now": [],
        "issues_occurred": [],
    }

    status, issues = evaluate_health_status(metrics, {"state": "closed"})

    assert status == "warning"
    assert "power.read_failed" in issues


def test_evaluate_health_status_marks_open_sensor_circuit_breaker_critical():
    status, issues = evaluate_health_status(_base_system_metrics(), {"state": "open"})

    assert status == "critical"
    assert "sensor.circuit_breaker.open" in issues


def test_health_endpoint_family_routes_are_registered_for_production_entrypoint():
    app = Flask(__name__)
    app.register_blueprint(status_bp, url_prefix="/api")
    app.register_blueprint(health_bp)

    routes = {rule.rule for rule in app.url_map.iter_rules()}

    assert "/api/health" in routes
    assert "/api/health/" in routes
    assert "/api/health/ready" in routes
    assert "/api/health/live" in routes
    assert "/api/health/metrics" in routes
    assert "/api/health/detailed" in routes
