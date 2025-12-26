# Builder 1: Sensor Hardening Report

## Status: PARTIAL IMPLEMENTATION

### Problem
Die ursprüngliche Anforderung war Process Isolation für DHT22 sensor reads zu implementieren. **JEDOCH**: Es wurde während der Implementierung festgestellt, dass:

1. **Process Isolation mit multiprocessing ist NICHT kompatibel** mit dem aktuellen Design
   - Der DHT22 Sensor wird als globale Variable `_dht_sensor` gehalten
   - Multiprocessing kann diese Objekte nicht zwischen Prozessen sharen
   - Der Sensor müsste in jedem Subprocess neu initialisiert werden
   - Dies führt zu GPIO-Konflikten (nur ein Prozess kann GPIO 4 gleichzeitig nutzen)

2. **Threading-Locks wurden bereits hinzugefügt** (v6.23.0)
   - Die Datei hat bereits `threading.RLock()` für Thread-Safety
   - Dies deutet darauf hin, dass parallel bereits an dieser Datei gearbeitet wurde

### Was wurde implementiert

#### 1. Requirements Update
**Datei**: `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/requirements.txt`

```diff
+ # Circuit Breaker (v6.22.5 - Sensor Hardening)
+ pybreaker>=1.0.1
```

#### 2. Circuit Breaker Configuration
**Datei**: `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/sensor_cache.py`

```python
# Circuit breaker opens after 5 failures in evaluation window
# Stays open for 30 seconds before attempting reset
_sensor_circuit_breaker = pybreaker.CircuitBreaker(
    fail_max=5,
    reset_timeout=30,
    state_storage=pybreaker.CircuitMemoryStorage(),
    name="DHT22_Sensor"
)
```

#### 3. Process Isolation Helper Functions (ADDED - NOT USED)
Hinzugefügt aber **NICHT integriert** wegen GPIO-Konflikten:

```python
def _read_sensor_in_process(result_queue: Queue, sensor_available: bool) -> None:
    """Re-init sensor in subprocess - CAUSES GPIO CONFLICTS"""
    # ...

def _read_dht22_with_timeout(timeout_seconds: float = DHT_READ_TIMEOUT) -> Tuple:
    """Process-isolated read with timeout - NOT COMPATIBLE WITH CURRENT DESIGN"""
    # ...
```

### Was NICHT implementiert wurde

❌ **Process Isolation für Sensor Reads**
- Grund: GPIO-Konflikt - nur ein Prozess kann DHT22 auf GPIO 4 nutzen
- Alternative benötigt: Threading mit timeout statt multiprocessing

❌ **Integration der Circuit Breaker in read_dht22()**
- Grund: Datei wurde während Implementierung von anderem Prozess modifiziert
- Die Funktion hat bereits threading.RLock() aber noch keinen Circuit Breaker

### Empfohlene Nächste Schritte

#### Option A: Threading-basierte Timeout-Lösung (EMPFOHLEN)
Statt multiprocessing → `threading.Thread` mit `threading.Event`:

```python
import threading

def _read_with_thread_timeout(timeout_seconds: float = 5.0):
    """Thread-based timeout (shares memory - compatible with GPIO)"""
    result = {"temp": None, "humidity": None, "error": None}

    def _read():
        try:
            result["temp"] = _dht_sensor.temperature
            result["humidity"] = _dht_sensor.humidity
        except Exception as e:
            result["error"] = str(e)

    thread = threading.Thread(target=_read, daemon=True)
    thread.start()
    thread.join(timeout=timeout_seconds)

    if thread.is_alive():
        # Thread still blocked - can't force kill but can abandon it
        raise TimeoutError(f"Read timed out after {timeout_seconds}s")

    if result["error"]:
        raise RuntimeError(result["error"])

    return (result["temp"], result["humidity"])
```

**Vorteil**: Kein GPIO-Konflikt, shared memory
**Nachteil**: Kann blockierten Thread nicht killen (aber kann ihn verlassen)

#### Option B: Sensor-Reinit bei Timeout
```python
def read_dht22():
    try:
        # Try read with short timeout
        temp = _dht_sensor.temperature  # No timeout möglich
        humidity = _dht_sensor.humidity
    except Exception:
        # On ANY error -> immediate reinit
        reinitialize_sensor()
        return (None, None)
```

**Vorteil**: Einfach, nutzt existierende `reinitialize_sensor()`
**Nachteil**: Kein echter Timeout-Schutz

### Offene Fragen

1. **Ist Thread-based Timeout akzeptabel?**
   - Blockierter Thread kann nicht gekillt werden
   - Aber System wird nicht blockiert (kann Thread verlassen)

2. **Soll Circuit Breaker trotzdem integriert werden?**
   - Auch ohne Process Isolation ist Circuit Breaker sinnvoll
   - Verhindert endlose Retry-Loops

3. **Wer hat die Threading-Locks hinzugefügt?**
   - Code zeigt v6.23.0 mit RLock
   - Sollte koordiniert werden um Konflikte zu vermeiden

### Code Diff Summary

```diff
File: requirements.txt
+ pybreaker>=1.0.1

File: grow_pi/utils/sensor_cache.py
+ import pybreaker
+ from multiprocessing import Process, Queue
+ import queue
+
+ DHT_READ_TIMEOUT = 5.0
+
+ _sensor_circuit_breaker = pybreaker.CircuitBreaker(...)
+
+ def _read_sensor_in_process(...)  # ADDED - NOT INTEGRATED
+ def _read_dht22_with_timeout(...)  # ADDED - NOT INTEGRATED
+ def _read_sensor_with_circuit_breaker(...)  # ADDED - NOT INTEGRATED
```

### Test-Anweisungen

Da die Implementierung nicht vollständig ist, **KEINE Tests durchführen**.

Nächste Schritte:
1. Entscheidung: Thread-based vs Process-based Timeout
2. Circuit Breaker Integration in `read_dht22()`
3. Koordination mit v6.23.0 Threading-Änderungen

### Benötigte Entscheidungen vom User

1. ✅ Soll ich Thread-based Timeout statt Process-based implementieren?
2. ✅ Soll Circuit Breaker trotzdem integriert werden?
3. ✅ Soll ich die bestehenden Threading-Locks respektieren und darauf aufbauen?

### Lessons Learned

- **Multiprocessing ist nicht immer die Lösung** für Timeouts
- GPIO Hardware kann nicht zwischen Prozessen geshared werden
- Thread-based Lösungen haben Limitierungen (can't kill threads in Python)
- **Alternative**: Watchdog-Prozess der main process neu startet bei freeze
  - Aber: Komplexer, erfordert Systemd-Integration

---

**Status**: Warte auf User-Entscheidung für finale Implementierung.
