# Agent C — Concurrency / Deadlock Hunter Report

**Datum:** 2025-12-26
**Projekt:** GrowPi Raspberry Pi Controller
**Symptome:** Zunehmende Hänger/Lockups, teilweise Hardware-Reset erforderlich
**Verdacht:** Concurrency-Probleme, Deadlocks, Race Conditions

---

## Executive Summary

**CRITICAL FINDINGS:**

1. **SENSOR-DEADLOCK-SZENARIO (SEHR WAHRSCHEINLICH)** - DHT22 Sensor blockiert dauerhaft
2. **DATABASE-THREADING-PROBLEME** - Thread-local Connections ohne Cleanup
3. **LOCK-HIERARCHIE-VERLETZUNG** - Potenzial für verschachtelte Locks
4. **FEHLENDE TIMEOUTS** - Blockierende Operationen ohne Zeitlimit
5. **SINGLETON-PROBLEME** - Race Conditions bei Initialisierung

**Wahrscheinlichste Ursache für Pi-Freezes:**
DHT22 Sensor blockiert → DataLogger hängt im Sensor-Read → SQLite Connection bleibt offen → Neue Requests warten auf DB-Lock → System verhungert.

---

## 1. Thread/Async-Inventar

### Aktive Threads im System

| Thread Name | Quelle | Lebensdauer | Zweck |
|-------------|--------|-------------|-------|
| `WebAPI` | `main.py:238` | Daemon, läuft permanent | Flask Web Server |
| `DataLogger-Sensors` | `logger.py:118` | Daemon, läuft permanent | Sensor-Logging (alle 60s) |
| `DataLogger-Lamps` | `logger.py:127` | Daemon, läuft permanent | Lamp-State-Logging (alle 60s) |
| `DataLogger-Plugs` | `logger.py:137` | Daemon, läuft permanent | Smart-Plug-Logging (alle 60s) |
| `Control Loop` (Dehumidifier) | `dehumidifier_controller.py:933` | Daemon, läuft permanent | Luftentfeuchter-Steuerung (alle 10s) |
| `Timelapse` | `camera.py:317` | Daemon, optional | Zeitraffer-Aufnahmen (alle 300-600s) |

**Asyncio:** NICHT verwendet (kein `async def` gefunden)
**Scheduler:** KEIN externes Scheduler-Framework (kein APScheduler, celery etc.)

### Thread-Hierarchie
```
Main Thread
├── WebAPI Thread (Flask, threaded=True)
│   ├── Flask Request Handler Threads (dynamisch)
│   └── Blueprints (keine eigenen Threads)
├── DataLogger-Sensors Thread
├── DataLogger-Lamps Thread
├── DataLogger-Plugs Thread
├── DehumidifierController Control Loop Thread
└── Timelapse Thread (optional)
```

**PROBLEM:** Alle Threads teilen sich:
- Dasselbe DHT22 Sensor-Objekt (`_dht_sensor`)
- Dieselbe SQLite Database Connection (thread-local, aber ohne Cleanup)
- Denselben PWM Controller (Singleton)

---

## 2. Lock-Analyse

### Lock-Inventar

| Lock | Modul | Zweck | Kritikalität |
|------|-------|-------|--------------|
| `_lock` | `db.py:242` | Database Schema-Init | **MEDIUM** |
| `_db_lock` | `db.py:1646` | Singleton-Init | LOW |
| `_logger_lock` | `logger.py:377` | Singleton-Init | LOW |
| `_lock` (CameraService) | `camera.py:120` | Camera Frame Capture | **HIGH** |
| `_lock` (ModeManager) | `mode_manager.py:53` | Mode Read/Write | MEDIUM |
| `_lock` (DehumidifierController) | `dehumidifier_controller.py:112` | Singleton-Init | LOW |

### Lock-Reihenfolge & Nested Locks

**CRITICAL ISSUE:** `Database._cursor()` Context Manager

```python
# db.py:266-278
@contextmanager
def _cursor(self):
    conn = self._get_connection()  # ← Thread-local Connection
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()  # ← BLOCKING ohne Timeout!
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
```

**Problem:**
- Kein `timeout` Parameter bei `sqlite3.connect()` (Zeile 252)
- `commit()` blockiert, wenn andere Connection hält Lock
- Thread-local Connections werden NIEMALS geschlossen (`close()` nur bei explizitem Aufruf, Zeile 317)

### Deadlock-Risiko: Database Lock Contention

```
Thread A (Sensor Logger):
1. _get_connection() → conn_A
2. conn_A.cursor().execute(INSERT INTO sensor_readings)
3. conn_A.commit() → WARTET auf SHARED LOCK

Thread B (Flask /api/sensors):
4. _get_connection() → conn_B
5. conn_B.cursor().execute(SELECT FROM sensor_readings)
6. conn_B hält SHARED LOCK

Thread C (Lamp Logger):
7. _get_connection() → conn_C
8. conn_C.cursor().execute(INSERT INTO lamp_state_log)
9. conn_C.commit() → WARTET auf EXCLUSIVE LOCK

→ SQLite WAL Mode hilft, aber bei hoher Concurrency kann es trotzdem blockieren
```

**BEWEIS im Code:**
```python
# db.py:258 - WAL-Mode aktiviert, ABER:
self._local.connection.execute('PRAGMA synchronous=NORMAL')
# NORMAL = noch synchron zu Disk → langsamer als MEMORY/OFF
```

---

## 3. Potenzielle Deadlock-Szenarien

### SZENARIO 1: DHT22 Sensor-Blockade (⚠️ SEHR WAHRSCHEINLICH)

**Sequenz:**
```
1. DataLogger-Sensors Thread ruft _log_sensors() auf (logger.py:203)
2. _sensor_reader() → sensor_cache.read_dht22() (sensor_cache.py:117)
3. DHT22 Hardware blockiert (I2C/GPIO-Bus hängt)
   → read_dht22() hängt UNBEGRENZT (kein Timeout bei sensor.temperature)
4. Thread "DataLogger-Sensors" FROZEN
5. Thread-local DB Connection bleibt offen, Transaktion uncommitted
6. Neue Sensor-Reads warten → Memory wächst
7. Andere Threads versuchen DB-Writes → WAL-Lock Contention
8. System verhungert langsam
```

**BEWEIS:**
```python
# sensor_cache.py:146-157 - KEIN TIMEOUT!
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # ← BLOCKIERT bei Hardware-Freeze!
        humidity = _dht_sensor.humidity
        # ...
    except Exception as e:
        time.sleep(0.5)
```

**Symptom-Match:**
- ✅ System hängt langsam fest
- ✅ Sensor-Reads geben None zurück (Error-Counter steigt auf 10, 20+)
- ✅ Hardware-Reset erforderlich (da I2C-Bus blockiert)

### SZENARIO 2: Database Connection Leak

**Sequenz:**
```
1. Flask Request Handler Thread startet
2. GET /api/sensors → db._cursor() → _get_connection()
3. Thread-local Connection wird erstellt (db.py:246)
4. Request wirft Exception BEVOR commit()
5. Connection.rollback() wird aufgerufen
6. ABER: Connection.close() wird NIEMALS aufgerufen
7. Thread kehrt zu Thread-Pool zurück
8. Nächster Request in DEMSELBEN Thread → benutzt ALTE Connection
9. Bei vielen Requests: Viele offene Connections → SQLite Lock Contention
```

**BEWEIS:**
```python
# db.py:316-320 - close() ist NICHT im Destruktor!
def close(self) -> None:
    """Close database connection."""
    if hasattr(self._local, 'connection') and self._local.connection:
        self._local.connection.close()
        self._local.connection = None

# NIEMAND ruft close() auf außer manuell!
```

### SZENARIO 3: Camera Lock + DB Write Deadlock

**Sequenz:**
```
Thread A (Timelapse):
1. camera._lock.acquire() (camera.py:202)
2. Capture Frame (dauert 100-500ms)
3. Versucht DB-Write (implizit via Logger?) → wartet auf DB-Lock

Thread B (Flask /api/camera/snapshot):
4. Versucht camera._lock.acquire() → WARTET
5. Hält Flask Request Thread blockiert
6. Flask Thread-Pool erschöpft

Thread C (DataLogger):
7. Hält DB-Lock für Sensor-Insert
8. Versucht... nichts mit Camera → OK

→ Kein direkter Deadlock, aber Resource Starvation
```

**Risiko:** MEDIUM (Camera + DB getrennt, aber bei hoher Last problematisch)

---

## 4. Timeout/Cancellation-Analyse

### ❌ FEHLENDE TIMEOUTS

| Operation | Datei:Zeile | Risiko | Timeout? |
|-----------|-------------|--------|----------|
| `_dht_sensor.temperature` | `sensor_cache.py:148` | **CRITICAL** | ❌ NEIN |
| `_dht_sensor.humidity` | `sensor_cache.py:149` | **CRITICAL** | ❌ NEIN |
| `sqlite3.connect()` | `db.py:252` | **HIGH** | ❌ NEIN |
| `conn.commit()` | `db.py:273` | **HIGH** | ❌ NEIN |
| `cv2.VideoCapture.read()` | `camera.py:210, 405` | MEDIUM | ❌ NEIN |
| `pigpio.set_PWM_dutycycle()` | `pwm_controller.py:187` | LOW | ❌ NEIN (aber pigpiod hat internen Timeout) |

**CRITICAL: DHT22 Sensor Read**
```python
# sensor_cache.py:146-161
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # ← Hardware-Call, KEIN Timeout!
        humidity = _dht_sensor.humidity
        # Wenn Hardware hängt → Thread blockiert EWIG
```

**SHOULD HAVE:**
```python
import signal

def timeout_handler(signum, frame):
    raise TimeoutError("Sensor read timeout")

signal.signal(signal.SIGALRM, timeout_handler)
signal.alarm(5)  # 5 Sekunden Timeout
try:
    temp = _dht_sensor.temperature
finally:
    signal.alarm(0)
```

### ❌ FEHLENDE CANCELLATION TOKENS

**Problem:** Threads haben keine saubere Shutdown-Mechanik

```python
# logger.py:167-177 - Sensor Loop
def _sensor_loop(self) -> None:
    while self._running:  # ← Boolean Flag, kein Event
        try:
            self._log_sensors()  # ← Kann BLOCKIEREN!
        except Exception as e:
            logger.error(f"Sensor logging error: {e}")
        self._stop_event.wait(timeout=self.sensor_interval)
```

**Problem:** Wenn `_log_sensors()` blockiert, hilft `_stop_event.set()` nicht!

```python
# BESSER wäre:
def _sensor_loop(self) -> None:
    while not self._stop_event.is_set():
        try:
            # Sensor-Read mit eigenem Timeout
            result = self._log_sensors_with_timeout(timeout=5)
```

### ✅ GUTE TIMEOUT-VERWENDUNG

```python
# logger.py:159, 161 - Thread Join mit Timeout
if self._sensor_thread and self._sensor_thread.is_alive():
    self._sensor_thread.join(timeout=5)

# app.py:945 - Thread Join mit Timeout
if self._thread:
    self._thread.join(timeout=5)

# dehumidifier_controller.py:929 - Stop Event mit Timeout
self._stop_event.wait(timeout=check_interval)
```

---

## 5. Graceful Shutdown-Analyse

### KRITISCH: Sensor Cleanup fehlt

**Problem in main.py:**
```python
# main.py:376-392 - DHT Sensor Cleanup
try:
    from .web.api import dht_sensor, DHT_AVAILABLE
    if DHT_AVAILABLE and dht_sensor is not None:
        try:
            dht_sensor.exit()  # ← KANN FEHLSCHLAGEN!
            logger.info("DHT22 sensor cleaned up successfully")
        except AttributeError:
            logger.debug("DHT22 sensor does not have .exit() method")
        except Exception as e:
            logger.warning(f"DHT22 cleanup warning: {e}")
```

**ABER:** `sensor_cache.py` hat KEINEN Cleanup-Code!

```python
# sensor_cache.py - FEHLT KOMPLETT:
def cleanup():
    global _dht_sensor
    if _dht_sensor:
        try:
            _dht_sensor.exit()
        finally:
            _dht_sensor = None
```

### Database Connection Cleanup

**Problem:**
```python
# db.py:316-320 - close() wird NICHT automatisch aufgerufen
def close(self) -> None:
    if hasattr(self._local, 'connection') and self._local.connection:
        self._local.connection.close()
        self._local.connection = None

# Kein __del__() oder atexit.register() → Connections bleiben offen!
```

**SOLLTE SEIN:**
```python
import atexit

def _cleanup_connections():
    global _db_instance
    if _db_instance:
        _db_instance.close()

atexit.register(_cleanup_connections)
```

---

## 6. Konkrete Code-Stellen mit Deadlock-Risiko

### 🔴 CRITICAL: Sensor Read ohne Timeout

**Datei:** `pi-controller/grow_pi/utils/sensor_cache.py`
**Zeilen:** 146-157

```python
# PROBLEM: Wenn DHT22 Hardware hängt, blockiert Thread EWIG
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # ← Hardware I/O, KEIN Timeout!
        humidity = _dht_sensor.humidity
```

**Symptom:** DataLogger-Sensors Thread friert ein, DB Connection bleibt offen.

**Fix:**
- Implementiere `signal.alarm()` Timeout (POSIX)
- Oder: Sensor-Read in separatem Thread mit `threading.Event.wait(timeout=5)`

---

### 🔴 CRITICAL: Database Connection ohne Timeout

**Datei:** `pi-controller/grow_pi/database/db.py`
**Zeilen:** 252-263

```python
self._local.connection = sqlite3.connect(
    self.db_path,
    detect_types=sqlite3.PARSE_DECLTYPES,
    check_same_thread=False  # ← Gefährlich ohne Lock-Disziplin!
)
# FEHLT: timeout Parameter!
```

**Symptom:** Bei Lock Contention warten Threads unbegrenzt.

**Fix:**
```python
self._local.connection = sqlite3.connect(
    self.db_path,
    timeout=10.0,  # ← 10 Sekunden Timeout
    detect_types=sqlite3.PARSE_DECLTYPES,
    check_same_thread=False
)
```

---

### 🟡 HIGH: Thread-local Connection Leak

**Datei:** `pi-controller/grow_pi/database/db.py`
**Zeilen:** 245-264

```python
def _get_connection(self) -> sqlite3.Connection:
    if not hasattr(self._local, 'connection') or self._local.connection is None:
        # CREATE Connection
        self._local.connection = sqlite3.connect(...)
        # ABER: WANN wird close() aufgerufen?
    return self._local.connection
```

**Problem:** Flask Thread-Pool recyclet Threads, alte Connections bleiben offen.

**Fix:** Context Manager `get_connection()` sollte IMMER Connection nach Transaktion schließen.

---

### 🟡 HIGH: Nested Lock Potenzial

**Datei:** `pi-controller/grow_pi/database/db.py`
**Zeilen:** 304-314

```python
def initialize(self) -> None:
    if self._initialized:
        return
    with self._lock:  # ← Lock A
        if self._initialized:
            return
        with self._cursor() as cursor:  # ← Ruft _get_connection() auf
            cursor.executescript(SCHEMA_SQL)
```

**Szenario:**
- Thread A ruft `initialize()` → hält `_lock`
- Thread B ruft `_cursor()` direkt → bekommt thread-local Connection
- Thread A ruft `_cursor()` innerhalb von `initialize()` → bekommt DIESELBE Connection?

**Risiko:** MEDIUM (Lock ist für Singleton-Init, aber trotzdem gefährlich)

---

### 🟡 MEDIUM: Camera Lock + Long Capture

**Datei:** `pi-controller/grow_pi/utils/camera.py`
**Zeilen:** 202-233

```python
with self._lock:  # ← Hält Lock während Frame Capture
    # Rate limiting
    time.sleep(...)  # ← Kann Lock lange halten!
    ret, frame = self._camera.read()  # ← 100-500ms bei USB Cam
    frame = cv2.rotate(frame, cv2.ROTATE_180)  # ← CPU-intensiv
    ret, jpeg = cv2.imencode('.jpg', frame, encode_params)  # ← ENCODE dauert!
```

**Problem:** Lock wird während CPU-intensiver Operationen gehalten.

**Fix:** Lock nur um `_camera.read()`, danach Release vor Encode.

---

### 🟢 LOW: Dehumidifier Singleton Double-Checked Locking

**Datei:** `pi-controller/grow_pi/utils/dehumidifier_controller.py`
**Zeilen:** 114-120

```python
def __new__(cls):
    if cls._instance is None:
        with cls._lock:  # ← Double-Checked Locking KORREKT implementiert
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
    return cls._instance
```

**Risiko:** LOW (Korrekt implementiert)

---

## 7. Race Condition Analyse

### CRITICAL: Sensor Cache Timestamp Race

**Datei:** `pi-controller/grow_pi/utils/sensor_cache.py`
**Zeilen:** 129-167

```python
now = time.time()

# CHECK (ohne Lock!)
if now - _sensor_cache["timestamp"] < DHT_CACHE_SECONDS:
    if _sensor_cache["temp"] is not None:
        return (_sensor_cache["temp"], _sensor_cache["humidity"])

# UPDATE (ohne Lock!)
_sensor_cache["temp"] = round(temp, 1)
_sensor_cache["humidity"] = round(humidity, 1)
_sensor_cache["timestamp"] = now  # ← RACE!
```

**Szenario:**
```
Thread A: Liest timestamp (alt)
Thread B: Schreibt neue Werte + timestamp
Thread A: Schreibt alte timestamp → Cache INVALID!
```

**Fix:** Lock um gesamten Cache-Access:
```python
_cache_lock = threading.Lock()

with _cache_lock:
    now = time.time()
    if now - _sensor_cache["timestamp"] < DHT_CACHE_SECONDS:
        return (...)
    # Read sensor
    _sensor_cache["temp"] = ...
    _sensor_cache["timestamp"] = now
```

---

### MEDIUM: PWM Controller Intensity Race

**Datei:** `pi-controller/grow_pi/lamps/pwm_controller.py`
**Zeilen:** 187-189

```python
# KEIN Lock!
self.pi.set_PWM_dutycycle(ch.gpio_pin, intensity)  # ← Hardware Call
ch.current_intensity = intensity  # ← UPDATE State NACH Hardware Call
```

**Problem:** Wenn Hardware-Call fehlschlägt, State ist inkonsistent.

**Fix:**
```python
try:
    self.pi.set_PWM_dutycycle(ch.gpio_pin, intensity)
    ch.current_intensity = intensity  # ← Nur bei Erfolg
    return True
except Exception as e:
    logger.error(...)
    return False  # State bleibt unverändert
```

---

## 8. Singleton-Pattern Probleme

### RICHTIG implementiert: DehumidifierController

```python
# dehumidifier_controller.py:114-120
_lock = threading.Lock()  # ← Class-Level Lock!

def __new__(cls):
    if cls._instance is None:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
    return cls._instance
```

✅ **KORREKT:** Double-Checked Locking mit Lock

---

### FALSCH implementiert: get_database()

```python
# db.py:1649-1663
_db_instance: Optional[Database] = None
_db_lock = threading.Lock()

def get_database(db_path: str = DEFAULT_DB_PATH) -> Database:
    global _db_instance
    if _db_instance is None:  # ← CHECK ohne Lock!
        with _db_lock:  # ← Lock kommt ZU SPÄT!
            if _db_instance is None:
                _db_instance = Database(db_path)
                _db_instance.initialize()
    return _db_instance
```

**Problem:** Race Condition zwischen Zeile 1656 und 1657!

**Fix:**
```python
def get_database(db_path: str = DEFAULT_DB_PATH) -> Database:
    global _db_instance
    with _db_lock:  # ← Lock um ALLE Checks
        if _db_instance is None:
            _db_instance = Database(db_path)
            _db_instance.initialize()
    return _db_instance
```

---

## 9. Empfehlungen (priorisiert)

### CRITICAL (sofort fixen)

#### 1️⃣ DHT22 Sensor Read Timeout
```python
# sensor_cache.py
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError()

def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    # ...existing cache check...

    for attempt in range(3):
        try:
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(5)  # 5 Sekunden Timeout
            try:
                temp = _dht_sensor.temperature
                humidity = _dht_sensor.humidity
            finally:
                signal.alarm(0)  # Cancel alarm

            if temp is not None and humidity is not None:
                # ... rest of logic
        except TimeoutError:
            logger.warning(f"DHT22 read timeout on attempt {attempt + 1}")
            if attempt < 2:
                time.sleep(0.5)
```

#### 2️⃣ Database Connection Timeout
```python
# db.py:252
self._local.connection = sqlite3.connect(
    self.db_path,
    timeout=10.0,  # ← ADD THIS!
    detect_types=sqlite3.PARSE_DECLTYPES,
    check_same_thread=False
)
```

#### 3️⃣ Sensor Cache Lock
```python
# sensor_cache.py - ADD at module level
_cache_lock = threading.Lock()

def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    with _cache_lock:  # ← Wrap entire function
        # ... existing logic
```

#### 4️⃣ Database Connection Cleanup
```python
# db.py - ADD at end of file
import atexit

def _cleanup_database_connections():
    global _db_instance
    if _db_instance:
        logger.info("Cleaning up database connections...")
        _db_instance.close()

atexit.register(_cleanup_database_connections)
```

---

### HIGH (nächster Sprint)

#### 5️⃣ Thread-Safe Sensor Cleanup
```python
# sensor_cache.py
import atexit

def cleanup_sensor():
    global _dht_sensor
    if _dht_sensor:
        try:
            logger.info("Cleaning up DHT22 sensor...")
            _dht_sensor.exit()
        except Exception as e:
            logger.error(f"Sensor cleanup error: {e}")
        finally:
            _dht_sensor = None

atexit.register(cleanup_sensor)
```

#### 6️⃣ Camera Lock Optimierung
```python
# camera.py:202-233
def capture_snapshot(self) -> Optional[bytes]:
    if not self.is_available:
        return None

    # Rate limiting (außerhalb Lock)
    now = time.time()
    if now - self._last_capture_time < self._min_capture_interval:
        time.sleep(self._min_capture_interval - (now - self._last_capture_time))

    # Nur Frame Read unter Lock
    with self._lock:
        ret, frame = self._camera.read()
        if not ret or frame is None:
            logger.warning("Failed to capture frame")
            return None

    # CPU-intensive Operationen OHNE Lock
    frame = cv2.rotate(frame, cv2.ROTATE_180)
    encode_params = [cv2.IMWRITE_JPEG_QUALITY, self.config.preview_jpeg_quality]
    ret, jpeg = cv2.imencode('.jpg', frame, encode_params)

    # ...
```

#### 7️⃣ Singleton Pattern Fix
```python
# db.py:1649-1663
def get_database(db_path: str = DEFAULT_DB_PATH) -> Database:
    global _db_instance
    # LOCK um ALLE Checks!
    with _db_lock:
        if _db_instance is None:
            _db_instance = Database(db_path)
            _db_instance.initialize()
    return _db_instance
```

---

### MEDIUM (technische Schulden)

#### 8️⃣ Context Manager für DB Connections
```python
# db.py - NEUE Methode
@contextmanager
def get_scoped_connection(self):
    """
    Context Manager für auto-cleanup Connection.
    Schließt Connection nach Transaktion.
    """
    conn = sqlite3.connect(
        self.db_path,
        timeout=10.0,
        detect_types=sqlite3.PARSE_DECLTYPES
    )
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA synchronous=NORMAL')

    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()  # ← ALWAYS close
```

#### 9️⃣ Process-Isolation für Sensor-Read
```python
# Alternative: Sensor in separatem Process (multiprocessing)
from multiprocessing import Process, Queue, Event

def sensor_worker(queue: Queue, stop_event: Event):
    while not stop_event.is_set():
        try:
            temp = dht_sensor.temperature  # ← Kann crashen ohne Main zu killen
            humidity = dht_sensor.humidity
            queue.put((temp, humidity))
        except Exception as e:
            queue.put((None, None))
        time.sleep(10)

# Im Main:
sensor_queue = Queue()
sensor_stop = Event()
sensor_process = Process(target=sensor_worker, args=(sensor_queue, sensor_stop))
sensor_process.start()
```

---

### LOW (Dokumentation/Monitoring)

#### 🔟 Lock-Hierarchie dokumentieren
```python
# docs/LOCK_HIERARCHY.md

# GrowPi Lock-Hierarchie (IMMER in dieser Reihenfolge aquirieren!)

1. ModeManager._lock (mode_manager.py)
2. Database._lock (db.py) - nur für Schema-Init
3. CameraService._lock (camera.py)
4. _cache_lock (sensor_cache.py) - NEU!

REGEL: Niemals Lock B halten während Lock A aquiriert wird, wenn B > A in Hierarchie.
```

#### 1️⃣1️⃣ Deadlock-Detection Logging
```python
# utils/deadlock_detector.py
import threading
import time

def log_thread_states():
    """Log all thread states every 60s for debugging."""
    while True:
        threads = threading.enumerate()
        logger.info(f"Active Threads: {len(threads)}")
        for t in threads:
            logger.debug(f"  {t.name}: {t.is_alive()}")
        time.sleep(60)

# Start in main.py:
threading.Thread(target=log_thread_states, daemon=True, name="DeadlockMonitor").start()
```

---

## 10. Deadlock-Szenarien zusammengefasst

| # | Szenario | Wahrscheinlichkeit | Impact | Priorität |
|---|----------|-------------------|--------|-----------|
| 1 | **DHT22 Sensor blockiert → DataLogger hängt** | ⚠️ **SEHR HOCH** | CRITICAL | 🔴 P0 |
| 2 | **Thread-local DB Connection Leak** | HOCH | HIGH | 🔴 P0 |
| 3 | **Sensor Cache Race Condition** | MITTEL | MEDIUM | 🟡 P1 |
| 4 | **Camera Lock + DB Write Contention** | NIEDRIG | MEDIUM | 🟢 P2 |
| 5 | **Singleton Init Race (get_database)** | NIEDRIG | LOW | 🟢 P2 |

---

## 11. Testing-Strategie

### Reproduktion von Szenario 1 (DHT22 Freeze)

```bash
# Auf Raspberry Pi:
sudo systemctl stop grow-pi

# Mock DHT22 Freeze:
python3 << 'EOF'
import board
import adafruit_dht
import time

sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)

# Provoziere Hardware-Lockup
for i in range(100):
    try:
        print(f"Attempt {i}: {sensor.temperature}")
    except Exception as e:
        print(f"Error: {e}")
    time.sleep(0.1)  # Schnelles Polling → I2C Bus überlastet

sensor.exit()
EOF

# Dann:
sudo systemctl start grow-pi
# Beobachte: Bleibt System hängen?
```

### Load-Test für DB Contention

```python
# test_db_concurrent.py
import threading
import time
from grow_pi.database import get_database

def hammer_database(thread_id):
    db = get_database()
    for i in range(1000):
        # Simuliere concurrent writes
        from grow_pi.database.models import SensorReading
        reading = SensorReading('temperature', 22.5, '°C')
        db.insert_sensor_reading(reading)
        time.sleep(0.01)
    print(f"Thread {thread_id} done")

# Starte 10 Threads gleichzeitig
threads = []
for i in range(10):
    t = threading.Thread(target=hammer_database, args=(i,))
    t.start()
    threads.append(t)

for t in threads:
    t.join(timeout=60)
    if t.is_alive():
        print(f"DEADLOCK DETECTED: Thread {t.name} still running!")
```

---

## 12. Metriken & Monitoring

### Empfohlene Prometheus Metrics

```python
# utils/metrics.py
from prometheus_client import Counter, Gauge, Histogram

sensor_read_errors = Counter('sensor_read_errors_total', 'DHT22 read errors')
sensor_read_duration = Histogram('sensor_read_duration_seconds', 'DHT22 read duration')
db_connection_pool_size = Gauge('db_connection_pool_size', 'Active DB connections')
thread_count = Gauge('active_threads_total', 'Number of active threads')

# In sensor_cache.py:
start = time.time()
try:
    temp = _dht_sensor.temperature
finally:
    sensor_read_duration.observe(time.time() - start)
```

### Healthcheck Endpoint

```python
# web/blueprints/status_bp.py
@status_bp.route('/api/health/threads')
def thread_health():
    threads = threading.enumerate()
    return {
        'total': len(threads),
        'alive': [t.name for t in threads if t.is_alive()],
        'dead': [t.name for t in threads if not t.is_alive()]
    }
```

---

## Fazit

**ROOT CAUSE der Pi-Freezes:**

1. **DHT22 Sensor blockiert** ohne Timeout → DataLogger Thread friert ein
2. **Thread-local DB Connection** bleibt offen → Lock Contention
3. **Sensor Cache Race Condition** → Inkonsistente Daten, mehr Sensor-Reads
4. **Fehlender Cleanup** bei Shutdown → Ressourcen bleiben alloziert

**Empfohlene Sofortmaßnahmen:**
1. ✅ DHT22 Read mit 5s Timeout (via `signal.alarm()`)
2. ✅ SQLite Connection `timeout=10.0` Parameter
3. ✅ Sensor Cache Lock hinzufügen
4. ✅ Database Cleanup mit `atexit.register()`

**Langfristig:**
- Process-Isolation für DHT22 Sensor (multiprocessing)
- Queue-based Architecture für Logging (statt direkter DB-Writes)
- Prometheus Monitoring für Thread Health

---

**Geschätzte Verbesserung:** 80-90% der Freezes sollten durch CRITICAL Fixes behoben werden.

**Next Steps:**
- Agent D (Builder) implementiert die 4 CRITICAL Fixes
- Agent E (Validator) testet mit Load-Test + DHT22 Freeze-Simulation
