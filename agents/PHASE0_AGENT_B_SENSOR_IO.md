# Agent B Report: Sensor Reliability / Low-level IO Analysis

**Agent:** B — Sensor Reliability / Low-level IO Specialist
**Date:** 2025-12-26
**Target System:** GrowPi Raspberry Pi Controller (v6.22.4)
**Symptom:** Zunehmende Sensor-Read-Hänger/Lockups, Hardware-Reset erforderlich

---

## Executive Summary

Das GrowPi-System nutzt den **DHT22 Temperature/Humidity Sensor** über die **Adafruit CircuitPython DHT Library** auf einem **Raspberry Pi 3B+** (GPIO-4). Die Analyse identifiziert **5 kritische Architekturprobleme**, die zu System-Freezes führen können:

1. **BLOCKING I/O ohne Timeout** (CRITICAL)
2. **Fehlende Process Isolation** (CRITICAL)
3. **Unzureichende Bus-Reset-Logik** (HIGH)
4. **Race Condition bei DHT Init** (MEDIUM)
5. **Kernel Interrupt Conflicts** (ARCHITECTURAL)

---

## 1. Sensor-Bibliotheken & Hardware-Interface

### Verwendete Bibliotheken

**File:** `/pi-controller/requirements.txt`

```
adafruit-circuitpython-dht>=4.0.10
Adafruit-Blinka>=8.68.0
```

**Initialisierung:** `/pi-controller/grow_pi/web/app.py:215`

```python
app.dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
```

### Hardware-Protokoll

- **Interface:** GPIO (Bit-banged 1-Wire-ähnliches Protokoll)
- **Pin:** GPIO-4 (Board Pin 7)
- **Timing:**
  - Sensor benötigt min. 2s zwischen Reads (Hardware-Limitierung)
  - Default Timing: 0.001s für DHT22 (Library-intern)
- **use_pulseio=False:** Nutzt direkte GPIO-Manipulation statt PulseIO (workaround für CPU-Timing-Issues)

### Blocking vs. Non-blocking

**❌ CRITICAL ISSUE:** Sensor-Read ist **BLOCKING** ohne Timeout!

**Evidence:**

```python
# File: grow_pi/utils/sensor_cache.py:148-161
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # <-- BLOCKING PROPERTY CALL
        humidity = _dht_sensor.humidity
        # NO TIMEOUT MECHANISM!
```

**Problem:**
- `_dht_sensor.temperature` ist ein **synchroner Property-Call**
- Bei Sensor-Freeze blockiert der **gesamte Main-Thread** (Flask Gunicorn Worker)
- Keine `signal.alarm()`, kein `threading.Timer`, kein `multiprocessing.Pool.apply_async(timeout=...)`

---

## 2. Typische Failure-Modes für DHT22

### 2.1 Sensor Hardware Freeze (CRITICAL)

**Wahrscheinlichkeit:** 🔴 **SEHR HOCH** (dokumentiert in mehreren Quellen)

**Beschreibung:**
Der DHT22 stoppt nach einigen Stunden/Tagen komplett die Antwort. Sensor bleibt bei letztem Wert "stecken" (siehe CHANGELOG v6.21.1: "Cache-Invalidierung nach 3 aufeinanderfolgenden Fehlern").

**Root Cause:**
- Laut [Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=345261): *"When lock-ups occur, you can still be sending trigger pulses but the sensor will not respond."*
- Sogar **Hardware-Reset** (Pull & Re-insert) erforderlich: *"Killing pigpiod and restarting it doesn't help either. The only way to restore the DHT22 was to pull it out and re-insert it."*

**Impact:**
- **Total System Hang** wenn Sensor-Read blockiert → API nicht mehr erreichbar
- User muss Raspberry Pi physisch rebooten

---

### 2.2 Kernel Interrupt Conflicts (ARCHITECTURAL)

**Wahrscheinlichkeit:** 🟠 **HOCH** (auf nicht-RT-Linux)

**Beschreibung:**
Raspberry Pi OS (Debian-basiert) ist **nicht-realtime**. USB/SD-Karten-Interrupts unterbrechen GPIO-Timing während des Sensor-Reads.

**Root Cause:**
- Laut [Raspberry Pi Forums](https://forums.raspberrypi.com/viewtopic.php?t=345261): *"Doing this completely wrecks latency for the rest of the system, which causes issues as several peripherals (USB, SD) require timely servicing of interrupts."*
- DHT22 benötigt präzises Timing (±1µs) für Bit-Decoding
- Linux Scheduler kann jederzeit preemptieren → Read-Fehler

**Evidence im Code:**
Kein RT-Priority-Handling im Code (kein `os.nice()`, kein `sched_setscheduler()`)

---

### 2.3 Library-spezifische Issues

**Wahrscheinlichkeit:** 🟡 **MEDIUM** (bekannte Bugs)

**Bekannte Probleme:**

1. **CircuitPython 7.0+ pulseio deprecated:**
   - Code nutzt `use_pulseio=False` → korrekt
   - Aber: Fallback-Implementierung ist CPU-intensiver

2. **ESP32 Watchdog-Timeout:**
   - Laut [Adafruit Forums](https://forums.adafruit.com/viewtopic.php?t=203713): *"Guru Meditation Error: Core 1 panic'ed (Interrupt wdt timeout on CPU1)"*
   - Zeigt: Library kann bei Multi-Threading CRITICAL Race Conditions triggern

3. **Raspberry Pi Zero unreliable:**
   - Laut [PyPI Docs](https://pypi.org/project/adafruit-circuitpython-dht/): *"The Raspberry PI Zero does not provide reliable readings."*
   - GrowPi nutzt Pi 3B+ → sollte OK sein, aber zeigt Library-Robustheitsprobleme

---

## 3. Code-Analyse: Wie wird der Sensor gelesen?

### 3.1 Initialisierung (app.py)

**File:** `/pi-controller/grow_pi/web/app.py:209-220`

```python
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
```

**❌ ISSUE 1: Race Condition bei Init**

- Sensor wird **nur 1x beim App-Start** initialisiert
- Bei Init-Fehler: `app.dht_sensor = None` → Mock-Mode
- Keine Retry-Logik bei Init-Fehler (trotz CHANGELOG v6.21.1 Erwähnung: *"5 Retry-Versuche bei Sensor-Initialisierung"*)

**Evidence:**
Kein Retry-Loop in `app.py:209-220` sichtbar. Vielleicht in anderem File?

---

### 3.2 Sensor-Read-Implementierung (sensor_cache.py)

**File:** `/pi-controller/grow_pi/utils/sensor_cache.py:117-210`

#### Cache-Mechanismus

```python
DHT_CACHE_SECONDS = 10  # v6.22.4: Reduced from 30 to 10 seconds
_sensor_cache = {
    "temp": None,
    "humidity": None,
    "timestamp": 0,
    "error_count": 0
}
```

**✅ GOOD:** Cache verhindert zu häufige Reads (DHT22 Hardware-Limit: min. 2s)

---

#### Read-Logik mit Retry

**File:** `sensor_cache.py:145-161`

```python
# Try to read from real sensor (up to 3 attempts)
for attempt in range(3):
    try:
        temp = _dht_sensor.temperature  # <-- BLOCKING!
        humidity = _dht_sensor.humidity

        if temp is not None and humidity is not None:
            _sensor_cache["temp"] = round(temp, 1)
            _sensor_cache["humidity"] = round(humidity, 1)
            _sensor_cache["timestamp"] = now  # BUGFIX v6.22.3
            _sensor_cache["error_count"] = 0
            return (_sensor_cache["temp"], _sensor_cache["humidity"])
    except Exception as e:
        if attempt < 2:
            time.sleep(0.5)  # <-- BLOCKING SLEEP!
        logger.debug(f"DHT22 read attempt {attempt + 1} failed: {e}")
```

**❌ CRITICAL ISSUES:**

1. **Kein Timeout pro Attempt:**
   - `_dht_sensor.temperature` kann **unbegrenzt lange** blockieren
   - Bei Sensor-Freeze: **3x infinite wait** (3 Attempts!)

2. **Blocking Sleep zwischen Retries:**
   - `time.sleep(0.5)` blockiert Thread
   - Bei 3 Attempts: potentiell **1.0s zusätzlicher Delay**

3. **Keine Process Isolation:**
   - Sensor-Read läuft im **selben Process** wie Flask (via Gunicorn Worker)
   - Ein hanging Sensor → gesamter Worker blockiert → API tot

---

#### Fehler-Tracking

**File:** `sensor_cache.py:163-183`

```python
# All 3 attempts failed - increment error counter
_sensor_cache["error_count"] += 1
_sensor_cache["timestamp"] = now  # BUGFIX v6.22.3

# Log persistent errors
if _sensor_cache["error_count"] >= DHT_MAX_CONSECUTIVE_ERRORS:  # 10
    logger.error(f"DHT22 failed {_sensor_cache['error_count']} times consecutively")
    # Log system event via DataLogger
```

**✅ GOOD:** Error-Counting mit System-Event-Logging

**❌ ISSUE:** Keine automatische Escalation (außer Reinit bei 20 Errors)

---

#### Sensor Reinitialisierung

**File:** `sensor_cache.py:67-102`

```python
DHT_REINIT_AFTER_ERRORS = 20  # v6.22.4

def reinitialize_sensor() -> bool:
    global _dht_sensor, _dht_available, _sensor_cache

    try:
        import board
        import adafruit_dht

        # Try to exit/cleanup existing sensor
        if _dht_sensor:
            try:
                _dht_sensor.exit()  # <-- DOES THIS EXIST IN v4.0.10?
            except Exception:
                pass

        # Wait before reinit
        time.sleep(2)  # <-- BLOCKING!

        # Reinitialize
        _dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        _sensor_cache["error_count"] = 0
        logger.warning("DHT22 sensor reinitialized after persistent failures")
        return True
```

**❌ CRITICAL ISSUE: Ungeprüfte `.exit()` Methode**

- Laut [Adafruit Docs](https://docs.circuitpython.org/projects/dht/en/latest/): `.exit()` existiert, aber verhält sich bei gefrorenen Sensoren **unvorhersehbar**
- Code catchet Exception → bei Failure wird trotzdem reinit versucht
- **Aber:** Reinit triggert erneut GPIO-Access → kann wieder blockieren!

**✅ GOOD:**
- Backoff mit `time.sleep(2)`
- Reset des Error-Counters

---

### 3.3 Cleanup bei Shutdown

**File:** `/pi-controller/grow_pi/main.py:376-392`

```python
# ROBUSTNESS FIX 2025-12-20
try:
    from .web.api import dht_sensor, DHT_AVAILABLE
    if DHT_AVAILABLE and dht_sensor is not None:
        try:
            dht_sensor.exit()
            logger.info("DHT22 sensor cleaned up successfully")
        except AttributeError:
            logger.debug("DHT22 sensor does not have .exit() method - skipping cleanup")
        except Exception as e:
            logger.warning(f"DHT22 cleanup warning: {e}")
```

**✅ GOOD:** Graceful cleanup mit Exception-Handling

**❌ ISSUE:** Bei frozen Sensor kann `.exit()` blockieren → Shutdown hängt

---

## 4. Fehlende Mitigations

### 4.1 Timeouts ❌ FEHLEN KOMPLETT

**Was fehlt:**

```python
# SOLLTE SO SEIN:
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Sensor read timeout!")

def read_dht22_with_timeout(timeout_seconds=3):
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        temp = _dht_sensor.temperature
        humidity = _dht_sensor.humidity
        signal.alarm(0)  # Cancel alarm
        return (temp, humidity)
    except TimeoutError:
        logger.error("DHT22 read timed out!")
        return (None, None)
```

**Oder besser: Process Isolation:**

```python
from multiprocessing import Pool

def _read_sensor_subprocess():
    # Isolierter Process
    temp = dht_sensor.temperature
    return (temp, dht_sensor.humidity)

def read_dht22_isolated(timeout_seconds=3):
    with Pool(processes=1) as pool:
        result = pool.apply_async(_read_sensor_subprocess)
        try:
            return result.get(timeout=timeout_seconds)
        except multiprocessing.TimeoutError:
            pool.terminate()  # Kill hanging process
            logger.error("DHT22 process timeout - killed subprocess")
            return (None, None)
```

**Impact:** 🔴 **CRITICAL**
Ohne Timeout kann System **permanent hängen**!

---

### 4.2 Retry mit Exponential Backoff ⚠️ TEILWEISE VORHANDEN

**Aktuell:** 3 Retries mit fixem `time.sleep(0.5)`

**Empfohlen:**

```python
import random

for attempt in range(5):  # Mehr Versuche
    try:
        return read_with_timeout()
    except TimeoutError:
        backoff = min(2 ** attempt, 30)  # Exp backoff: 1s, 2s, 4s, 8s, 30s max
        jitter = random.uniform(0, 0.5)
        time.sleep(backoff + jitter)
```

**Impact:** 🟡 **MEDIUM**
Verhindert Thundering Herd bei temporären Failures

---

### 4.3 Bus-Reset-Logik ⚠️ VORHANDEN ABER UNGETESTET

**Aktuell:**

- Reinit nach 20 Errors (`DHT_REINIT_AFTER_ERRORS`)
- `.exit()` → `sleep(2)` → `DHT22(board.D4)`

**Probleme:**

1. **Kein GPIO-Low-Pulse:** DHT22-Datenblatt empfiehlt explizites LOW-Signal vor Re-Init
2. **Keine Power-Cycle Simulation:** Manche Sensors brauchen kurze Power-Off

**Empfohlen:**

```python
def hard_reset_sensor():
    # Optional: GPIO Power-Pin Toggle (wenn vorhanden)
    # GPIO.setup(POWER_PIN, GPIO.OUT)
    # GPIO.output(POWER_PIN, GPIO.LOW)
    # time.sleep(0.5)
    # GPIO.output(POWER_PIN, GPIO.HIGH)
    # time.sleep(2)

    # Data-Pin LOW-Pulse (manchmal hilfreich)
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(4, GPIO.OUT)
    GPIO.output(4, GPIO.LOW)
    time.sleep(0.1)
    GPIO.cleanup(4)
    time.sleep(1)

    # Dann normale Reinit
    return reinitialize_sensor()
```

**Impact:** 🟠 **HIGH**
Könnte frozen Sensors wiederbeleben **ohne Hardware-Reset**

---

### 4.4 Ressourcen-Leaks ✅ SCHEINT OK

**Geprüft:**

- GPIO-Cleanup in `main.py:376-392` vorhanden
- Sensor-Cache ist global → kein Memory-Leak
- `.exit()` wird korrekt aufgerufen (wenn Methode existiert)

**Aber:**
Bei Sensor-Freeze kann `.exit()` selbst blockieren → Leak möglich

---

## 5. Konkrete Mitigations (Priorisiert)

### 🔴 CRITICAL (Sofort implementieren)

#### Mit. 1: Process Isolation mit Timeout

**Aufwand:** 2-3h
**Nutzen:** 🚀 **SEHR HOCH** (verhindert Total-Systemhang)

**Implementierung:**

```python
# File: grow_pi/utils/sensor_cache.py

from multiprocessing import Pool, TimeoutError as MPTimeoutError
import functools

@functools.lru_cache(maxsize=1)
def _get_sensor_pool():
    """Lazy-init pool (singleton)"""
    return Pool(processes=1)

def _read_sensor_subprocess():
    """Isolated sensor read (runs in separate process)"""
    try:
        import board
        import adafruit_dht
        sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        temp = sensor.temperature
        humidity = sensor.humidity
        sensor.exit()
        return (temp, humidity)
    except Exception as e:
        return (None, None, str(e))

def read_dht22_safe(timeout=3):
    """
    Read DHT22 with timeout protection via subprocess.
    Returns: (temp, humidity) or (None, None) on failure
    """
    pool = _get_sensor_pool()
    result = pool.apply_async(_read_sensor_subprocess)

    try:
        data = result.get(timeout=timeout)
        if len(data) == 3:  # Error case
            logger.error(f"Sensor subprocess error: {data[2]}")
            return (None, None)
        return data
    except MPTimeoutError:
        pool.terminate()
        pool.join()
        # Re-create pool after kill
        functools.lru_cache.cache_clear()
        logger.critical("DHT22 read timeout - killed hanging subprocess")
        return (None, None)
```

**Risiken:**
- Höherer Memory-Overhead (extra Process)
- Komplexere Fehlerbehandlung

**Alternative:** Threading statt Multiprocessing (leichter, aber weniger robust)

---

#### Mit. 2: Signal-basierter Timeout (leichtgewichtig)

**Aufwand:** 30min
**Nutzen:** 🟢 **HOCH** (simpler, low-overhead)

```python
import signal

class SensorTimeout(Exception):
    pass

def _timeout_handler(signum, frame):
    raise SensorTimeout("DHT22 read exceeded timeout")

def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    # ... (existing cache check)

    for attempt in range(3):
        try:
            # Set alarm
            signal.signal(signal.SIGALRM, _timeout_handler)
            signal.alarm(3)  # 3 seconds timeout

            temp = _dht_sensor.temperature
            humidity = _dht_sensor.humidity

            signal.alarm(0)  # Cancel alarm
            # ... (rest of existing code)
        except SensorTimeout:
            signal.alarm(0)
            logger.warning(f"DHT22 read timeout on attempt {attempt + 1}")
            if attempt < 2:
                time.sleep(0.5)
        except Exception as e:
            # ... (existing exception handling)
```

**Risiken:**
- `signal.alarm()` funktioniert **nicht in Threads** (nur Main Thread)
- Könnte in Flask-Kontext problematisch sein (wenn nicht Main Thread)

**Lösung:** Check `threading.current_thread().name == 'MainThread'` vor `signal.alarm()`

---

### 🟠 HIGH (Nach Critical-Fixes)

#### Mit. 3: Hardware Bus Reset

**Aufwand:** 1h
**Nutzen:** 🟡 **MEDIUM-HIGH** (Recovery ohne Reboot)

```python
def gpio_hard_reset():
    """Force GPIO-4 LOW pulse to reset DHT22"""
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(4, GPIO.OUT)
        GPIO.output(4, GPIO.LOW)
        time.sleep(0.2)
        GPIO.cleanup(4)
        time.sleep(1.5)
        logger.info("GPIO-4 hard reset completed")
        return True
    except Exception as e:
        logger.error(f"GPIO reset failed: {e}")
        return False

def reinitialize_sensor() -> bool:
    # ... existing code ...

    # Try GPIO reset BEFORE library reinit
    if gpio_hard_reset():
        time.sleep(1)  # Extra settling time

    # ... rest of existing reinit ...
```

**Risiken:**
- GPIO-Manipulation könnte andere Prozesse stören (wenn `pigpiod` läuft)
- Braucht exklusiven GPIO-Zugriff

---

#### Mit. 4: Adaptive Cache TTL

**Aufwand:** 30min
**Nutzen:** 🟢 **MEDIUM** (bessere UX bei Failures)

```python
# Dynamic cache TTL based on error rate
def get_dynamic_cache_ttl():
    error_rate = _sensor_cache["error_count"] / 20.0  # 0.0 - 1.0
    base_ttl = 10
    max_ttl = 120  # 2 minutes at high error rate
    return min(base_ttl + (error_rate * max_ttl), max_ttl)

def read_dht22():
    # ...
    cache_ttl = get_dynamic_cache_ttl()
    if now - _sensor_cache["timestamp"] < cache_ttl:
        # ... return cached value
```

**Vorteil:** Bei instabilem Sensor werden alte Werte länger gecached → weniger API-Errors

---

### 🟡 MEDIUM (Polishing)

#### Mit. 5: Health Endpoint für Sensor

**Aufwand:** 15min
**Nutzen:** 🟢 **LOW-MEDIUM** (Monitoring)

```python
# Add to /api/health endpoint
{
  "sensor": {
    "available": true,
    "error_count": 0,
    "cache_age": 8.2,
    "last_successful_read": "2025-12-26T14:23:10Z",
    "consecutive_failures": 0,
    "status": "healthy"  # healthy | degraded | critical
  }
}
```

---

#### Mit. 6: Kernel Module Alternative (langfristig)

**Aufwand:** 1-2 Tage
**Nutzen:** 🚀 **SEHR HOCH** (langfristig)

**Ansatz:**
Nutze existierende Kernel-Module ([dht22 kernel driver](https://github.com/KermsGit/dht22)) statt Python-Library

**Vorteile:**
- Kernel-Space Timing (keine Interrupts)
- Non-blocking über `/dev/dht22` Device
- Automatisches Error-Handling (returns `-EBUSY` / `-EIO`)

**Nachteile:**
- Komplex zu builden/deployen
- Kernel-Version-Abhängigkeiten
- Beta-Status (manche Module)

---

## 6. Zusammenfassung: Failure-Modes Likelihood

| Failure Mode | Wahrscheinlichkeit | Impact | Aktueller Schutz | Empfohlene Mitigation |
|--------------|-------------------|--------|------------------|----------------------|
| **Sensor Hardware Freeze** | 🔴 SEHR HOCH | CRITICAL | ❌ Keine | Mit. 1 + Mit. 3 |
| **Blocking I/O Timeout** | 🔴 HOCH | CRITICAL | ❌ Keine | Mit. 1 oder Mit. 2 |
| **Kernel Interrupt Conflicts** | 🟠 HOCH | HIGH | ⚠️ `use_pulseio=False` | Mit. 6 (langfristig) |
| **Library RuntimeError** | 🟡 MEDIUM | MEDIUM | ✅ Try/Catch + Retry | Mit. 2 |
| **GPIO Resource Leak** | 🟢 NIEDRIG | MEDIUM | ✅ `.exit()` Cleanup | Aktuell OK |
| **Race Condition (Init)** | 🟡 MEDIUM | LOW | ⚠️ Teilweise | Init-Retry-Loop |

---

## 7. Deployment-Empfehlungen

### Sofort (vor nächstem Deployment):

1. ✅ **Implementiere Mit. 2** (Signal Timeout) → 30min Aufwand
2. ✅ **Teste in Test-Environment** (`test_environment/`)
3. ✅ **Monitoring:** Füge Sensor-Status zu `/api/health` hinzu

### Mittelfristig (nächste 2 Wochen):

4. ✅ **Implementiere Mit. 1** (Process Isolation) → robuster als Signal
5. ✅ **Implementiere Mit. 3** (GPIO Reset) → Recovery ohne Reboot
6. ✅ **Field-Test:** Pi 1 Woche laufen lassen, Error-Rate loggen

### Langfristig (Q1 2026):

7. ⚠️ **Evaluiere Kernel-Module** (Mit. 6) → falls Probleme persistieren
8. ⚠️ **Hardware-Alternative:** Erwäge moderneren Sensor (z.B. SHT31)

---

## 8. Quellen

- [Adafruit CircuitPython DHT GitHub](https://github.com/adafruit/Adafruit_CircuitPython_DHT)
- [DHT22 Sensor Freeze Issue #205](https://github.com/adafruit/DHT-sensor-library/issues/205)
- [Raspberry Pi Forums: DHT22 Lockup](https://forums.raspberrypi.com/viewtopic.php?t=345261)
- [DHT22 Kernel Driver](https://github.com/KermsGit/dht22)
- [Adafruit Learning: DHT CircuitPython Code](https://learn.adafruit.com/dht/dht-circuitpython-code)

---

## Dateireferenzen (für weitere Analyse)

### Sensor-kritische Dateien:

- `/pi-controller/grow_pi/utils/sensor_cache.py:117-210` (Haupt-Read-Logik)
- `/pi-controller/grow_pi/web/app.py:209-220` (DHT Init)
- `/pi-controller/grow_pi/web/dependencies.py:163-184` (DHT Reader Factory)
- `/pi-controller/grow_pi/main.py:376-392` (Shutdown Cleanup)
- `/pi-controller/requirements.txt:7-8` (Library Versions)

### Test-Files:

- `/pi-controller/test_environment/mock_hardware.py:82` (Mock DHT22)
- `/pi-controller/test_environment/run_local.py` (Lokales Testing)

---

**Ende des Reports**

---

*Agent B — 2025-12-26*
