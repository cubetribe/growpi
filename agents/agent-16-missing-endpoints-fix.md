# Agent #16: Missing Backend Endpoints Fix

**Date:** 2025-12-06 20:12 CET
**Status:** SUCCESS
**Agent:** Opus 4.5

## Problem

Neue Blueprints (`costs_bp.py`, `dehumidifier_bp.py`) wurden nicht deployed und die `api.py` (der aktive Flask-Server) importierte sie nicht.

**Symptome:**
- Frontend zeigte "Room" und "Kosten" Tabs
- Backend returned 404 (bzw. HTML anstatt JSON) fuer `/api/costs` und `/api/room`

## Root Cause

1. Die Blueprints waren lokal vorhanden, aber nicht auf dem Pi deployed
2. Der aktive Server (`api.py`) importierte und registrierte die Blueprints NICHT
3. `dehumidifier_controller.py` und `tuya_cloud.py` fehlten im utils-Verzeichnis

## Files Deployed

- [x] `costs_bp.py` - Stromkosten API Blueprint
- [x] `dehumidifier_bp.py` - Entfeuchter/Room API Blueprint
- [x] `api.py` - Aktualisiert mit Blueprint-Registrierung
- [x] `dehumidifier_controller.py` - Kopiert aus Backup
- [x] `tuya_cloud.py` - Kopiert aus Backup

## Changes to api.py

1. **Blueprint Import hinzugefuegt** (nach Zeile 149):
```python
try:
    from .blueprints.costs_bp import costs_bp
    from .blueprints.dehumidifier_bp import dehumidifier_bp
    app.register_blueprint(costs_bp)
    app.register_blueprint(dehumidifier_bp)
    logging.info("Registered costs_bp and dehumidifier_bp blueprints")
except ImportError as e:
    logging.warning(f"Could not import blueprints: {e}")
```

2. **DehumidifierController Initialisierung** (nach ModeManager):
```python
dehumidifier_controller = None
try:
    from ..utils.dehumidifier_controller import get_dehumidifier_controller
    dehumidifier_controller = get_dehumidifier_controller()
    # ... dependency injection in blueprint
```

3. **Humidity Reader Injection** (nach read_dht22 Definition):
```python
if dehumidifier_controller is not None:
    from .blueprints.dehumidifier_bp import set_humidity_reader
    set_humidity_reader(read_dht22)
```

## Service Restart Log

```
grow-pi.service - GrowPi Greenhouse Controller
Active: active (running) since Sat 2025-12-06 20:12:03 CET

Logs:
- Registered costs_bp and dehumidifier_bp blueprints
- Loaded dehumidifier config: target=60.0%
- DehumidifierController initialized with Tuya Cloud
- Dehumidifier state synced from cloud: OFF
- DehumidifierController initialized and injected into blueprint
- Humidity reader set for dehumidifier blueprint
```

## API Health Check

| Endpoint | Status | Response (Summary) |
|----------|--------|----------|
| `/api/costs?period=today` | 200 | success=True, total_kwh=5.14, devices=6 |
| `/api/costs/config` | 200 | kwh_price=0.3, currency=EUR, 6 devices |
| `/api/room` | 200 | temp=24.2, humidity=62.4, dehumidifier.tuya_available=true |
| `/api/room/config` | 200 | target=60.0%, threshold_high=65.0%, threshold_low=55.0% |
| `/api/health` | 200 | status=healthy, version=1.2.0 |
| `/api/status` | 200 | 4 lamps, temp=24.3, humidity=62.2 |

## Smoke Test Results

```
=== Core Endpoints ===
PASS: GET /api/health (200)
PASS: GET /api/status (200)
PASS: GET /api/temperature (200)
PASS: GET /api/mode (200)

=== Curves ===
PASS: GET /api/curves (200)
PASS: GET /api/curves/intensities (200)

=== Logs ===
PASS: GET /api/logs/sensors?hours=1&limit=10 (200)
PASS: GET /api/logs/lamps?hours=1&limit=10 (200)
PASS: GET /api/logs/events?hours=1&limit=10 (200)
PASS: GET /api/logs/stats (200)

=== Costs (NEW) ===
PASS: GET /api/costs?period=today (200)
PASS: GET /api/costs/config (200)

=== Room/Dehumidifier (NEW) ===
PASS: GET /api/room (200)
PASS: GET /api/room/config (200)

All 14/14 tests PASSED
```

## Verification Checklist

- [x] Alle neuen Endpoints return 200 OK
- [x] Alte Endpoints funktionieren weiterhin
- [x] Service laeuft stabil (`active (running)`)
- [x] Keine kritischen Errors in Logs
- [x] Dehumidifier Controller mit Tuya Cloud verbunden
- [x] Stromkosten-Daten werden aus Datenbank gelesen

## Technical Notes

### Endpoint Mapping

| Blueprint | Endpoints |
|-----------|-----------|
| costs_bp | `/api/costs`, `/api/costs/config` |
| dehumidifier_bp | `/api/room`, `/api/room/config`, `/api/room/dehumidifier` |

### Dependencies Required

- `tinytuya` - Tuya Smart Home Cloud API
- `grow_pi.utils.tuya_cloud` - Tuya Cloud Wrapper
- `grow_pi.utils.dehumidifier_controller` - Entfeuchter-Steuerung

## Status: SUCCESS

User kann jetzt die **Room** und **Kosten** Tabs im Frontend testen:
- http://192.168.0.86:5000 -> Room Tab
- http://192.168.0.86:5000 -> Kosten Tab

## Files Modified (Local)

- `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/web/api.py`
  - Added Blueprint imports and registration
  - Added DehumidifierController initialization
  - Added Humidity reader injection

## Next Steps (Optional)

1. **Sync local files:** Die lokalen utils-Dateien (`dehumidifier_controller.py`, `tuya_cloud.py`) sollten vom Pi zurueck ins Repository kopiert werden
2. **Update smoke_test.sh:** Das Script testet `/api/dehumidifier/*`, aber die Blueprints verwenden `/api/room/*`
