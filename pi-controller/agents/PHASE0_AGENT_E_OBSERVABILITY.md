# Agent E: Observability / Logging & Metrics Analysis Report

**Project:** GrowPi Raspberry Pi Controller
**Agent:** Agent E (Observability Specialist)
**Date:** 2025-12-26
**Context:** System zeigt Sensor-Freeze/Lockup-Probleme, schwer reproduzierbar

---

## Executive Summary

Das GrowPi-System verfügt über eine **solide Logging-Grundlage** mit Python's `logging`-Modul und einer SQLite-basierten Event/Metrics-Datenbank. **JEDOCH**: Es fehlen **kritische Performance-Metriken** und **strukturierte Incident-Snapshots** für Freeze-Diagnose.

**Hauptprobleme:**
1. ❌ **Keine Sensor-Read-Duration-Metriken** – wir wissen nicht, ob DHT22-Reads langsam werden
2. ❌ **Keine DB-Write-Latency** – DB-Locks könnten System blockieren
3. ❌ **Keine Loop-Lag-Metriken** – wir sehen nicht, ob Main-Loop hängt
4. ⚠️ **Inconsistent Logging** – manche Module loggen DEBUG, andere ERROR-only
5. ⚠️ **Keine Correlation IDs** – multi-threaded Logs schwer zu tracken

---

## 1. Aktueller Logging-Stand

### 1.1 Logging-Framework

**Framework:** Python `logging` (stdlib)
**Configuration:** `logging.basicConfig()` in `main.py:116-120`

```python
# grow_pi/main.py:116-120
logging.basicConfig(
    level=level,  # From config YAML (default: INFO)
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
```

**Bewertung:**
- ✅ **Zeitstempel mit Sekunden-Genauigkeit**
- ❌ **Keine Millisekunden** – kritisch für Performance-Debugging
- ❌ **Keine Timezone-Info** – bei Remote-Debugging problematisch
- ❌ **Keine Thread-ID** – DataLogger läuft in 3 Threads!

**Empfohlenes Format:**
```python
format="%(asctime)s.%(msecs)03d [%(threadName)s] %(name)s - %(levelname)s - %(message)s",
datefmt="%Y-%m-%d %H:%M:%S"
```

---

### 1.2 Log-Levels Konsistenz

**Analyse:** Grep zeigt **582 log statements** über 33 Dateien.

**Verteilung (Stichprobe):**

| Modul | DEBUG | INFO | WARNING | ERROR | CRITICAL |
|-------|-------|------|---------|-------|----------|
| `sensor_cache.py` | 3 | 0 | 4 | 2 | 1 |
| `database/logger.py` | 2 | 4 | 1 | 3 | 0 |
| `main.py` | 0 | 12 | 1 | 3 | 0 |
| `pwm_controller.py` | 2 | 2 | 2 | 2 | 0 |

**Problem:** Sensor-Reads nutzen nur `logger.debug()` – bei INFO-Level sehen wir **keine Sensor-Aktivität**!

```python
# database/logger.py:233 (Sensor-Read)
logger.debug(f"Logged temperature: {temp}°C")  # ❌ INVISIBLE bei INFO-Level
```

**Recommendation:**
- Sensor-Read-**Start** → INFO
- Sensor-Read-**Success** → DEBUG
- Sensor-Read-**Failure** → WARNING (nach 3 retries)

---

### 1.3 Structured Logging

**Current State:** Freitext-Logging mit f-Strings

```python
# sensor_cache.py:206
logger.warning(f"DHT22 read failed (error #{_sensor_cache['error_count']}) - returning cached value")
```

**Problem:** Nicht maschinell auswertbar, keine strukturierte Aggregation möglich.

**Better Approach:**
```python
logger.warning(
    "DHT22 read failed - returning cached value",
    extra={
        "error_count": _sensor_cache['error_count'],
        "cache_age": get_cache_age(),
        "metric": "sensor.read.failed"
    }
)
```

Mit JSON-Formatter wäre das:
```json
{
  "timestamp": "2025-12-26T10:45:23.456",
  "level": "WARNING",
  "message": "DHT22 read failed - returning cached value",
  "error_count": 3,
  "cache_age": 15.2,
  "metric": "sensor.read.failed"
}
```

---

### 1.4 Correlation IDs

**Status:** ❌ **NICHT VORHANDEN**

**Problem:** DataLogger hat 3 Threads:
- `DataLogger-Sensors` (120s interval)
- `DataLogger-Lamps` (120s interval)
- `DataLogger-Plugs` (60s interval)

Bei concurrent errors **unmöglich** zu sagen, welcher Thread welchen Log erzeugte.

**Solution:** Thread-Local Request ID

```python
# In threading start:
import threading
request_id = threading.current_thread().name
logger.info("Sensor read started", extra={"request_id": request_id})
```

---

## 2. Logging-Lücken (KRITISCH)

### 2.1 Sensor Read Cycle

**Current Logging:**

| Event | File | Line | Level | Status |
|-------|------|------|-------|--------|
| Sensor read **attempt** | `sensor_cache.py` | 161 | DEBUG | ❌ Invisible at INFO |
| Sensor read **success** | - | - | - | ❌ MISSING |
| Sensor read **failure** (3x) | `sensor_cache.py` | 206 | WARNING | ✅ OK |
| Sensor read **duration** | - | - | - | ❌ **CRITICAL MISSING** |

**KRITISCH FEHLEND:**
```python
# sensor_cache.py:146 - ADD THIS:
start_time = time.perf_counter()
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Sensor read SUCCESS in {duration_ms:.1f}ms (attempt {attempt+1})")
        # ⬆️ THIS WOULD REVEAL IF SENSOR IS SLOWING DOWN!
```

**Location:** `grow_pi/utils/sensor_cache.py:146-162`

---

### 2.2 Database Write Latency

**Current Logging:**

| Event | File | Line | Level | Status |
|-------|------|------|-------|--------|
| Sensor insert | `database/logger.py` | 233 | DEBUG | ❌ Invisible |
| Lamp insert | `database/logger.py` | 271 | DEBUG | ❌ Invisible |
| DB write **duration** | - | - | - | ❌ **CRITICAL MISSING** |

**KRITISCH FEHLEND:**
```python
# database/logger.py:226 - ADD THIS:
if temp is not None:
    start_time = time.perf_counter()
    reading = SensorReading(...)
    self.db.insert_sensor_reading(reading)
    duration_ms = (time.perf_counter() - start_time) * 1000

    if duration_ms > 100:  # 🚨 WARN if DB write takes > 100ms
        logger.warning(f"SLOW DB INSERT: {duration_ms:.1f}ms for sensor reading")
    else:
        logger.debug(f"Logged temperature: {temp}°C in {duration_ms:.1f}ms")
```

**Location:** `grow_pi/database/logger.py:226-246`

---

### 2.3 Main Loop Health

**Current Logging:**

| Event | File | Line | Level | Status |
|-------|------|------|-------|--------|
| Loop heartbeat | `main.py` | 346 | INFO | ✅ OK (every 5min) |
| Loop iteration **lag** | - | - | - | ❌ **MISSING** |
| Expected vs actual sleep | - | - | - | ❌ **MISSING** |

**KRITISCH FEHLEND:**
```python
# main.py:316 - ADD THIS:
while self.running:
    loop_start = time.time()
    time.sleep(5)  # Expected: 5s
    actual_sleep = time.time() - loop_start

    if actual_sleep > 6:  # 🚨 WARN if sleep overran by >1s
        logger.warning(f"LOOP LAG: Expected 5s sleep, took {actual_sleep:.1f}s")
```

**Location:** `grow_pi/main.py:316-337`

---

### 2.4 DHT22 Sensor Initialization

**Current Logging:**

| Event | File | Line | Level | Status |
|-------|------|------|-------|--------|
| Sensor init | `web/api.py` | 55 | WARNING | ⚠️ Only on import fail |
| Sensor reinit | `sensor_cache.py` | 98 | WARNING | ✅ OK (v6.22.4) |
| Init **duration** | - | - | - | ❌ **MISSING** |

**FEHLEND:**
```python
# web/api.py - ADD THIS when initializing sensor:
if DHT_AVAILABLE:
    start = time.time()
    dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
    duration = time.time() - start
    logger.info(f"DHT22 initialized in {duration:.2f}s")
```

---

### 2.5 Silent Failures (GEFÄHRLICH)

**Location:** `grow_pi/database/logger.py:172-177`

```python
try:
    self._log_sensors()
except Exception as e:
    logger.error(f"Sensor logging error: {e}")
    self.log_event('sensor_error', 'error', str(e))
    # ❌ NO TRACEBACK! We lose stack info!
```

**FIX:**
```python
except Exception as e:
    logger.error(f"Sensor logging error: {e}", exc_info=True)  # ✅ Adds traceback
    self.log_event('sensor_error', 'error', str(e),
                   {'traceback': traceback.format_exc()})
```

---

## 3. Minimaler Log-Standard (EMPFOHLEN)

### 3.1 PFLICHT-Events

Folgende Events **MÜSSEN IMMER geloggt werden** (INFO-Level):

| Event | Format | Location |
|-------|--------|----------|
| **Service Start** | `"DataLogger service started"` | `database/logger.py:112` ✅ |
| **Sensor Read Start** | `"DHT22 read started"` | `sensor_cache.py:146` ❌ |
| **Sensor Read Success** | `"DHT22 read OK in {ms}ms"` | `sensor_cache.py:156` ❌ |
| **DB Write Start** | `"Writing sensor data"` | `database/logger.py:226` ❌ |
| **DB Write Complete** | `"Sensor data written in {ms}ms"` | `database/logger.py:232` ❌ |
| **Service Stop** | `"DataLogger service stopped"` | `database/logger.py:155` ✅ |
| **Heartbeat** | `"Heartbeat [HH:MM] Mode=auto"` | `main.py:346` ✅ |

### 3.2 Kontext-Daten (IMMER mitloggen)

```python
logger.info("Sensor read started", extra={
    "thread": threading.current_thread().name,
    "cache_age": get_cache_age(),
    "error_count": _sensor_cache['error_count']
})
```

### 3.3 Log-Rotation

**Status:** ❌ **NICHT KONFIGURIERT**

**Problem:** `/var/log/grow-pi/service.log` wächst unbegrenzt → Disk full!

**Solution:** RotatingFileHandler

```python
# main.py - ADD THIS:
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    '/var/log/grow-pi/service.log',
    maxBytes=10*1024*1024,  # 10 MB
    backupCount=5           # Keep 5 old logs
)
handler.setFormatter(logging.Formatter(
    "%(asctime)s.%(msecs)03d [%(threadName)s] %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
))
logging.root.addHandler(handler)
```

---

## 4. Health Metrics (DEFINIERT)

### 4.1 Primäre Metriken (MÜSSEN implementiert werden)

| Metric | Type | Location | Sampling | Threshold |
|--------|------|----------|----------|-----------|
| `sensor.read.duration_ms` | Gauge | `sensor_cache.py:146` | Every read | >500ms WARN |
| `sensor.read.success_count` | Counter | `sensor_cache.py:156` | Every read | - |
| `sensor.read.failure_count` | Counter | `sensor_cache.py:164` | Every read | - |
| `sensor.cache.age_seconds` | Gauge | `sensor_cache.py:114` | On read | >60s WARN |
| `db.write.duration_ms` | Gauge | `database/logger.py:232` | Every write | >100ms WARN |
| `db.connection.open_count` | Gauge | `database/db.py` | On connect | >10 CRIT |
| `loop.iteration.duration_ms` | Gauge | `main.py:316` | Every loop | >6000ms WARN |
| `loop.lag_ms` | Gauge | `main.py:316` | Every loop | >1000ms WARN |

### 4.2 Sekundäre Metriken (NICE-TO-HAVE)

| Metric | Type | Location | Sampling |
|--------|------|----------|----------|
| `pwm.update.duration_ms` | Gauge | `pwm_controller.py:set_intensity` | On change |
| `api.request.duration_ms` | Gauge | `web/api.py` | Per request |
| `system.cpu_temp` | Gauge | `status_bp.py:123` ✅ | 30s cache |
| `system.memory_percent` | Gauge | `status_bp.py:125` ✅ | 30s cache |

### 4.3 Metrics Storage

**Option 1:** In SQLite `system_events` table (CURRENT)

```sql
INSERT INTO system_events (event_type, severity, message, details)
VALUES ('metric', 'info', 'sensor.read.duration_ms', '{"value": 45.2}')
```

**Option 2:** Separate `metrics` table (BETTER)

```sql
CREATE TABLE metrics (
    id TEXT PRIMARY KEY,
    metric_name TEXT NOT NULL,
    value REAL NOT NULL,
    unit TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_metrics_name_time ON metrics(metric_name, created_at DESC);
```

**Option 3:** In-Memory + Periodic Flush (BEST PERFORMANCE)

```python
# Keep last 1000 metrics in memory, flush to DB every 60s
_metrics_buffer = deque(maxlen=1000)
```

---

## 5. Incident Snapshot (DEFINIERT)

### 5.1 Freeze Detection Trigger

**WANN loggen wir einen Incident Snapshot?**

1. **Sensor Read Failure** ≥ 20x consecutive (`sensor_cache.py:186`)
2. **Loop Lag** > 30s (`main.py:316`)
3. **DB Write** > 5s (`database/logger.py`)
4. **Manual Trigger** via API endpoint `/api/debug/snapshot`

### 5.2 Snapshot Inhalt

```python
def create_incident_snapshot() -> Dict:
    """
    Create diagnostic snapshot on freeze detection.

    Returns:
        Dict with comprehensive system state
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "trigger": "sensor_freeze_detected",

        # Thread State
        "threads": [
            {
                "name": t.name,
                "alive": t.is_alive(),
                "daemon": t.daemon,
                "ident": t.ident
            }
            for t in threading.enumerate()
        ],

        # Sensor State
        "sensor": {
            "cache_age": get_cache_age(),
            "error_count": _sensor_cache['error_count'],
            "last_value": (_sensor_cache['temp'], _sensor_cache['humidity']),
            "last_timestamp": _sensor_cache['timestamp']
        },

        # Database State
        "database": {
            "file_size_mb": os.path.getsize(DB_PATH) / 1024 / 1024,
            "open_connections": len(threading.enumerate()),  # Approx
            "pending_writes": len(data_logger._queue) if hasattr(data_logger, '_queue') else 0
        },

        # System Resources
        "system": {
            "cpu_temp": get_cpu_temperature(),
            "cpu_load": psutil.cpu_percent(interval=0.1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "uptime_seconds": int(time.time() - psutil.boot_time())
        },

        # Open File Handles
        "file_handles": {
            "count": len(psutil.Process().open_files()),
            "files": [f.path for f in psutil.Process().open_files()[:10]]  # First 10
        },

        # PWM State
        "pwm": {
            "connected": pwm_controller.pi.connected if pwm_controller.pi else False,
            "channels": pwm_controller.get_current_state()
        },

        # Last 10 Log Lines
        "recent_logs": get_recent_logs(10)
    }
```

**Location:** Create new file `grow_pi/utils/diagnostics.py`

### 5.3 Thread Dumps

**Python hat keinen nativen Thread-Dump wie Java!**

**Workaround:** `traceback` module

```python
import sys
import traceback

def dump_all_threads():
    """Print stack trace of all running threads."""
    for thread_id, frame in sys._current_frames().items():
        logger.critical(f"Thread {thread_id} stack:")
        logger.critical("".join(traceback.format_stack(frame)))
```

**Location:** Call in `sensor_cache.py:187` when freeze detected

### 5.4 Snapshot Storage

**Option 1:** Write to separate JSON file
```python
snapshot_path = f"/var/log/grow-pi/incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(snapshot_path, 'w') as f:
    json.dump(snapshot, f, indent=2)
```

**Option 2:** Store in `system_events` table
```python
self.log_event(
    'incident_snapshot',
    'critical',
    'Freeze detected - full diagnostic snapshot',
    snapshot
)
```

---

## 6. Implementierungsvorschlag (PRIORITÄT)

### Phase 1: Critical Metrics (SOFORT)

**Effort:** 2-3 Stunden
**Files:** 3
**Impact:** Hoch

1. **Add Sensor Read Duration** (`sensor_cache.py`)
   ```python
   start = time.perf_counter()
   temp = _dht_sensor.temperature
   duration_ms = (time.perf_counter() - start) * 1000
   logger.info(f"Sensor read: {duration_ms:.1f}ms")
   ```

2. **Add DB Write Duration** (`database/logger.py`)
   ```python
   start = time.perf_counter()
   self.db.insert_sensor_reading(reading)
   duration_ms = (time.perf_counter() - start) * 1000
   if duration_ms > 100:
       logger.warning(f"SLOW DB: {duration_ms:.1f}ms")
   ```

3. **Add Loop Lag Detection** (`main.py`)
   ```python
   loop_start = time.time()
   time.sleep(5)
   lag = time.time() - loop_start - 5
   if lag > 1.0:
       logger.warning(f"LOOP LAG: {lag:.1f}s")
   ```

### Phase 2: Incident Snapshots (WICHTIG)

**Effort:** 4-5 Stunden
**Files:** 2 (new `diagnostics.py` + `sensor_cache.py`)
**Impact:** Mittel-Hoch

1. Create `grow_pi/utils/diagnostics.py`
2. Implement `create_incident_snapshot()`
3. Call on freeze detection (sensor_cache.py:187)
4. Store in `/var/log/grow-pi/incidents/`

### Phase 3: Structured Logging (OPTIONAL)

**Effort:** 6-8 Stunden
**Files:** 30+
**Impact:** Mittel (langfristig)

1. Add `pythonjsonlogger` dependency
2. Configure JSON formatter
3. Migrate critical paths to structured logging
4. Add Correlation IDs via `threading.local()`

---

## 7. Beispiel: Logging BEFORE/AFTER

### BEFORE (Current)

```
2025-12-26 10:45:23 - grow_pi.utils.sensor_cache - WARNING - DHT22 read failed (error #3) - returning cached value
2025-12-26 10:47:15 - grow_pi.database.logger - DEBUG - Logged temperature: 22.5°C
```

**Problem:**
- Keine Duration → wissen nicht, ob langsam
- Keine Thread-Info → welcher Thread?
- DEBUG unsichtbar bei INFO-Level

### AFTER (Recommended)

```
2025-12-26 10:45:23.456 [DataLogger-Sensors] grow_pi.utils.sensor_cache - INFO - Sensor read started (cache_age=15.2s, error_count=2)
2025-12-26 10:45:23.512 [DataLogger-Sensors] grow_pi.utils.sensor_cache - WARNING - Sensor read FAILED in 56ms (attempt 1/3)
2025-12-26 10:45:24.068 [DataLogger-Sensors] grow_pi.utils.sensor_cache - WARNING - Sensor read FAILED in 556ms (attempt 2/3) 🚨 SLOW!
2025-12-26 10:45:24.624 [DataLogger-Sensors] grow_pi.utils.sensor_cache - ERROR - Sensor read FAILED in 556ms (attempt 3/3) - returning stale cache
2025-12-26 10:47:15.123 [DataLogger-Sensors] grow_pi.database.logger - INFO - DB write completed in 12ms (temperature=22.5°C)
```

**Benefits:**
- ✅ Millisekunden-Timestamps
- ✅ Thread-Name sichtbar
- ✅ Duration bei jedem Read
- ✅ Alarm bei >500ms
- ✅ INFO-Level für kritische Events

---

## 8. Zusammenfassung & Empfehlungen

### ✅ Was gut läuft

1. **System Events Table** existiert und wird genutzt
2. **Health Metrics** für System (CPU/RAM/Disk) vorhanden (v6.22+)
3. **Sensor Reinit** bei Freeze implementiert (v6.22.4)
4. **Heartbeat** alle 5min in Main Loop
5. **Exception Handling** generell vorhanden (try/except blocks)

### ❌ Was KRITISCH fehlt

1. **Sensor Read Duration** – wir fliegen blind!
2. **DB Write Latency** – könnte der Bottleneck sein
3. **Loop Lag Metrics** – Main-Loop-Health unklar
4. **Millisekunden-Timestamps** – Performance-Debugging unmöglich
5. **Incident Snapshots** – kein Freeze-Postmortem möglich

### 🎯 TOP 3 Maßnahmen (Quick Wins)

1. **[PRIO 1]** Add `time.perf_counter()` zu Sensor Reads → zeigt ob DHT22 langsam wird
2. **[PRIO 2]** Add DB Write Duration Logging → zeigt DB-Lock-Probleme
3. **[PRIO 3]** Millisekunden-Timestamps in Log-Format → bessere Trace-Analyse

### 📊 Erwarteter Nutzen

Nach Implementierung Phase 1+2:
- **Freeze-Ursache** identifizierbar in <5 Minuten (statt Stunden)
- **Performance-Regression** sichtbar bevor es crasht
- **Proaktive Alerts** möglich (z.B. "Sensor-Read >500ms")
- **Remote Debugging** ohne SSH via Log-Aggregation

---

## Anhang A: Dateien mit Logging

**Vollständige Liste:**

| File | Log Statements | Priority |
|------|----------------|----------|
| `grow_pi/utils/sensor_cache.py` | 10 | **CRITICAL** |
| `grow_pi/database/logger.py` | 18 | **HIGH** |
| `grow_pi/main.py` | 17 | **HIGH** |
| `grow_pi/lamps/pwm_controller.py` | 8 | MEDIUM |
| `grow_pi/database/db.py` | 12 | MEDIUM |
| `grow_pi/web/api.py` | 63 | LOW (API errors) |
| `grow_pi/web/blueprints/*.py` | ~150 | LOW (HTTP access) |

---

## Anhang B: Nächste Schritte

1. **User-Entscheidung:** Phase 1 (Metrics) implementieren? → 2-3h Arbeit
2. **Agent-Handoff:** Falls JA → Agent F (Builder) erstellt Code
3. **Validierung:** Agent G (Validator) testet Metriken auf Pi
4. **Monitoring:** Nach 24h Production-Logs analysieren

---

**Report erstellt von:** Agent E (Observability Specialist)
**Nächster Agent:** User-Entscheidung → Agent F (Implementation) ODER Phase 2 (Snapshots)
