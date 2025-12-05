# GrowPi Local Database Specification

**Version**: 1.0
**Erstellt**: 2025-12-05
**Status**: Design-Phase

---

## 1. Übersicht

### 1.1 Zweck

Das lokale Logging-System auf dem Raspberry Pi dient zwei Hauptzwecken:

1. **Offline-Betrieb**: Daten werden lokal gespeichert, auch wenn keine Internetverbindung besteht
2. **Synchronisation**: Daten können später zum zentralen Server hochgeladen werden

### 1.2 Design-Prinzipien

| Prinzip | Begründung |
|---------|------------|
| **SQLite** | Leichtgewichtig, keine Server-Installation, einzelne Datei |
| **Schema-Kompatibilität** | Identische Tabellenstruktur wie PostgreSQL-Server |
| **UUID als Primary Key** | Ermöglicht konfliktfreie Synchronisation |
| **Timestamp-basiert** | Alle Einträge haben `created_at` für Zeitreihen-Abfragen |
| **Soft-Delete** | `synced_at` Feld statt harter Löschung nach Sync |

### 1.3 Datenfluss

```
┌─────────────────────────────────────────────────────────────────┐
│                     Raspberry Pi (Lokal)                         │
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  DHT22       │    │  PWM         │    │  Sun Curve       │  │
│  │  Sensor      │    │  Controller  │    │  Interpolation   │  │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘  │
│         │                   │                     │             │
│         ▼                   ▼                     ▼             │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   DataLogger Service                        ││
│  │  - Sammelt Sensor-Daten (alle 60s)                         ││
│  │  - Sammelt Lampen-Status (bei Änderung + alle 60s)         ││
│  │  - Schreibt in SQLite                                       ││
│  └─────────────────────────────────────────────────────────────┘│
│                              │                                   │
│                              ▼                                   │
│                   ┌──────────────────┐                          │
│                   │   SQLite DB      │                          │
│                   │   /opt/grow-pi/  │                          │
│                   │   data/growpi.db │                          │
│                   └──────────────────┘                          │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               │ (Zukünftig: Sync via API)
                               ▼
                   ┌──────────────────┐
                   │   PostgreSQL     │
                   │   (VPS Server)   │
                   └──────────────────┘
```

---

## 2. Datenbank-Schema

### 2.1 Entity-Relationship Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         LOCAL DATABASE                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────────────────────┐ │
│  │ sensor_readings  │         │ lamp_state_log                    │ │
│  ├──────────────────┤         ├──────────────────────────────────┤ │
│  │ id (UUID) PK     │         │ id (UUID) PK                     │ │
│  │ sensor_type      │         │ channel (INT)                    │ │
│  │ value (FLOAT)    │         │ intensity (INT)                  │ │
│  │ created_at       │         │ source (TEXT)                    │ │
│  │ synced_at        │         │ created_at                       │ │
│  └──────────────────┘         │ synced_at                        │ │
│                               └──────────────────────────────────┘ │
│                                                                      │
│  ┌──────────────────┐         ┌──────────────────────────────────┐ │
│  │ system_events    │         │ sync_status                       │ │
│  ├──────────────────┤         ├──────────────────────────────────┤ │
│  │ id (UUID) PK     │         │ id (INT) PK                      │ │
│  │ event_type       │         │ last_sync (DATETIME)             │ │
│  │ message          │         │ readings_synced (INT)            │ │
│  │ details (JSON)   │         │ lamp_logs_synced (INT)           │ │
│  │ created_at       │         │ status (TEXT)                    │ │
│  └──────────────────┘         └──────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.2 Tabellen-Definitionen

#### 2.2.1 `sensor_readings` - Sensor-Messwerte

Speichert alle Sensor-Messungen (Temperatur, Luftfeuchtigkeit, zukünftig Bodensensoren).

```sql
CREATE TABLE sensor_readings (
    id TEXT PRIMARY KEY,              -- UUID v4
    sensor_type TEXT NOT NULL,        -- 'temperature', 'humidity', 'soil_moisture', etc.
    value REAL NOT NULL,              -- Messwert
    unit TEXT NOT NULL,               -- '°C', '%', 'pH', etc.
    created_at TEXT NOT NULL,         -- ISO 8601 Timestamp
    synced_at TEXT DEFAULT NULL       -- NULL = nicht synchronisiert
);

-- Index für Zeitreihen-Abfragen
CREATE INDEX idx_sensor_readings_type_time
ON sensor_readings(sensor_type, created_at DESC);

-- Index für Sync-Abfragen
CREATE INDEX idx_sensor_readings_synced
ON sensor_readings(synced_at) WHERE synced_at IS NULL;
```

**Sensor-Typen (kompatibel mit Server-Schema):**
| sensor_type | unit | Beschreibung |
|-------------|------|--------------|
| `temperature` | `°C` | Lufttemperatur (DHT22) |
| `humidity` | `%` | Luftfeuchtigkeit (DHT22) |
| `soil_moisture` | `%` | Bodenfeuchtigkeit (RS485) |
| `soil_temp` | `°C` | Bodentemperatur (RS485) |
| `soil_ph` | `pH` | Boden-pH-Wert (RS485) |
| `soil_ec` | `mS/cm` | Elektrische Leitfähigkeit (RS485) |
| `soil_n` | `mg/kg` | Stickstoff (RS485) |
| `soil_p` | `mg/kg` | Phosphor (RS485) |
| `soil_k` | `mg/kg` | Kalium (RS485) |

#### 2.2.2 `lamp_state_log` - Lampen-Zustandsprotokoll

Protokolliert jeden Lampenzustand mit Zeitstempel. Kritisch für die Analyse der Lichtzyklen.

```sql
CREATE TABLE lamp_state_log (
    id TEXT PRIMARY KEY,              -- UUID v4
    channel INTEGER NOT NULL,         -- Kanal 1-4
    name TEXT NOT NULL,               -- 'Far Red', 'Warm White', etc.
    intensity INTEGER NOT NULL,       -- 0-100%
    source TEXT NOT NULL,             -- 'curve', 'manual', 'api', 'override'
    curve_time TEXT,                  -- Geplante Zeit aus Kurve (falls source='curve')
    created_at TEXT NOT NULL,         -- ISO 8601 Timestamp
    synced_at TEXT DEFAULT NULL       -- NULL = nicht synchronisiert
);

-- Index für Zeitreihen-Abfragen pro Kanal
CREATE INDEX idx_lamp_state_channel_time
ON lamp_state_log(channel, created_at DESC);

-- Index für Sync-Abfragen
CREATE INDEX idx_lamp_state_synced
ON lamp_state_log(synced_at) WHERE synced_at IS NULL;
```

**Source-Typen:**
| source | Beschreibung |
|--------|--------------|
| `curve` | Automatisch von Sonnenkurven-Interpolation |
| `manual` | Manuell über Web-Interface Slider |
| `api` | Über REST-API gesetzt |
| `override` | All-On/All-Off Override |
| `startup` | Initialer Wert beim Service-Start |
| `shutdown` | Wert beim Service-Stop (immer 0) |

#### 2.2.3 `system_events` - System-Ereignisse

Protokolliert wichtige Systemereignisse für Debugging und Audit.

```sql
CREATE TABLE system_events (
    id TEXT PRIMARY KEY,              -- UUID v4
    event_type TEXT NOT NULL,         -- 'service_start', 'error', 'config_change', etc.
    severity TEXT NOT NULL,           -- 'info', 'warning', 'error', 'critical'
    message TEXT NOT NULL,            -- Kurze Beschreibung
    details TEXT,                     -- JSON mit zusätzlichen Details
    created_at TEXT NOT NULL          -- ISO 8601 Timestamp
);

-- Index für Event-Typ Abfragen
CREATE INDEX idx_system_events_type_time
ON system_events(event_type, created_at DESC);

-- Index für Severity-Filter
CREATE INDEX idx_system_events_severity
ON system_events(severity, created_at DESC);
```

**Event-Typen:**
| event_type | Beschreibung |
|------------|--------------|
| `service_start` | Service wurde gestartet |
| `service_stop` | Service wurde gestoppt |
| `config_change` | Konfiguration wurde geändert |
| `sensor_error` | Sensor-Lesefehler |
| `pwm_error` | PWM-Controller Fehler |
| `sync_start` | Synchronisation gestartet |
| `sync_complete` | Synchronisation erfolgreich |
| `sync_error` | Synchronisation fehlgeschlagen |

#### 2.2.4 `sync_status` - Synchronisations-Status

Einzelne Zeile, die den aktuellen Sync-Status speichert.

```sql
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY CHECK (id = 1),  -- Nur eine Zeile erlaubt
    last_sync TEXT,                          -- Letzter erfolgreicher Sync
    last_attempt TEXT,                       -- Letzter Sync-Versuch
    readings_pending INTEGER DEFAULT 0,      -- Unsynced sensor_readings
    lamp_logs_pending INTEGER DEFAULT 0,     -- Unsynced lamp_state_log
    status TEXT DEFAULT 'never',             -- 'never', 'syncing', 'success', 'error'
    error_message TEXT                       -- Letzte Fehlermeldung
);

-- Initialer Datensatz
INSERT INTO sync_status (id, status) VALUES (1, 'never');
```

---

## 3. Logging-Strategie

### 3.1 Sensor-Logging

```
┌─────────────────────────────────────────────────────────────────┐
│                    Sensor Logging Flow                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   DHT22 Sensor                                                   │
│        │                                                         │
│        ▼                                                         │
│   ┌─────────────────┐                                           │
│   │ Alle 60 Sekunden│◄──── Konfigurierbar via config.yaml       │
│   └────────┬────────┘                                           │
│            │                                                     │
│            ▼                                                     │
│   ┌─────────────────┐     ┌─────────────────┐                   │
│   │ read_dht22()    │────►│ Temperatur      │                   │
│   │ (mit Retry)     │     │ + Humidity      │                   │
│   └─────────────────┘     └────────┬────────┘                   │
│                                    │                             │
│                                    ▼                             │
│                           ┌─────────────────┐                   │
│                           │ log_sensor_     │                   │
│                           │ reading()       │                   │
│                           └────────┬────────┘                   │
│                                    │                             │
│                                    ▼                             │
│                           ┌─────────────────┐                   │
│                           │ INSERT INTO     │                   │
│                           │ sensor_readings │                   │
│                           └─────────────────┘                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Logging-Intervall**: 60 Sekunden (Standard)
- Ergibt: 1.440 Einträge/Tag pro Sensor-Typ
- Bei 2 Sensor-Typen (temp + humidity): 2.880 Einträge/Tag
- Pro Monat: ~86.400 Einträge

### 3.2 Lampen-Logging

```
┌─────────────────────────────────────────────────────────────────┐
│                    Lamp State Logging Flow                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   Logging erfolgt bei:                                           │
│                                                                  │
│   1. PERIODISCH (alle 60s)                                      │
│      └─► Aktueller Zustand aller Kanäle                         │
│                                                                  │
│   2. BEI ÄNDERUNG                                               │
│      ├─► Kurven-Interpolation berechnet neuen Wert              │
│      ├─► Manueller Slider-Change                                │
│      ├─► API-Request                                            │
│      └─► Override (All On/Off)                                  │
│                                                                  │
│   3. SYSTEM-EVENTS                                              │
│      ├─► Service Start (source='startup')                       │
│      └─► Service Stop (source='shutdown', intensity=0)          │
│                                                                  │
│   ┌─────────────────────────────────────────────────────────────┐│
│   │                    Deduplizierung                           ││
│   │                                                             ││
│   │   NICHT loggen wenn:                                        ││
│   │   - Letzter Log < 5s her UND                               ││
│   │   - Gleicher Kanal UND                                      ││
│   │   - Gleiche Intensität                                      ││
│   │                                                             ││
│   │   → Verhindert Spam bei schnellen Slider-Bewegungen         ││
│   └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Erwartete Log-Einträge pro Tag:**
- Periodisch: 1.440 × 4 Kanäle = 5.760 Einträge
- Änderungen (Kurve): ~8-12 pro Kanal = ~40 Einträge
- Manuell: variabel, typisch 0-50 Einträge
- **Gesamt**: ~6.000 Einträge/Tag

### 3.3 Speicherplatz-Kalkulation

| Zeitraum | sensor_readings | lamp_state_log | Gesamt |
|----------|-----------------|----------------|--------|
| 1 Tag | ~200 KB | ~400 KB | ~600 KB |
| 1 Woche | ~1.4 MB | ~2.8 MB | ~4.2 MB |
| 1 Monat | ~6 MB | ~12 MB | ~18 MB |
| 1 Jahr | ~72 MB | ~144 MB | ~216 MB |

**Empfehlung**: Daten älter als 30 Tage automatisch löschen (oder nach Sync archivieren).

---

## 4. Datenbank-Rotation

### 4.1 Retention Policy

```python
# Standardmäßige Aufbewahrungsfristen
RETENTION_POLICY = {
    'sensor_readings': 30,      # Tage
    'lamp_state_log': 30,       # Tage
    'system_events': 90,        # Tage (länger für Debugging)
}
```

### 4.2 Cleanup-Job

```sql
-- Täglicher Cleanup (via Scheduler)
DELETE FROM sensor_readings
WHERE created_at < datetime('now', '-30 days')
  AND synced_at IS NOT NULL;

DELETE FROM lamp_state_log
WHERE created_at < datetime('now', '-30 days')
  AND synced_at IS NOT NULL;

DELETE FROM system_events
WHERE created_at < datetime('now', '-90 days');

-- Datenbank optimieren nach Löschung
VACUUM;
```

---

## 5. API für Daten-Abfrage

### 5.1 Neue Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/logs/sensors` | GET | Sensor-Daten mit Zeitfilter |
| `/api/logs/lamps` | GET | Lampen-Log mit Zeitfilter |
| `/api/logs/events` | GET | System-Events |
| `/api/logs/stats` | GET | Zusammenfassung/Statistiken |

### 5.2 Query-Parameter

```
GET /api/logs/sensors?type=temperature&from=2025-12-05T00:00:00&to=2025-12-05T23:59:59&limit=1000

GET /api/logs/lamps?channel=1&from=2025-12-05T00:00:00&to=2025-12-05T23:59:59

GET /api/logs/stats?date=2025-12-05
```

### 5.3 Response-Format

```json
{
  "success": true,
  "data": {
    "sensor_readings": [
      {
        "id": "uuid",
        "sensor_type": "temperature",
        "value": 22.5,
        "unit": "°C",
        "created_at": "2025-12-05T14:30:00"
      }
    ]
  },
  "meta": {
    "total": 1440,
    "returned": 100,
    "from": "2025-12-05T00:00:00",
    "to": "2025-12-05T23:59:59"
  }
}
```

---

## 6. Synchronisation mit Server (Zukünftig)

### 6.1 Sync-Strategie

```
┌─────────────────────────────────────────────────────────────────┐
│                      Sync Flow (Zukünftig)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   1. Pi prüft alle 5 Minuten auf Internet-Verbindung            │
│                                                                  │
│   2. Falls online:                                               │
│      a) SELECT * FROM sensor_readings WHERE synced_at IS NULL   │
│      b) SELECT * FROM lamp_state_log WHERE synced_at IS NULL    │
│      c) Batch-Upload zum Server (max 1000 pro Request)          │
│      d) Bei Erfolg: UPDATE SET synced_at = NOW()                │
│                                                                  │
│   3. Server-Tabellen:                                            │
│      - sensor_readings (identisches Schema + zone_id)           │
│      - lamp_state_log (identisches Schema + zone_id)            │
│                                                                  │
│   4. Konflikt-Handling:                                          │
│      - UUID garantiert Eindeutigkeit                            │
│      - Server akzeptiert nur neue IDs (INSERT OR IGNORE)        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Server-Schema Erweiterung

```sql
-- Auf PostgreSQL-Server hinzufügen:

-- Erweiterung von sensor_readings
ALTER TABLE sensor_readings ADD COLUMN pi_id TEXT;
ALTER TABLE sensor_readings ADD COLUMN pi_created_at TIMESTAMPTZ;

-- Neue Tabelle für Lampen-Logs
CREATE TABLE lamp_state_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
    channel INTEGER NOT NULL,
    name TEXT NOT NULL,
    intensity INTEGER NOT NULL,
    source TEXT NOT NULL,
    curve_time TEXT,
    pi_id TEXT,                    -- Original-UUID vom Pi
    pi_created_at TIMESTAMPTZ,     -- Original-Timestamp vom Pi
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_lamp_state_log_zone_time
ON lamp_state_log(zone_id, created_at DESC);
```

---

## 7. Datei-Struktur

```
/opt/grow-pi/
├── data/
│   └── growpi.db              # SQLite Datenbank
├── grow_pi/
│   ├── database/
│   │   ├── __init__.py
│   │   ├── models.py          # Dataclasses für DB-Einträge
│   │   ├── db.py              # SQLite Connection Manager
│   │   └── logger.py          # DataLogger Service
│   └── ...
└── config/
    └── config.yaml            # Logging-Intervalle etc.
```

---

## 8. Konfiguration

### 8.1 config.yaml Erweiterung

```yaml
# Logging Configuration
logging:
  level: "INFO"

  # Datenbank
  database:
    path: "/opt/grow-pi/data/growpi.db"

  # Sensor-Logging
  sensors:
    interval: 60              # Sekunden zwischen Messungen
    retry_count: 3            # Wiederholungen bei Fehler

  # Lampen-Logging
  lamps:
    interval: 60              # Periodisches Logging (Sekunden)
    log_on_change: true       # Bei jeder Änderung loggen
    dedupe_seconds: 5         # Min. Zeit zwischen gleichen Logs

  # Datenbereinigung
  retention:
    sensor_readings_days: 30
    lamp_state_log_days: 30
    system_events_days: 90
    cleanup_hour: 3           # Uhrzeit für täglichen Cleanup (03:00)
```

---

## 9. Migrations-Pfad

### 9.1 Von Lokal zu Online

1. **Phase 1 (Jetzt)**: Lokales SQLite-Logging
   - Alle Daten werden lokal gespeichert
   - Web-Interface zeigt lokale Daten an

2. **Phase 2 (Später)**: Sync-Mechanismus
   - Pi sendet Daten an Server
   - Server aggregiert Daten von mehreren Pis

3. **Phase 3 (Produktion)**: Vollständige Integration
   - Dashboard zeigt Server-Daten
   - Historische Auswertungen
   - Multi-Zone Support

### 9.2 Schema-Kompatibilität

Die lokalen Tabellen verwenden identische Feldnamen wie das Server-Schema:
- `sensor_readings` → entspricht `SensorReading` Model
- `lamp_state_log` → neue Tabelle (muss auf Server erstellt werden)

---

## 10. Zusammenfassung

| Aspekt | Entscheidung | Begründung |
|--------|--------------|------------|
| **Datenbank** | SQLite | Leichtgewichtig, keine Installation, Single-File |
| **Primary Keys** | UUID v4 | Konfliktfreie Synchronisation |
| **Timestamps** | ISO 8601 Text | Portabel, lesbar, sortierbar |
| **Sync-Marker** | `synced_at` | NULL = pending, Timestamp = synced |
| **Logging-Trigger** | Interval + Change | Vollständige Historie + Effizienz |
| **Retention** | 30 Tage | Balance zwischen Historie und Speicher |

---

**Nächste Schritte:**
1. ✅ Schema-Design (dieses Dokument)
2. ⏳ Implementierung `database/` Module
3. ⏳ Integration in Web-API
4. ⏳ Test mit echten Daten
5. ⏳ API-Endpoints für Abfragen

---

**Autor**: Claude Code
**Letzte Aktualisierung**: 2025-12-05
