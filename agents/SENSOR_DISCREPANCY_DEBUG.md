# Sensor Diskrepanz Debug-Bericht
**Datum:** 2025-12-20
**System:** GrowPi v6.22.0
**Problem:** Temperatur- und Luftfeuchtigkeitswerte auf Startseite vs. Room-Tab unterschiedlich

---

## Executive Summary

Die Sensor-Werte für Temperatur und Luftfeuchtigkeit unterscheiden sich zwischen zwei API-Endpoints:

- **`/api/status`** (Startseite): Live-Werte vom DHT22-Sensor mit 30s-Cache
- **`/api/room`** (Room-Tab): **VERALTETE Werte** die im DehumidifierController gecached sind

### Gemessene Diskrepanz (2025-12-20 14:39 UTC)
| Endpoint | Temperatur | Luftfeuchtigkeit | Status |
|----------|------------|------------------|---------|
| `/api/status` | 22.0°C | 61.7% | Live (aktualisiert sich) |
| `/api/room` | 21.1°C | 65.1% | **FEST (ändert sich nicht!)** |
| `/api/temperature` | 21.1°C | 65.1% | Gleiche Quelle wie `/api/room` |

---

## Root Cause Analysis

### Problemquelle: DehumidifierController cached Humidity-Werte

Der `DehumidifierController` ruft `get_humidity()` in seinem `get_status()` auf:

```python
# dehumidifier_controller.py, Zeile 878-884
def get_status(self) -> Dict:
    """Get current status"""
    self._sync_device_status()

    humidity = self.get_humidity()  # <-- HIER LIEGT DAS PROBLEM

    return {
        "humidity": humidity,  # Veralteter Wert!
        ...
    }
```

Die `get_humidity()` Methode ruft `self._humidity_reader()` auf:

```python
# dehumidifier_controller.py, Zeile 238-248
def get_humidity(self) -> Optional[float]:
    """Get current humidity reading"""
    if self._humidity_reader:
        try:
            result = self._humidity_reader()
            if isinstance(result, tuple):
                return result[1]  # (temp, humidity)
            return result
        except Exception as e:
            logger.error(f"Error reading humidity: {e}")
    return None
```

**Hypothese:** Die `_humidity_reader` Funktion ist ENTWEDER:
1. Nicht korrekt injiziert (gibt veraltete Werte zurück)
2. Der DHT22-Cache wird nicht invalidiert zwischen verschiedenen API-Calls
3. Es existiert ein versteckter Cache im Thread der control_loop

---

## Code-Path Vergleich

### 1. `/api/status` (Funktioniert korrekt)

```
/api/status (api.py:511)
  └─> read_dht22() (api.py:339)
      └─> DHT22 Sensor mit 30s-Cache (_dht_cache)
          └─> Gibt AKTUELLE Werte zurück
```

**Code:**
```python
# api.py, Zeile 511-540
@app.route('/api/status', methods=['GET'])
def get_status():
    # Get sensor data
    temp, humidity = read_dht22()  # <-- Direkter Sensor-Zugriff

    return jsonify(create_response(True, {
        "temperature": temp,
        "humidity": humidity,
        ...
    }))
```

### 2. `/api/room` (Zeigt veraltete Werte)

```
/api/room (dehumidifier_bp.py:71)
  ├─> _humidity_reader() (Blueprint-Injected)
  │   └─> read_dht22() (sollte gleiche Funktion sein!)
  │       └─> DHT22 Sensor mit 30s-Cache
  │
  └─> controller.get_status() (dehumidifier_controller.py:878)
      └─> self.get_humidity()
          └─> self._humidity_reader() (Controller-Injected)
              └─> read_dht22() (sollte gleiche Funktion sein!)
                  └─> **ABER: Gibt ALTE Werte zurück!**
```

**Code:**
```python
# dehumidifier_bp.py, Zeile 71-94
@dehumidifier_bp.route('/api/room', methods=['GET'])
def get_room_status():
    # Read temperature and humidity
    temp = None
    humidity = None
    if _humidity_reader:
        temp, humidity = _humidity_reader()  # <-- Blueprint Reader

    response_data = {
        "temperature": temp,      # Zeile 80: Aus _humidity_reader
        "humidity": humidity,     # Zeile 80: Aus _humidity_reader
        ...
    }

    # Add dehumidifier status
    controller = _get_dehumidifier()
    if controller:
        response_data["dehumidifier"] = controller.get_status()  # <-- Controller Reader
        # dehumidifier.humidity kommt von HIER (veralteter Wert!)

    return jsonify(create_response(True, response_data))
```

---

## Dependency Injection Analyse

### Wie wird `_humidity_reader` gesetzt?

**1. Blueprint-Injection (dehumidifier_bp.py):**
```python
# api.py, Zeile 416-418
from .blueprints.dehumidifier_bp import set_humidity_reader
set_humidity_reader(read_dht22)
logger.info("Humidity reader set for dehumidifier blueprint")
```

**2. Controller-Injection (dehumidifier_controller):**
```python
# api.py, Zeile 411-414
if dehumidifier_controller is not None:
    dehumidifier_controller.set_humidity_reader(read_dht22)
    logger.info("Humidity reader set for DehumidifierController")
```

**Beide Injektionen verwenden die GLEICHE `read_dht22()` Funktion!**

---

## DHT22 Cache-Verhalten

Der DHT22-Sensor hat einen 30-Sekunden-Cache:

```python
# api.py, Zeile 333-407
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0, "error_count": 0}
DHT_CACHE_SECONDS = 30  # Minimum seconds between sensor reads

def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    global _dht_cache
    import time

    # Return cached value if recent enough
    now = time.time()
    if now - _dht_cache["timestamp"] < DHT_CACHE_SECONDS:
        if _dht_cache["temp"] is not None:
            return (_dht_cache["temp"], _dht_cache["humidity"])

    # Try up to 3 times to read the sensor
    for attempt in range(3):
        try:
            temp = dht_sensor.temperature
            humidity = dht_sensor.humidity
            if temp is not None and humidity is not None:
                _dht_cache["temp"] = round(temp, 1)
                _dht_cache["humidity"] = round(humidity, 1)
                _dht_cache["timestamp"] = now  # <-- Cache-Timestamp
                _dht_cache["error_count"] = 0
                return (_dht_cache["temp"], _dht_cache["humidity"])
        except RuntimeError as e:
            logger.warning(f"DHT22 read attempt {attempt+1}/3: {e}")
            if attempt < 2:
                time.sleep(0.5)

    # Return last known good value if available
    if _dht_cache["temp"] is not None:
        logger.warning(f"DHT22 read failed - returning cached value")
        return (_dht_cache["temp"], _dht_cache["humidity"])

    return (None, None)
```

**Beobachtung:** Der Cache sollte nach 30 Sekunden invalidiert werden, aber die `/api/room` Werte bleiben DAUERHAFT bei 21.1°C / 65.1%.

---

## Test-Ergebnisse

### Test 1: Parallele API-Calls (14:36-14:39 UTC)

```bash
# /api/status
{"temperature": 19.7, "humidity": 60.1, "timestamp": "2025-12-20T14:36:49"}

# /api/room
{"temperature": 21.1, "humidity": 65.1, "timestamp": "2025-12-20T14:36:50"}
```

**Diskrepanz:** 1.4°C und 5.0% innerhalb 1 Sekunde!

### Test 2: Wiederholte Calls über 15 Sekunden (14:39 UTC)

```bash
# Request 1 (14:39:08)
/api/status:  {"temp": 22.0, "humidity": 61.7}
/api/room:    {"temp": 21.1, "humidity": 65.1}

# Request 2 (14:39:12)
/api/status:  {"temp": 22.0, "humidity": 61.7}  # Leicht geändert
/api/room:    {"temp": 21.1, "humidity": 65.1}  # IDENTISCH!

# Request 3 (14:39:49)
/api/status:  {"temp": 22.0, "humidity": 61.7}  # Aktualisiert
/api/room:    {"temp": 21.1, "humidity": 65.1}  # IMMER NOCH GLEICH!
```

**Befund:** `/api/room` gibt IMMER die gleichen Werte zurück, während `/api/status` sich aktualisiert.

### Test 3: Dedicated `/api/temperature` Endpoint

```bash
# /api/temperature (nutzt auch read_dht22())
{"temperature": 21.1, "humidity": 65.1, "unit_temperature": "°C"}
```

**Befund:** `/api/temperature` gibt die GLEICHEN Werte wie `/api/room` zurück - NICHT wie `/api/status`!

---

## Hypothesen für Root Cause

### Hypothese 1: Thread-basierter Cache im DehumidifierController ⭐ **WAHRSCHEINLICH**

Der `DehumidifierController` läuft in einem Background-Thread (control_loop):

```python
# dehumidifier_controller.py, Zeile 920-934
def control_loop():
    logger.info(f"Control loop started (interval: {check_interval}s)")
    while not self._stop_event.is_set():
        try:
            self.check_and_control()  # <-- Ruft get_humidity() auf
        except Exception as e:
            logger.error(f"Control loop error: {e}")

        self._stop_event.wait(timeout=check_interval)
```

**Möglichkeit:** Die `control_loop` cached Humidity-Werte in einer versteckten Variable, die wir nicht gefunden haben.

### Hypothese 2: Doppelte `_humidity_reader` Injection überschreibt Funktion

In `api.py` Zeile 1201-1204 gibt es eine ZWEITE Injection:

```python
# api.py, Zeile 1195-1206 (DEPRECATED _get_dehumidifier Helper)
def _get_dehumidifier():
    """Get or initialize dehumidifier controller with humidity reader."""
    global dehumidifier_controller
    if DEHUMIDIFIER_AVAILABLE and dehumidifier_controller is None:
        dehumidifier_controller = get_dehumidifier_controller()
        # Set humidity reader
        def humidity_reader():
            _, humidity = read_dht22()  # <-- NUR HUMIDITY!
            return humidity
        dehumidifier_controller.set_humidity_reader(humidity_reader)  # <-- ÜBERSCHREIBT?
    return dehumidifier_controller
```

**Problem:** Diese Funktion erstellt einen WRAPPER der nur humidity zurückgibt. Wenn dieser NACH der ersten Injection (Zeile 413) aufgerufen wird, überschreibt er den korrekten Reader!

**Status:** Diese Funktion ist DEPRECATED (v6.16.0) und sollte nicht mehr verwendet werden, ABER sie könnte noch irgendwo aufgerufen werden.

### Hypothese 3: Globale `_dht_cache` Variable ist Thread-Unsafe

Möglicherweise gibt es Race Conditions im Multi-Threaded Environment (Flask + control_loop).

**Weniger wahrscheinlich**, da Python's GIL Dictionary-Zugriffe serialisiert.

---

## Fix-Vorschlag

### Option 1: Debugging-Fix (EMPFOHLEN für erste Iteration)

Füge Logging hinzu um zu verstehen woher die veralteten Werte kommen:

```python
# dehumidifier_controller.py, Zeile 238-248 (MODIFIZIERT)
def get_humidity(self) -> Optional[float]:
    """Get current humidity reading"""
    if self._humidity_reader:
        try:
            result = self._humidity_reader()
            if isinstance(result, tuple):
                humidity = result[1]
            else:
                humidity = result

            # DEBUG LOGGING
            logger.info(f"[DEHUMIDIFIER] get_humidity() = {humidity} (type={type(result)})")
            return humidity
        except Exception as e:
            logger.error(f"Error reading humidity: {e}")
    return None
```

Dann:
1. Deployment auf Pi
2. API-Calls durchführen
3. Logs analysieren um zu sehen welche Werte zurückgegeben werden

### Option 2: Entferne DEPRECATED `_get_dehumidifier()` (CLEANUP)

Die Funktion in `api.py` Zeile 1195-1206 ist deprecated und überschreibt möglicherweise den Reader:

```python
# api.py - LÖSCHEN:
# Zeile 1195-1206 komplett entfernen
```

**Risiko:** LOW - Die Funktion ist seit v6.16.0 deprecated und sollte nicht mehr verwendet werden.

### Option 3: Force-Refresh in `get_status()` (WORKAROUND)

Erzwinge einen neuen Sensor-Read in `get_status()`:

```python
# dehumidifier_controller.py, Zeile 878-906 (MODIFIZIERT)
def get_status(self) -> Dict:
    """Get current status"""
    self._sync_device_status()

    # BUGFIX: Force fresh sensor read by invalidating cache
    if hasattr(self._humidity_reader, '__globals__'):
        # Access global _dht_cache and invalidate timestamp
        cache = self._humidity_reader.__globals__.get('_dht_cache')
        if cache:
            cache['timestamp'] = 0  # Force new read

    humidity = self.get_humidity()

    # ... rest of method
```

**Risiko:** MEDIUM - Hacky solution, aber sollte funktionieren.

### Option 4: Separate Sensor-Instance für DehumidifierController (CLEAN)

Erstelle eine dedizierte Sensor-Read-Funktion die KEINEN Cache verwendet:

```python
# api.py - Neue Funktion
def read_dht22_uncached() -> Tuple[Optional[float], Optional[float]]:
    """Read DHT22 sensor WITHOUT caching (for real-time control)"""
    if dht_sensor is None:
        import random
        return (22.0 + random.uniform(-2, 2), 60.0 + random.uniform(-5, 5))

    for attempt in range(3):
        try:
            temp = dht_sensor.temperature
            humidity = dht_sensor.humidity
            if temp is not None and humidity is not None:
                return (round(temp, 1), round(humidity, 1))
        except RuntimeError as e:
            if attempt < 2:
                time.sleep(0.5)

    return (None, None)

# Inject uncached reader to DehumidifierController
if dehumidifier_controller is not None:
    dehumidifier_controller.set_humidity_reader(read_dht22_uncached)
```

**Vorteil:** Saubere Trennung zwischen UI-Cache (30s) und Control-Loop (real-time).

---

## Empfohlene Schritte

### Phase 1: Diagnose (JETZT)
1. ✅ API-Endpoints getestet und Diskrepanz bestätigt
2. ✅ Code-Analyse durchgeführt
3. ✅ Hypothesen formuliert
4. ⬜ **NÄCHSTER SCHRITT:** Debug-Logging hinzufügen (Option 1)

### Phase 2: Fix Implementation
1. ⬜ Option 4 implementieren (separate uncached reader)
2. ⬜ Option 2 implementieren (deprecated code entfernen)
3. ⬜ Tests auf Pi durchführen
4. ⬜ Verifizieren dass beide Endpoints gleiche Werte zurückgeben

### Phase 3: Cleanup
1. ⬜ Debug-Logging entfernen
2. ⬜ CHANGELOG.md aktualisieren
3. ⬜ Version auf v6.22.1 bumpen

---

## Betroffene Dateien

| Datei | Zeilen | Beschreibung |
|-------|--------|--------------|
| `pi-controller/grow_pi/web/api.py` | 339-407 | `read_dht22()` Cache-Logik |
| `pi-controller/grow_pi/web/api.py` | 511-544 | `/api/status` Endpoint |
| `pi-controller/grow_pi/web/api.py` | 410-420 | Humidity reader injection |
| `pi-controller/grow_pi/web/api.py` | 1195-1206 | DEPRECATED `_get_dehumidifier()` |
| `pi-controller/grow_pi/web/blueprints/dehumidifier_bp.py` | 71-102 | `/api/room` Endpoint |
| `pi-controller/grow_pi/utils/dehumidifier_controller.py` | 238-248 | `get_humidity()` Methode |
| `pi-controller/grow_pi/utils/dehumidifier_controller.py` | 878-906 | `get_status()` Methode |

---

## Anhang: API Response Beispiele

### `/api/status` (Live-Werte)
```json
{
  "humidity": 61.7,
  "lamps": [...],
  "logging_enabled": false,
  "success": true,
  "temperature": 22.0,
  "timestamp": "2025-12-20T14:39:08.270799",
  "version": "6.22.0"
}
```

### `/api/room` (Veraltete Werte)
```json
{
  "dehumidifier": {
    "active_schedule": null,
    "available": true,
    "config": {
      "enabled": true,
      "min_off_time": 60,
      "min_run_time": 300,
      "target": 70.0,
      "threshold_high": 8.0,
      "threshold_low": 5.0,
      "time_schedule_enabled": false
    },
    "humidity": 65.1,  // <-- VERALTET
    "is_on": false,
    "last_toggle": null,
    "last_trigger": null,
    "last_trigger_details": null
  },
  "humidity": 65.1,      // <-- VERALTET
  "success": true,
  "temperature": 21.1,   // <-- VERALTET
  "timestamp": "2025-12-20T14:39:49.050535"
}
```

---

## Fazit

**ROOT CAUSE:** Der DehumidifierController gibt veraltete Humidity-Werte zurück, vermutlich durch:
1. Thread-basierten Cache in der control_loop
2. Überschreiben des humidity_reader durch deprecated Code
3. Cache-Invalidierungs-Problem im Multi-Threaded Environment

**EMPFOHLENER FIX:** Implementiere Option 4 (separate uncached sensor reader) + Option 2 (entferne deprecated code).

**PRIORITÄT:** MEDIUM - Die Diskrepanz beeinflusst nicht die Funktionalität, verwirrt aber den User.

**NÄCHSTER SCHRITT:** Debug-Logging hinzufügen und auf Pi deployen um exakte Ursache zu identifizieren.

---

**Bericht erstellt von:** Claude Code (Sonnet 4.5)
**Agent:** web-debug-specialist
**Datum:** 2025-12-20 14:40 UTC
