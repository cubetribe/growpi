# PI CRASH DIAGNOSIS REPORT

**Erstellt**: 2025-12-20
**Status**: Kritische Fehler identifiziert
**Version**: v6.21.0

---

## Zusammenfassung

Der Raspberry Pi ist aufgrund von **Fehlern in der Exception-Handling bei der DHT22-Sensor-Initialisierung nach dem Neustart** abgestürzt. Nach dem Hardware-Neustart funktioniert der Sensor nicht mehr, weil sich die Sensor-Instanz in einem beschädigten Zustand befindet.

---

## 1. KRITISCHE FEHLERURSACHEN (PRIORISIERT)

### A. **BLOCKING ISSUE #1: Sensor-Initialisierung nach Neustart schlägt fehl**

**Datei:** `pi-controller/grow_pi/web/api.py` (Zeilen 220-225)

```python
# Zeilen 220-225: DHT22-Initialisierung
dht_sensor = None
if DHT_AVAILABLE:
    try:
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        logger.info("DHT22 Sensor initialized on GPIO-4")
    except Exception as e:
        logger.error(f"Failed to initialize DHT22: {e}")
        # PROBLEM: dht_sensor bleibt None, aber System läuft weiter!
```

**Problem:**
- Wenn die DHT22-Initialisierung fehlschlägt, wird `dht_sensor = None` gesetzt
- Der Code lässt die App starten, obwohl das Kerngerät nicht funktioniert
- Keine Failover-Mechanismus, um den Sensor zu reinitalisieren

---

### B. **BLOCKING ISSUE #2: Cache-Vergiftung nach Sensor-Fehler**

**Datei:** `temperature_bp.py` (Zeilen 57-98) + `api.py` (Zeilen 310-351)

```python
# Zeilen 326-329: Cache wird niemals invalidiert
if now - _dht_cache["timestamp"] < DHT_CACHE_SECONDS:
    if _dht_cache["temp"] is not None:
        return (_dht_cache["temp"], _dht_cache["humidity"])
```

**Problem:**
- Wenn Sensor einmal Werte liefert (vor Absturz), werden diese für 30 Sekunden gecacht
- Wenn Sensor nach Neustart ausfällt, werden ALTE gecachte Werte zurückgegeben
- **Symptom: "festgenagelte" Temperatur**
- Cache hat keine Invalidierungs-Logik bei Sensor-Fehler

---

### C. **BLOCKING ISSUE #3: DataLogger ignoriert Sensor-Fehler stilschweigend**

**Datei:** `grow_pi/database/logger.py` (Zeilen 203-226)

```python
def _log_sensors(self) -> None:
    """Read and log sensor values."""
    if not self._sensor_reader:
        return

    temp, humidity = self._sensor_reader()

    if temp is not None:
        reading = SensorReading(...)
        self.db.insert_sensor_reading(reading)
```

**Problem:**
- Wenn `read_dht22()` nach Fehler mit `(None, None)` zurückkommt, wird NICHTS geloggt
- Keine Fehlerereignis in der Datenbank gespeichert
- Frontend erhält keine Warnung, dass Sensor ausfällt
- DataLogger-Thread läuft einfach weiter ohne Diagnostik

---

### D. **MEMORY LEAK #1: DHT22-Objekt wird nicht freigegeben**

**Datei:** `api.py` (Zeilen 220-225)

```python
dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
# PROBLEM: Keine cleanup() oder deinit() beim Neustart!
```

**Auswirkung:**
- Beim Pi-Neustart bleibt der alte DHT22-Prozess möglicherweise im GPIO-Driver
- Neue Initialisierung versucht, GPIO-4 zu öffnen, aber der Treiber sperrt es
- RuntimeError: "Can't create sensor object" oder GPIO-Konflikt

---

### E. **RACE CONDITION: Dehumidifier greift auf toten Sensor zu**

**Datei:** `grow_pi/utils/dehumidifier_controller.py` + `api.py` (Zeilen 355-358)

```python
if dehumidifier_controller is not None:
    dehumidifier_controller.set_humidity_reader(read_dht22)
    # PROBLEM: Wenn read_dht22 mit None/None zurückkommt,
    # versucht DehumidifierController, im Kreis zu laufen
```

**Auswirkung:**
- Dehumidifier-Thread liest ständig None-Werte
- Könnte zu Thread-Deadlock oder ExceptionHandler-Überfluss führen
- Verursacht CPU-Last und potenzielle OOM-Fehler

---

## 2. WARUM NACH NEUSTART KEINE WERTE MEHR KOMMEN

**Fehlersequenz:**

1. **Vor Absturz:** DHT22 läuft, Cache speichert Werte (22.5°C, 65%)
2. **Absturz passiert:** Pi wird hart ausgeschaltet (Strom raus/rein)
3. **Pi bootet neu:**
   - `pigpiod` wird gestartet
   - `grow-pi` Web-Service startet
   - **FEHLER:** `dht_sensor = adafruit_dht.DHT22(board.D4)` schlägt fehl
     - Grund: GPIO-4 ist möglicherweise vom alten Prozess blockiert
     - Oder: Sensor-Timing ist beschädigt nach Hard-Reset
4. **Cache wird zurückgegeben:** Frontend zeigt alte Werte (festgenagelt!)
5. **Nach Cache-Ablauf:** Keine Werte mehr (None)

---

## 3. SOFORT-MASSNAHMEN (SSH auf Pi)

```bash
# 1. Service-Status prüfen
sudo systemctl status grow-pi

# 2. Logs der letzten Minuten
sudo journalctl -u grow-pi -n 100 --no-pager

# 3. GPIO-Status prüfen
gpio readall

# 4. Prüfen ob DHT22 blockiert ist
lsof /dev/gpiomem

# 5. Service neustarten (sauber)
sudo systemctl restart grow-pi

# 6. Erneut Logs prüfen
sudo journalctl -u grow-pi -f
```

---

## 4. EMPFOHLENE CODE-FIXES

### Fix #1: Robuste Sensor-Initialisierung mit Wiederversuchen

```python
# In api.py - DHT22 Init
max_retries = 5
for attempt in range(max_retries):
    try:
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        logger.info("DHT22 Sensor initialized on GPIO-4")
        break
    except Exception as e:
        logger.error(f"DHT22 init attempt {attempt+1}/{max_retries} failed: {e}")
        if attempt < max_retries - 1:
            time.sleep(2)
        else:
            logger.critical("DHT22 sensor initialization FAILED - running in fallback mode")
            DHT_AVAILABLE = False
```

### Fix #2: Cache-Invalidierung bei Sensor-Fehler

```python
def read_dht22() -> Tuple[Optional[float], Optional[float]]:
    global _dht_cache

    if dht_sensor is None:
        return (None, None)

    now = time.time()

    # Invalidiere Cache wenn > 60 Sekunden alt
    if now - _dht_cache["timestamp"] >= 60:
        _dht_cache = {"temp": None, "humidity": None, "timestamp": 0}

    # ... rest of logic
```

### Fix #3: Sensor-Fehler-Ereignisse protokollieren

```python
# In logger.py _log_sensors():
if temp is None or humidity is None:
    self.log_event(
        'sensor_error',
        'warning',
        f"DHT22 sensor returned None values",
        {'recovered': False}
    )
```

### Fix #4: Sauberes Cleanup bei Shutdown

```python
# In main.py stop() Methode:
def stop(self) -> None:
    global dht_sensor
    if dht_sensor is not None:
        try:
            dht_sensor.exit()
            dht_sensor = None
            logger.info("DHT22 sensor cleaned up")
        except Exception as e:
            logger.error(f"Error cleaning up DHT22: {e}")
```

---

## 5. PRÄVENTIV-MASSNAHMEN (ROADMAP)

| Massnahme | Priorität | Aufwand |
|-----------|-----------|---------|
| Pi Health Dashboard (CPU-Temp, RAM, Disk) | HOCH | 1 Tag |
| CPU-Lüftersteuerung (temperaturgesteuert) | HOCH | 0.5 Tag |
| Sensor-Watchdog mit Auto-Restart | MITTEL | 0.5 Tag |
| Heartbeat-Monitoring | MITTEL | 0.5 Tag |

---

## ZUSAMMENFASSUNG DER ABSTURZURSACHEN

| Nr. | Ursache | Severity | Symptom |
|-----|---------|----------|---------|
| 1 | DHT22-Init schlägt fehl nach Neustart | CRITICAL | Keine Sensorwerte |
| 2 | Cache-Vergiftung (30s) | CRITICAL | "Festgenagelt" Temperatur |
| 3 | DataLogger ignoriert Fehler | HIGH | Keine Fehler-Diagnostik |
| 4 | GPIO-Ressource nicht freigegeben | HIGH | Init-Konflikt nach Reboot |
| 5 | Keine Fallback-Strategie | HIGH | App läuft mit broken sensor |
| 6 | Memory Leak in Threads | MEDIUM | Potenzielle OOM über Tage |

**Dringendste Massnahme:**
1. SSH auf Pi → Logs prüfen → Service neustarten
2. Code-Fixes für Sensor-Robustheit implementieren
3. Pi Health Dashboard für Früherkennung
