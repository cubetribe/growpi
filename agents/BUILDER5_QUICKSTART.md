# Builder 5: Observability Layer - Quick Start

## 🎯 Was wurde implementiert?

### 1. Health Check Endpoints
```bash
# Voller Health Check
curl http://localhost:5000/api/health/

# Kubernetes Readiness
curl http://localhost:5000/api/health/ready

# Kubernetes Liveness
curl http://localhost:5000/api/health/live

# Prometheus Metrics
curl http://localhost:5000/api/health/metrics
```

### 2. Incident Snapshots
```python
from grow_pi.utils.incident_snapshot import IncidentSnapshot

try:
    critical_operation()
except Exception as e:
    snapshot_id = IncidentSnapshot.capture(error=e, context={"operation": "test"})
    # Snapshot saved to: /var/log/grow-pi/incidents/incident_YYYYMMDD_HHMMSS.json
```

### 3. Structured Logging
```python
from grow_pi.utils.structured_logging import get_structured_logger, log_operation

logger = get_structured_logger(__name__, component="sensor", device="DHT22")
logger.info("Reading sensor")  # Output: [component=sensor, device=DHT22] Reading sensor

@log_operation("read_sensor")
def read_dht22():
    # Automatically logs START/END with timing
    pass
```

---

## 📁 Neue Dateien

1. **`grow_pi/web/blueprints/health_bp.py`** - Health check endpoints
2. **`grow_pi/utils/incident_snapshot.py`** - Incident capture system
3. **`grow_pi/utils/structured_logging.py`** - Logging utilities

---

## 🔧 Geänderte Dateien

1. **`grow_pi/utils/sensor_cache.py`** - Added `get_sensor_health()`, `get_cache_state()`
2. **`grow_pi/web/app.py`** - Registered health blueprint

---

## 🧪 Schnelltest

```bash
# 1. Start GrowPi
cd /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller
python -m grow_pi.web.app

# 2. Test Health (in anderem Terminal)
curl http://localhost:5000/api/health/ | jq

# 3. Test Incident Snapshot
python3 << 'PYTHON'
from grow_pi.utils.incident_snapshot import IncidentSnapshot
try:
    raise RuntimeError("Test")
except Exception as e:
    snapshot_id = IncidentSnapshot.capture(e, {"test": True})
    print(f"Snapshot: {snapshot_id}")
PYTHON
```

---

## 📊 Health Check Response Beispiel

```json
{
  "status": "healthy",
  "version": "6.22.5",
  "uptime_seconds": 86400.5,
  "checks": {
    "database": {"status": "healthy", "response_time_ms": 2.34},
    "sensors": {"status": "healthy", "error_count": 0, "cache_age": 3.2}
  },
  "system": {
    "cpu_percent": 15.2,
    "memory_percent": 42.1,
    "disk_percent": 35.8
  }
}
```

---

## 🚀 Deployment auf Pi

```bash
# 1. Erstelle Incident-Verzeichnis
sudo mkdir -p /var/log/grow-pi/incidents
sudo chown -R admin:admin /var/log/grow-pi

# 2. Service neu starten
sudo systemctl restart grow-pi

# 3. Verify
curl http://localhost:5000/api/health/
```

---

## 📝 Weitere Details

Siehe: `/agents/BUILDER5_OBSERVABILITY.md` (vollständiger Report)
