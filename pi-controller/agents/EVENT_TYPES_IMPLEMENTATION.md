# Event Types Implementation Report

**Agent:** @builder
**Datum:** 2025-12-20
**Task:** Fehlende Event-Types in DB-Schema implementieren
**Status:** ABGESCHLOSSEN

---

## Problem-Analyse

### Fehlende Event-Types

Der Code versuchte folgende Event-Types zu loggen, die nicht im Schema existierten:

1. `sensor_read_failure` (logger.py:219)
2. `sensor_persistent_error` (api.py:390)

### Root Cause

In `grow_pi/database/models.py` Zeile 134-139 war die `VALID_EVENT_TYPES` Set-Definition unvollständig:

**VORHER:**
```python
VALID_EVENT_TYPES = {
    'service_start', 'service_stop', 'config_change',
    'sensor_error', 'pwm_error', 'database_error',
    'sync_start', 'sync_complete', 'sync_error',
    'lamp_change', 'curve_update'
}
```

### Verwendungs-Kontext

#### 1. sensor_read_failure
**Datei:** `grow_pi/database/logger.py:218-223`

```python
self.log_event(
    'sensor_read_failure',
    'warning',
    'DHT22 sensor returned None for temperature and humidity',
    {'timestamp': datetime.now().isoformat()}
)
```

**Use Case:** Wird geloggt wenn DHT22 Sensor für beide Werte (Temperatur + Humidity) None zurückgibt. Severity: `warning`

#### 2. sensor_persistent_error
**Datei:** `grow_pi/web/api.py:389-394`

```python
data_logger.log_event(
    'sensor_persistent_error',
    'error',
    f'DHT22 failed {_dht_cache["error_count"]} consecutive reads',
    {'error_count': _dht_cache["error_count"]}
)
```

**Use Case:** Wird geloggt wenn DHT22 Sensor X-mal hintereinander fehlschlägt (DHT_MAX_CONSECUTIVE_ERRORS). Severity: `error`

---

## Implementierung

### Code-Änderung

**Datei:** `grow_pi/database/models.py`
**Zeilen:** 134-140

**NACHHER:**
```python
# Gültige Event-Typen
VALID_EVENT_TYPES = {
    'service_start', 'service_stop', 'config_change',
    'sensor_error', 'sensor_read_failure', 'sensor_persistent_error',
    'pwm_error', 'database_error',
    'sync_start', 'sync_complete', 'sync_error',
    'lamp_change', 'curve_update'
}
```

### Änderungen im Detail

- `sensor_read_failure` hinzugefügt (einzelner Lesefehler)
- `sensor_persistent_error` hinzugefügt (wiederholte Fehler)
- Gruppierung angepasst: Sensor-bezogene Events zusammen

### Validierung

1. **Syntax-Check:**
   ```bash
   python3 -m py_compile grow_pi/database/models.py
   # Exit Code: 0 (Success)
   ```

2. **Konsistenz-Check:**
   - Alle verwendeten Event-Types sind jetzt in VALID_EVENT_TYPES
   - Keine Migration nötig (SQLite verwendet VARCHAR, kein ENUM)

---

## DB-Schema Analyse

### Tabellenstruktur

**Tabelle:** `system_events` (db.py:59-66)

```sql
CREATE TABLE IF NOT EXISTS system_events (
    id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    details TEXT,
    created_at TEXT NOT NULL
);
```

**Index:** `idx_system_events_type_time` auf `(event_type, created_at DESC)`

### Validierungs-Mechanismus

**Code-Level Validation** (models.py:146-149):

```python
def __post_init__(self):
    """Validate event_type and severity."""
    if self.event_type not in self.VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type: {self.event_type}")
    if self.severity not in self.VALID_SEVERITIES:
        raise ValueError(f"Invalid severity: {self.severity}")
```

### Migration Status

**Keine DB-Migration erforderlich** weil:
- SQLite verwendet `TEXT NOT NULL` für `event_type` (kein ENUM)
- Validierung erfolgt auf Code-Level (Python Dataclass)
- Bestehende Datenbank bleibt kompatibel

---

## Betroffene Dateien

### Geänderte Dateien

| Datei | Änderung | Lines |
|-------|----------|-------|
| `grow_pi/database/models.py` | Event-Types erweitert | 134-140 |

### Consumer-Dateien (keine Änderung nötig)

| Datei | Event-Type | Severity | Kontext |
|-------|-----------|----------|---------|
| `grow_pi/database/logger.py` | `sensor_read_failure` | warning | DHT22 returniert None |
| `grow_pi/web/api.py` | `sensor_persistent_error` | error | Wiederholte DHT22 Fehler |

---

## Testing

### Manuelle Tests

**Test 1: SystemEvent Instanzierung**
```python
from grow_pi.database.models import SystemEvent

# Sollte erfolgreich sein
event1 = SystemEvent(
    event_type='sensor_read_failure',
    severity='warning',
    message='Test sensor failure'
)

event2 = SystemEvent(
    event_type='sensor_persistent_error',
    severity='error',
    message='Test persistent error'
)
```

**Test 2: Validierung (negative test)**
```python
# Sollte ValueError werfen
try:
    event3 = SystemEvent(
        event_type='invalid_type',
        severity='warning',
        message='Should fail'
    )
except ValueError as e:
    print(f"Expected error: {e}")
    # "Invalid event_type: invalid_type"
```

### Integration Tests (empfohlen nach Deployment)

1. **Sensor Read Failure Test:**
   - DHT22 disconnecten
   - Warten bis DataLogger lauft
   - Prüfen: `system_events` Tabelle enthält `sensor_read_failure` Event

2. **Persistent Error Test:**
   - DHT22 disconnecten
   - Warten bis DHT_MAX_CONSECUTIVE_ERRORS erreicht
   - Prüfen: `system_events` Tabelle enthält `sensor_persistent_error` Event

---

## Vollständige Event-Type Registry

Nach der Änderung unterstützt das System folgende Event-Types:

| Event Type | Category | Use Case |
|------------|----------|----------|
| `service_start` | Lifecycle | Service gestartet |
| `service_stop` | Lifecycle | Service gestoppt |
| `config_change` | Config | Konfigurationsänderung |
| `sensor_error` | Sensor | Allgemeiner Sensor-Fehler |
| `sensor_read_failure` | Sensor | Einzelner Lesefehler (None) |
| `sensor_persistent_error` | Sensor | Wiederholte Lesefehler |
| `pwm_error` | Hardware | PWM-Controller Fehler |
| `database_error` | Database | Datenbankfehler |
| `sync_start` | Sync | Synchronisation gestartet |
| `sync_complete` | Sync | Synchronisation erfolgreich |
| `sync_error` | Sync | Synchronisationsfehler |
| `lamp_change` | Lighting | Lampenzustand geändert |
| `curve_update` | Lighting | Lichtkurve aktualisiert |

---

## Deployment-Hinweise

### Kein DB-Restart erforderlich

Da die Validierung auf Code-Level erfolgt, ist **kein Neustart des Raspberry Pi** nötig.

### Deployment-Workflow

1. Code-Datei aktualisieren:
   ```bash
   scp grow_pi/database/models.py admin@192.168.0.86:/opt/grow-pi/grow_pi/database/
   ```

2. Service neu starten (für Code-Reload):
   ```bash
   ssh admin@192.168.0.86
   sudo systemctl restart grow-pi
   ```

3. Logs überwachen:
   ```bash
   sudo journalctl -u grow-pi -f
   ```

### Rollback-Plan

Falls Probleme auftreten:

```bash
# Alte Version wiederherstellen
git checkout HEAD~1 grow_pi/database/models.py

# Service restart
sudo systemctl restart grow-pi
```

---

## Code-Qualität

### Style-Compliance

- PEP 8 konform
- Bestehende Code-Patterns beibehalten
- Alphabetische Gruppierung nach Kategorie

### Type Safety

- Alle Event-Types als String-Literals im Set
- Runtime-Validation via `__post_init__`
- Keine Type-Hints nötig (Python Set[str] implizit)

### Backwards Compatibility

- Alle existierenden Event-Types unverändert
- Nur Erweiterung (keine Breaking Changes)
- DB-Schema kompatibel

---

## Lessons Learned

### Best Practices

1. Event-Types IMMER in VALID_EVENT_TYPES definieren BEVOR sie verwendet werden
2. Consumer-Code-Search vor Implementation durchführen
3. Code-Level Validation für dynamische Enums (statt DB-Constraints)

### Future Improvements

**Empfehlung:** EventType-Registry in separater Config-Datei

```python
# grow_pi/database/event_types.py
class EventType:
    # Lifecycle
    SERVICE_START = 'service_start'
    SERVICE_STOP = 'service_stop'

    # Sensors
    SENSOR_ERROR = 'sensor_error'
    SENSOR_READ_FAILURE = 'sensor_read_failure'
    SENSOR_PERSISTENT_ERROR = 'sensor_persistent_error'

    # ...

    @classmethod
    def all_types(cls):
        return {
            cls.SERVICE_START, cls.SERVICE_STOP,
            cls.SENSOR_ERROR, cls.SENSOR_READ_FAILURE,
            cls.SENSOR_PERSISTENT_ERROR,
            # ...
        }
```

**Vorteile:**
- Autocomplete in IDE
- Typ-sichere Referenzen
- Zentrale Dokumentation

---

## Checklist

- [x] Event-Types in VALID_EVENT_TYPES hinzugefügt
- [x] Syntax-Check durchgeführt (py_compile)
- [x] Consumer-Code identifiziert
- [x] DB-Schema analysiert
- [x] Keine Migration erforderlich
- [x] Deployment-Plan dokumentiert
- [x] Bericht erstellt

---

## Zusammenfassung

**Problem:** 2 fehlende Event-Types (`sensor_read_failure`, `sensor_persistent_error`) blockierten Event-Logging

**Lösung:** Event-Types zu `VALID_EVENT_TYPES` Set in `models.py` hinzugefügt

**Impact:**
- Sensor-Fehler werden jetzt korrekt geloggt
- Monitoring von DHT22-Ausfällen funktioniert
- Keine Breaking Changes

**Deployment:**
- Nur Code-Update nötig
- Kein DB-Restart erforderlich
- Service-Restart für Code-Reload empfohlen

**Status:** Bereit für Deployment nach User-Genehmigung
