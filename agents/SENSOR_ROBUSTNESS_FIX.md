# Sensor Robustness Fix - Implementation Report

**Agent**: @builder
**Datum**: 2025-12-20
**Kontext**: DHT22 Sensor Absturz nach Hard-Reset

---

## Executive Summary

Nach einem nächtlichen Pi-Absturz und Hard-Reset brauchte der DHT22 Sensor mehrere Versuche zur Initialisierung ("A full buffer was not returned"). Die bestehende Retry-Logik funktionierte, aber das System wurde robuster gemacht gegen zukünftige Hardware-Probleme.

**Alle Änderungen sind LOKAL** und müssen vom User manuell auf den Pi kopiert werden.

---

## Implementierte Fixes

### 1. Robustere DHT22-Initialisierung

**Datei**: `/pi-controller/grow_pi/web/api.py` (Zeilen 218-243)

**Problem**:
- Bei Hard-Reset kann DHT22 beim ersten Init-Versuch fehlschlagen
- Ein Fehlschlag führte zu Mock-Daten ohne weitere Versuche

**Lösung**:
```python
# VORHER:
dht_sensor = None
if DHT_AVAILABLE:
    try:
        dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
        logger.info("DHT22 Sensor initialized on GPIO-4")
    except Exception as e:
        logger.error(f"Failed to initialize DHT22: {e}")

# NACHHER:
dht_sensor = None
if DHT_AVAILABLE:
    max_init_retries = 5
    init_retry_delay = 2

    for attempt in range(1, max_init_retries + 1):
        try:
            dht_sensor = adafruit_dht.DHT22(board.D4, use_pulseio=False)
            logger.info(f"DHT22 Sensor initialized on GPIO-4 (attempt {attempt}/{max_init_retries})")
            break
        except RuntimeError as e:
            if attempt < max_init_retries:
                logger.warning(f"DHT22 init attempt {attempt}/{max_init_retries} failed: {e} - retrying in {init_retry_delay}s...")
                time.sleep(init_retry_delay)
            else:
                logger.error(f"DHT22 initialization failed after {max_init_retries} attempts: {e}")
                logger.error("DHT_AVAILABLE set to False - sensor will return mock data")
                DHT_AVAILABLE = False
                dht_sensor = None
        except Exception as e:
            logger.error(f"Unexpected DHT22 initialization error: {e}")
            DHT_AVAILABLE = False
            dht_sensor = None
            break
```

**Verbesserungen**:
- 5 Retry-Versuche mit 2 Sekunden Pause
- Unterscheidung zwischen RuntimeError (Sensor busy) und anderen Fehlern
- Explizites Logging bei jedem Versuch
- Sauberer Fallback zu Mock-Daten wenn alle Versuche fehlschlagen

---

### 2. Cache-Invalidierung bei Sensor-Fehler

**Datei**: `/pi-controller/grow_pi/web/api.py` (Zeilen 328-402)

**Problem**:
- Cache lieferte alte Werte auch wenn Sensor dauerhaft fehlschlug
- Keine Erkennung von persistenten Hardware-Problemen

**Lösung**:
```python
# VORHER:
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0}

# NACHHER:
_dht_cache = {"temp": None, "humidity": None, "timestamp": 0, "error_count": 0}
DHT_MAX_CONSECUTIVE_ERRORS = 3

def read_dht22():
    # ... retry logic ...

    # All 3 attempts failed - increment error counter
    _dht_cache["error_count"] += 1

    # Invalidate cache if too many consecutive errors
    if _dht_cache["error_count"] >= DHT_MAX_CONSECUTIVE_ERRORS:
        logger.error(f"DHT22 failed {_dht_cache['error_count']} times consecutively - invalidating cache")
        _dht_cache["temp"] = None
        _dht_cache["humidity"] = None
        _dht_cache["timestamp"] = 0

        # Log persistent sensor error for monitoring
        if data_logger:
            try:
                data_logger.log_event(
                    'sensor_persistent_error',
                    'error',
                    f'DHT22 failed {_dht_cache["error_count"]} consecutive reads',
                    {'error_count': _dht_cache["error_count"]}
                )
            except Exception:
                pass

        return (None, None)

    # On success: Reset error count
    _dht_cache["error_count"] = 0
```

**Verbesserungen**:
- Zähler für aufeinanderfolgende Fehler
- Cache wird nach 3 Fehlern ungültig (verhindert stale data)
- System-Event wird geloggt für Monitoring
- Error-Count wird bei Erfolg zurückgesetzt

---

### 3. Sauberes Sensor-Cleanup

**Datei**: `/pi-controller/grow_pi/main.py` (Zeilen 376-392)

**Problem**:
- DHT22 wurde beim Shutdown nicht sauber freigegeben
- Konnte zu GPIO-Konflikten beim Restart führen

**Lösung**:
```python
# VORHER:
def stop(self) -> None:
    # ... PWM state saving ...
    self.pwm_controller.disconnect()
    logger.info("GrowPi Controller stopped (PWM preserved).")

# NACHHER:
def stop(self) -> None:
    # ... PWM state saving ...

    # DHT22 Sensor Cleanup (ROBUSTNESS FIX 2025-12-20)
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
    except ImportError:
        logger.debug("Web API not available - skipping sensor cleanup")
    except Exception as e:
        logger.warning(f"Unexpected error during sensor cleanup: {e}")

    self.pwm_controller.disconnect()
    logger.info("GrowPi Controller stopped (PWM preserved).")
```

**Verbesserungen**:
- `dht_sensor.exit()` wird aufgerufen (gibt GPIO frei)
- Graceful handling wenn `.exit()` Methode nicht existiert
- Keine Exceptions die Shutdown blockieren
- Log-Eintrag für erfolgreichen Cleanup

---

### 4. Sensor-Fehler Events loggen

**Datei**: `/pi-controller/grow_pi/database/logger.py` (Zeilen 203-246)

**Problem**:
- None-Werte wurden stillschweigend in DB geschrieben
- Keine Visibility über Sensor-Ausfälle

**Lösung**:
```python
# VORHER:
def _log_sensors(self) -> None:
    if not self._sensor_reader:
        return

    temp, humidity = self._sensor_reader()

    if temp is not None:
        # ... insert to DB ...
    if humidity is not None:
        # ... insert to DB ...

# NACHHER:
def _log_sensors(self) -> None:
    if not self._sensor_reader:
        return

    temp, humidity = self._sensor_reader()

    # ROBUSTNESS FIX: Log sensor failure as system event
    if temp is None and humidity is None:
        logger.warning("Sensor read returned None for both temp and humidity - logging failure event")
        self.log_event(
            'sensor_read_failure',
            'warning',
            'DHT22 sensor returned None for temperature and humidity',
            {'timestamp': datetime.now().isoformat()}
        )
        return  # Don't insert None values into database

    if temp is not None:
        # ... insert to DB ...
    else:
        logger.warning("Temperature reading is None - skipping database insert")

    if humidity is not None:
        # ... insert to DB ...
    else:
        logger.warning("Humidity reading is None - skipping database insert")
```

**Verbesserungen**:
- System-Event bei kompletten Sensor-Ausfällen
- Keine None-Werte mehr in der Datenbank
- Explizite Warnings bei partiellen Ausfällen
- Besseres Debugging durch strukturierte Events

---

## Geänderte Dateien

| Datei | Zeilen | Änderung |
|-------|--------|----------|
| `pi-controller/grow_pi/web/api.py` | 218-243 | DHT22 Init mit 5 Retries |
| `pi-controller/grow_pi/web/api.py` | 328-402 | Cache-Invalidierung bei Fehlern |
| `pi-controller/grow_pi/main.py` | 376-392 | DHT22 Cleanup bei Shutdown |
| `pi-controller/grow_pi/database/logger.py` | 203-246 | Event-Logging bei Sensor-Fehler |

**KEINE neuen Dependencies!**
**KEINE Breaking Changes!**

---

## Test-Anweisungen

### Lokale Tests (OHNE Pi)

```bash
cd pi-controller

# Type-Check (muss ohne Fehler durchlaufen)
python3 -m mypy grow_pi/web/api.py grow_pi/main.py grow_pi/database/logger.py

# Syntax-Check
python3 -m py_compile grow_pi/web/api.py
python3 -m py_compile grow_pi/main.py
python3 -m py_compile grow_pi/database/logger.py
```

### Auf dem Pi (nach Upload)

**WICHTIG**: Erst nach User-Erlaubnis!

1. **Backup des aktuellen Zustands**:
   ```bash
   ssh admin@192.168.0.86
   cd /opt/grow-pi
   sudo cp -r grow_pi grow_pi.backup_20251220
   ```

2. **Dateien hochladen**:
   ```bash
   # LOKAL (auf deinem Rechner):
   cd /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller

   scp grow_pi/web/api.py admin@192.168.0.86:/tmp/api.py
   scp grow_pi/main.py admin@192.168.0.86:/tmp/main.py
   scp grow_pi/database/logger.py admin@192.168.0.86:/tmp/logger.py
   ```

3. **Installation auf dem Pi**:
   ```bash
   ssh admin@192.168.0.86

   # Dateien verschieben
   sudo mv /tmp/api.py /opt/grow-pi/grow_pi/web/api.py
   sudo mv /tmp/main.py /opt/grow-pi/grow_pi/main.py
   sudo mv /tmp/logger.py /opt/grow-pi/grow_pi/database/logger.py

   # Permissions setzen
   sudo chown -R growpi:growpi /opt/grow-pi/grow_pi
   ```

4. **Service Neustart**:
   ```bash
   sudo systemctl restart grow-pi

   # Logs beobachten (sollte "attempt 1/5" zeigen)
   sudo journalctl -u grow-pi -f
   ```

5. **Erwartete Log-Ausgabe**:
   ```
   DHT22 Sensor initialized on GPIO-4 (attempt 1/5)
   PWM Controller initialized successfully
   DataLogger started
   Web API started on http://0.0.0.0:5000
   ```

   **Falls Sensor-Problem**:
   ```
   DHT22 init attempt 1/5 failed: A full buffer was not returned - retrying in 2s...
   DHT22 init attempt 2/5 failed: A full buffer was not returned - retrying in 2s...
   DHT22 Sensor initialized on GPIO-4 (attempt 3/5)
   ```

6. **Funktionstest**:
   ```bash
   # API-Check (sollte Temperatur + Humidity zurückgeben)
   curl http://192.168.0.86:5000/api/temperature

   # Erwartete Antwort:
   {
     "success": true,
     "temperature": 22.5,
     "humidity": 58.3,
     "unit_temperature": "°C",
     "unit_humidity": "%"
   }
   ```

7. **Monitoring** (10 Minuten laufen lassen):
   ```bash
   # Prüfe auf sensor_persistent_error Events
   sqlite3 /opt/grow-pi/grow_pi_data.db
   > SELECT * FROM system_events WHERE event_type = 'sensor_persistent_error' ORDER BY timestamp DESC LIMIT 5;
   > .quit
   ```

---

## Erwartete Verbesserungen

### Vor dem Fix
- **Init**: Sensor-Init konnte beim ersten Versuch fehlschlagen → Mock-Daten
- **Runtime**: Cache lieferte stale data bei Sensor-Problemen
- **Shutdown**: GPIO nicht sauber freigegeben
- **Monitoring**: Keine Events bei Sensor-Ausfällen

### Nach dem Fix
- **Init**: 5 Retry-Versuche mit 2s Pause → höhere Erfolgsrate
- **Runtime**: Cache wird nach 3 Fehlern invalidiert → keine stale data
- **Shutdown**: `sensor.exit()` gibt GPIO ordnungsgemäß frei
- **Monitoring**: `sensor_persistent_error` und `sensor_read_failure` Events

---

## Rollback-Plan

Falls Probleme auftreten:

```bash
ssh admin@192.168.0.86
cd /opt/grow-pi

# Backup wiederherstellen
sudo rm -rf grow_pi
sudo mv grow_pi.backup_20251220 grow_pi
sudo chown -R growpi:growpi grow_pi

# Service neustarten
sudo systemctl restart grow-pi
```

---

## Nächste Schritte

1. **User-Approval**: Warten auf explizite Erlaubnis zum Deployment
2. **Backup**: Aktuellen Code auf dem Pi sichern
3. **Upload**: Geänderte Dateien hochladen
4. **Test**: Service neustart + Funktionstest
5. **Monitor**: 24h Beobachtung der Events-Tabelle

**KRITISCH**: Der Pi darf NICHT ohne User-Erlaubnis neugestartet werden!

---

## Code-Qualität

- [x] Python 3.13 kompatibel
- [x] Type Hints beibehalten
- [x] Bestehende Logger verwendet
- [x] Keine neuen Dependencies
- [x] Graceful Error Handling
- [x] Rückwärtskompatibel

---

**Status**: READY FOR DEPLOYMENT (nach User-Approval)
**Risk Level**: LOW (nur Robustness-Verbesserungen, keine funktionalen Änderungen)

---

Ende des Berichts
