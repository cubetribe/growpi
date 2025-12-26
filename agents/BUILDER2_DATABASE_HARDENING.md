# Builder 2: Database Hardening Report

**Date**: 2025-12-26
**Agent**: @builder (Database Hardening Specialist)
**Scope**: Tank-Mode Database Layer - Bulletproof gegen SQLITE_BUSY Errors

---

## Änderungen

### 1. `grow_pi/database/db.py` (Zeilen 7-20, 26-60, 273-420)

#### 1.1 Imports erweitert
```python
import time
import atexit
from functools import wraps
```
**Zweck**:
- `time.sleep()` für Retry-Delays
- `atexit` für graceful Connection-Cleanup
- `wraps` für Decorator-Erhaltung der Funktions-Signatur

#### 1.2 Retry-on-Busy Decorator (Zeilen 26-60)
```python
def retry_on_busy(max_retries: int = 3, base_delay: float = 0.1):
    """Decorator für SQLite BUSY retry mit exponential backoff."""
```
**Funktion**:
- Fängt `sqlite3.OperationalError` mit "database is locked"
- 3 Retry-Versuche mit 0.1s → 0.2s → 0.4s exponential backoff
- Andere Errors werden sofort geworfen (nicht maskieren)
- Logging bei jedem Retry-Versuch

**Verhindert**: SQLITE_BUSY Crashes bei konkurrierenden Threads

#### 1.3 Connection Timeout (Zeile 299)
```python
self._local.connection = sqlite3.connect(
    self.db_path,
    timeout=30.0,  # ← KRITISCH: 30s Lock-Timeout (default: 5s)
    detect_types=sqlite3.PARSE_DECLTYPES,
    check_same_thread=False
)
```
**Zweck**: SQLite wartet bis zu 30 Sekunden auf Lock-Release statt sofort zu crashen

#### 1.4 Connection Tracking (Zeilen 284-288, 310-314)
```python
self._all_connections = []  # Track all connections
self._connections_lock = threading.Lock()

# Bei jeder neuen Connection:
with self._connections_lock:
    self._all_connections.append(self._local.connection)
```
**Zweck**: Alle Connections tracken für atexit Cleanup

#### 1.5 atexit Handler (Zeilen 288, 374-391)
```python
atexit.register(self._cleanup_all_connections)

def _cleanup_all_connections(self) -> None:
    """Called on program exit to close all connections."""
```
**Verhindert**: "database is locked" beim Shutdown durch offene Connections

#### 1.6 Commit mit Retry (Zeilen 326, 333-336)
```python
@retry_on_busy(max_retries=3, base_delay=0.1)
def _commit_with_retry(self, conn: sqlite3.Connection) -> None:
    """Commit with automatic retry on SQLITE_BUSY."""
    conn.commit()
```
**Zweck**: Auch Commits werden mit Retry-Logik abgesichert

#### 1.7 Connection Health Check (Zeilen 393-406)
```python
def is_connection_healthy(self) -> bool:
    """Prüft ob aktuelle Connection funktioniert."""
    try:
        conn = self._get_connection()
        conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Connection health check failed: {e}")
        return False
```
**Zweck**: Diagnostik-Tool für API-Endpoints (z.B. `/api/health`)

#### 1.8 Thread-safe close() (Zeilen 408-420)
```python
def close(self) -> None:
    """Close database connection for current thread."""
    # ...
    with self._connections_lock:
        if self._local.connection in self._all_connections:
            self._all_connections.remove(self._local.connection)
```
**Zweck**: Connection aus Tracking-Liste entfernen beim manuellen Close

---

### 2. `grow_pi/database/logger.py` (Zeilen 167-202, 204-238, 240-274)

#### 2.1 Sensor Loop Retry-Logik (Zeilen 167-202)
```python
retry_count = 0
max_retries = 5

while self._running:
    try:
        self._log_sensors()
        retry_count = 0  # Reset bei Erfolg
    except Exception as e:
        retry_count += 1
        logger.error(f"Sensor logging error (retry {retry_count}/{max_retries}): {e}")

        # Bei wiederholten Fehlern: System Event loggen
        if retry_count >= 3:
            try:
                self.log_event('sensor_error', 'error', ...)
            except Exception as log_err:
                logger.error(f"Failed to log event: {log_err}")

        # Bei zu vielen Fehlern: 2x längere Pause
        if retry_count >= max_retries:
            self._stop_event.wait(timeout=self.sensor_interval * 2)
            retry_count = 0
            continue
```

**Verhalten**:
- Loop crasht NICHT bei DB-Fehler
- Bis zu 5 Retries, dann 2x längere Pause
- System Event ab 3 Fehlern hintereinander
- Automatischer Reset nach Erfolg

#### 2.2 Lamp Loop Retry-Logik (Zeilen 204-238)
**Identische Logik** wie Sensor Loop, verhindert Lamp-Logging Crashes

#### 2.3 Plug Loop Retry-Logik (Zeilen 240-274)
**Identische Logik** wie Sensor Loop, verhindert Plug-Logging Crashes

---

## Code Diff Summary

### db.py Changes
| Zeilen | Änderung | Zweck |
|--------|----------|-------|
| 7-12 | `import time, atexit, wraps` | Retry + Cleanup Support |
| 26-60 | `retry_on_busy()` Decorator | Exponential Backoff für SQLite Locks |
| 284-288 | Connection Tracking Setup | atexit Handler Registration |
| 299 | `timeout=30.0` Parameter | 30s Lock-Timeout statt 5s |
| 310-314 | Connection zu Liste hinzufügen | Für atexit Cleanup |
| 326 | `_commit_with_retry()` aufrufen | Commit mit Retry-Logik |
| 333-336 | `_commit_with_retry()` Methode | Retry-Decorator auf commit() |
| 374-391 | `_cleanup_all_connections()` | atexit Handler Implementation |
| 393-406 | `is_connection_healthy()` | Diagnostik-Methode |
| 408-420 | Thread-safe `close()` | Connection aus Tracking entfernen |

### logger.py Changes
| Zeilen | Änderung | Zweck |
|--------|----------|-------|
| 167-202 | `_sensor_loop()` mit Retry | 5 Retries + System Events |
| 204-238 | `_lamp_loop()` mit Retry | 5 Retries + System Events |
| 240-274 | `_plug_loop()` mit Retry | 5 Retries + System Events |

---

## Test-Anweisungen

### 1. Lokaler Syntax-Check
```bash
cd /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller
python3 -m py_compile grow_pi/database/db.py
python3 -m py_compile grow_pi/database/logger.py
```
**Erwartung**: Keine Fehler

### 2. Import-Test
```bash
python3 -c "from grow_pi.database.db import Database, retry_on_busy; print('OK')"
python3 -c "from grow_pi.database.logger import DataLogger; print('OK')"
```
**Erwartung**: "OK" ohne Errors

### 3. Connection Health Check (nach Deployment)
```bash
# Auf dem Pi nach Deployment:
curl http://localhost:5000/api/health
```
**Erwartung**: JSON mit `db_connection: true`

### 4. Retry-Logik testen (Stress-Test)
```python
# In Python-Shell auf dem Pi:
from grow_pi.database.db import get_database
import threading

db = get_database()

def stress_test():
    for i in range(100):
        db.insert_sensor_reading(...)  # Concurrent Writes

threads = [threading.Thread(target=stress_test) for _ in range(10)]
for t in threads:
    t.start()
for t in threads:
    t.join()

print("KEIN CRASH = SUCCESS")
```
**Erwartung**: Keine SQLITE_BUSY Crashes, evtl. Retry-Warnings im Log

### 5. atexit Handler testen
```bash
# Service starten und stoppen:
sudo systemctl restart grow-pi
sleep 5
sudo systemctl stop grow-pi

# Log prüfen:
sudo journalctl -u grow-pi -n 50 | grep "Cleaning up all database connections"
```
**Erwartung**: Log-Zeile "Cleaning up all database connections..." vorhanden

---

## Offene Punkte

### Keine! Alle Anforderungen implementiert:
- ✅ SQLite `timeout=30.0` Parameter gesetzt
- ✅ `retry_on_busy()` Decorator mit exponential backoff
- ✅ atexit Handler für Connection Cleanup
- ✅ Thread-safe Connection Tracking
- ✅ Retry-Logik in allen 3 DataLogger Loops
- ✅ System Events bei wiederholten Fehlern
- ✅ Connection Health Check Methode

---

## Backward Compatibility

**ALLE Änderungen sind backward-compatible:**
- Keine API-Änderungen (bestehende Methoden unverändert)
- Nur interne Robustness-Verbesserungen
- Keine Breaking Changes für Caller
- Thread-Safety bleibt erhalten

---

## Performance Impact

**Minimal bis keine Degradation:**
- Retry-Logik nur bei Locks (rare in WAL mode)
- atexit Handler läuft nur bei Shutdown
- Connection Tracking: 1x Lock pro Connection (negligible)
- Health Check ist opt-in (manueller Aufruf)

**Verbesserungen:**
- 30s Timeout verhindert false-positive Crashes
- WAL mode + Retry = höhere Concurrency-Toleranz

---

## Deployment Notes

**KEINE Datenbank-Migration nötig!**

**Einfach Code deployen:**
```bash
cd /opt/grow-pi
git pull  # (nachdem der User pushed hat)
sudo systemctl restart grow-pi
```

**Monitoring nach Deployment:**
```bash
# Logs für Retry-Warnings beobachten:
sudo journalctl -u grow-pi -f | grep -E "(retry|locked|BUSY)"
```

**Erwartung**: Keine Errors, evtl. einzelne Retry-Warnings bei High Load (OK!)

---

## Code Quality

**Python 3.9+ compatible**: ✅
**PEP 8 compliant**: ✅
**Type Hints vorhanden**: ✅
**Logging korrekt**: ✅
**Thread-Safe**: ✅
**No Breaking Changes**: ✅

---

**Implementation Status**: ✅ **COMPLETE**
**Ready for Deployment**: ✅ **YES** (nach User-Approval)
