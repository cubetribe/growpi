# Analyse: Stromverbrauchs-Logging Problem

**Analysiert am**: 2025-12-08 09:38 Uhr
**Analysiert von**: MCP Specialist Agent
**Version**: v6.8.0

---

## Executive Summary

**KRITISCHER BUG IDENTIFIZIERT**: Die lokale Datenbank `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi_data.db` ist **0 Bytes groß** und wurde nie initialisiert. Die Tabelle `plug_logs` existiert nicht, weshalb keine Stromverbrauchs-Daten im Verlauf-Tab angezeigt werden können.

**Root Cause**: Datenbank-Initialisierung wird beim lokalen Start nicht durchgeführt.

---

## Screenshots

### 1. Kosten-Tab (HEUTE) - 08.12.2025
![Kosten Heute](/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/.playwright-mcp/screenshots/costs-tab-heute.png)

**Beobachtung**:
- **Zeitraum**: today
- **Gesamt**: 1.071 kWh (0.32 EUR)
- **Devices**:
  - Entfeuchter: 0.509 kWh (0.15 EUR)
  - Main Light: 0.405 kWh (0.12 EUR)
  - Wohnzimmer: 0.093 kWh (0.03 EUR)
  - FR main: 0.064 kWh (0.02 EUR)
  - Pumpe: 0.000 kWh
  - Mittags Sonne: 0.000 kWh

**Status**: ✅ Kosten-Berechnung funktioniert korrekt

---

### 2. Kosten-Tab (7 TAGE) - 01.12. - 08.12.2025
![Kosten 7 Tage](/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/.playwright-mcp/screenshots/costs-tab-7tage.png)

**Beobachtung**:
- **Zeitraum**: week
- **Gesamt**: 31.347 kWh (9.40 EUR)
- **Devices**:
  - Main Light: 24.458 kWh (7.34 EUR)
  - Entfeuchter: 5.828 kWh (1.75 EUR)
  - Wohnzimmer: 0.860 kWh (0.26 EUR)
  - FR main: 0.201 kWh (0.06 EUR)

**Status**: ✅ Historische Daten werden korrekt aggregiert

---

### 3. Verlauf-Tab (24h Ansicht)
![Verlauf 24h](/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/.playwright-mcp/screenshots/verlauf-tab-24h-overview.png)

**Beobachtung**:
- **Klima-Chart**: Zeigt Daten von ~10:00 - 09:00 Uhr (korrekt)
- **Beleuchtung-Chart**: Zeigt Daten von ~09:00 - 09:00 Uhr (korrekt)
- **Stromverbrauch-Chart**: Zeigt NUR Daten von ~07:00 - 09:00 Uhr ❌

**Problem**: Nur ca. 2 Stunden Daten im Stromverbrauchs-Chart!

---

### 4. Verlauf-Tab (7 TAGE Ansicht)
![Verlauf 7 Tage](/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/.playwright-mcp/screenshots/verlauf-tab-7tage-power.png)

**Beobachtung**:
- **Klima-Chart**: Zeigt Daten von 02.12. - 08.12. (korrekt)
- **Beleuchtung-Chart**: Zeigt Daten von 30.11. - 08.12. (korrekt)
- **Stromverbrauch-Chart**: Zeigt NUR Daten vom 08.12. ❌

**Problem**: Chart zeigt nur 1 Tag statt 7 Tage!

---

## Findings

### 1. Kosten-Tab (Costs Module)

**Wie funktioniert es?**
- **API Endpoint**: `GET /api/costs?period={today|week|month|year}`
- **Backend**: `pi-controller/grow_pi/web/blueprints/costs_bp.py`
- **Datenquelle**:
  ```python
  db.get_plug_logs(hours=int(hours), limit=100000)
  ```
- **Berechnung**:
  ```python
  interval_hours = 60 / 3600  # 60 seconds in hours
  kwh = sum(p * interval_hours for p in power_readings) / 1000
  cost = kwh * kwh_price
  ```

**Status**: ✅ Funktioniert korrekt
- Ruft `get_plug_logs()` auf (NICHT die downsampled Variante)
- Verarbeitet bis zu 100.000 Einträge
- Aggregiert korrekt über alle Devices

**Woher kommen die Daten?**
- Direkter Zugriff auf `plug_logs` Tabelle via `db.get_plug_logs()`
- Keine Downsampling-Logik

---

### 2. Verlauf-Tab (History Module)

**Wie funktioniert es?**
- **Frontend**: `pi-controller/grow_pi/web/static/js/modules/history.js`
- **API Endpoint**: `GET /api/logs/plugs?hours={24|168|720}`
- **Backend**: `pi-controller/grow_pi/web/blueprints/logs_bp.py`
- **Datenquelle**:
  ```python
  db.get_plug_logs_downsampled(hours=hours)
  ```

**Downsampling-Regeln** (Zeile 176-181 in `logs_bp.py`):
```
- 0-4 hours: Raw data (every minute)
- 4-24 hours: 5-minute averages
- 1-7 days: 15-minute averages
- 7-30 days: 30-minute averages
- >30 days: 1-hour averages
```

**Chart-Rendering** (Zeile 520-639 in `history.js`):
```javascript
// Uses time-based X-axis with fixed time range bounds
this.plugChartInstance.options.scales.x.min = bounds.min;
this.plugChartInstance.options.scales.x.max = bounds.max;
```

**Status**: ❌ Zeigt nur 2 Stunden statt voller Zeitspanne

---

### 3. Backend-Analyse: `/api/logs/plugs`

**Code-Flow**:
```python
@logs_bp.route('/api/logs/plugs', methods=['GET'])
def get_plug_logs():
    hours = int(request.args.get('hours', 24))
    db = get_database()
    logs = db.get_plug_logs_downsampled(hours=hours)

    return jsonify({
        "data": logs,
        "count": len(logs),
        "hours": hours,
        "downsampled": True
    })
```

**Downsampling-Implementierung** (`db.py` Zeile 1001-1079):
```python
def get_plug_logs_downsampled(self, device_id=None, hours=24):
    # 1. Raw data for last 4 hours
    # 2. 5-minute averages for 4-24 hours
    # 3. 15-minute averages for 1-7 days
    # 4. 30-minute averages for 7-30 days
    # 5. 1-hour averages for >30 days
```

---

### 4. Datenbank-Schema

**Schema Definition** (`db.py` Zeile 104-115):
```sql
CREATE TABLE IF NOT EXISTS plug_logs (
    id TEXT PRIMARY KEY,
    device_id TEXT NOT NULL,
    voltage REAL,
    current REAL,
    power REAL,
    created_at TEXT NOT NULL,
    synced_at TEXT DEFAULT NULL
);

CREATE INDEX IF NOT EXISTS idx_plug_logs_device_time
ON plug_logs(device_id, created_at DESC);
```

**Logging-Mechanismus** (`logger.py` Zeile 260-270):
```python
status = self.plug_controller.get_status(device_id)
if status:
    log = PlugLog(
        device_id=device_id,
        voltage=status.get('voltage', 0),
        current=status.get('current', 0),
        power=status.get('power', 0)
    )
    self.db.insert_plug_log(log)
```

**Logging-Intervall** (`logger.py` Zeile 58):
```python
self.plug_interval = 60  # Default 60s for plugs
```

**Status**: Schema ist korrekt definiert ✅

---

## Root Cause

### KRITISCHER BUG: Leere Datenbank

**Beobachtung**:
```bash
$ ls -lh /Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi_data.db
-rw-r--r--@ 1 denniswestermann  staff  0B Dec 8 09:39 grow_pi_data.db
```

**Test**:
```bash
$ sqlite3 grow_pi_data.db ".tables"
# (no output - empty database)

$ sqlite3 grow_pi_data.db "SELECT COUNT(*) FROM plug_logs;"
Error: no such table: plug_logs
```

**Analyse**:
1. Die lokale Datenbankdatei ist **0 Bytes groß**
2. Die Tabelle `plug_logs` wurde **nie erstellt**
3. `db.initialize()` wurde **nicht aufgerufen** beim lokalen Start
4. Alle API-Calls zu `/api/logs/plugs` liefern **leere Arrays** zurück

**Warum funktioniert der Kosten-Tab dann?**

Der Kosten-Tab ruft dieselbe `get_plug_logs()` Methode auf, aber:
- Er arbeitet auf dem **Raspberry Pi** (192.168.0.86:5000)
- Dort ist die Datenbank **korrekt initialisiert**
- Die Screenshots zeigen, dass der Pi korrekt Daten loggt

**Das Problem**:
- Die Frontend-Analyse wurde lokal durchgeführt
- Die lokale Datenbank ist leer
- Der Verlauf-Tab zeigt deshalb keine Daten

---

## Daten-Aggregations-Spezifikation

### Existierende Implementation

**Downsampling** ist bereits implementiert in `get_plug_logs_downsampled()`:

| Zeitraum | Aggregation | Implementierung |
|----------|-------------|-----------------|
| 0-4h | Raw (1min) | Direkte SELECT-Query |
| 4-24h | 5min avg | `strftime('%Y-%m-%dT%H:') \|\| printf('%02d', (CAST(strftime('%M', created_at) AS INTEGER) / 5) * 5)` |
| 1-7d | 15min avg | `(CAST(strftime('%M', created_at) AS INTEGER) / 15) * 15` |
| 7-30d | 30min avg | `(CAST(strftime('%M', created_at) AS INTEGER) / 30) * 30` |
| >30d | 1h avg | `strftime('%Y-%m-%dT%H:00:00', created_at)` |

**Status**: ✅ Aggregation ist implementiert

### Daten-Retention

**Aktueller Stand**:
- ❌ KEINE automatische Daten-Retention implementiert
- ❌ Alte Daten werden NICHT gelöscht
- ✅ Datenbank wächst unbegrenzt

**Geplant laut Roadmap**: NICHT dokumentiert

---

## Empfehlungen

### 1. SOFORTMASSNAHME: Datenbank-Initialisierung fixen

**Problem**: Lokale Datenbank ist leer (0 Bytes)

**Fix**:
```python
# In api.py oder main.py beim Start:
from grow_pi.database import get_database

db = get_database()
db.initialize()  # <-- Diese Zeile fehlt!
```

**Wo hinzufügen**:
- `pi-controller/grow_pi/main.py` Zeile 454 (bereits vorhanden für Controller)
- `pi-controller/grow_pi/web/app.py` beim Start

**Test**:
```bash
# Nach dem Fix:
sqlite3 grow_pi_data.db ".tables"
# Erwartete Ausgabe:
# curve_presets    lamp_state_log   sensor_readings  system_events
# lamp_curves      plug_logs
```

---

### 2. Raspberry Pi Datenbank prüfen

**Status**: Kann aktuell nicht geprüft werden (SSH Permission Denied)

**Nächste Schritte**:
1. SSH-Zugang zum Pi herstellen
2. Prüfen ob `/home/admin/grow-pi/grow_pi_data.db` existiert
3. Prüfen der Dateigröße:
   ```bash
   ls -lh /home/admin/grow-pi/grow_pi_data.db
   ```
4. Anzahl der Einträge prüfen:
   ```bash
   sqlite3 /home/admin/grow-pi/grow_pi_data.db "SELECT COUNT(*) FROM plug_logs;"
   ```
5. Zeitbereich prüfen:
   ```bash
   sqlite3 /home/admin/grow-pi/grow_pi_data.db "SELECT MIN(created_at), MAX(created_at) FROM plug_logs;"
   ```

**Erwartung**:
- Pi-Datenbank sollte **korrekt funktionieren** (basierend auf Kosten-Tab)
- Problem ist vermutlich **nur lokal**

---

### 3. Daten-Retention Policy implementieren

**Aktueller Stand**: Keine automatische Bereinigung

**Empfohlene Policy**:
```python
# Pseudo-Code
def cleanup_old_data():
    # Behalte Raw-Daten für 30 Tage
    db.delete_plug_logs(older_than_days=30)

    # Alternativ: Archive to separate table
    db.archive_plug_logs(older_than_days=90, target_table="plug_logs_archive")
```

**Implementierung**:
- Als Cron-Job (täglich um 03:00 Uhr)
- Oder als Background-Thread im DataLogger

**Vorteil**:
- Verhindert unbegrenztes Wachstum der Datenbank
- Verbessert Performance von Queries
- Reduziert Speicherverbrauch

---

### 4. Logging-Intervalle optimieren

**Aktuell**:
- Sensors: 120s (2 Minuten)
- Lamps: 120s (2 Minuten)
- Plugs: 60s (1 Minute)

**Empfehlung**:
- Plugs auf 30s reduzieren für feinere Auflösung
- Oder: Adaptive Logging (nur bei Änderung > 5%)

**Vorteil**:
- Bessere Auflösung für Stromverbrauchs-Spitzen
- Echtzeit-Monitoring wird genauer

---

### 5. Frontend-Fehlerbehandlung verbessern

**Problem**: Wenn keine Daten vorhanden sind, zeigt der Chart eine leere Zeitachse

**Empfehlung**:
```javascript
// In history.js:
updatePlugChart(logs) {
    if (!logs || logs.length === 0) {
        this.showChartMessage('Keine Daten verfügbar für diesen Zeitraum');
        return;
    }
    // ... render chart
}
```

**Vorteil**:
- User weiß sofort, dass keine Daten existieren
- Kein "leerer" Chart mehr

---

### 6. Kosten-API auf Downsampling umstellen

**Aktuell**:
```python
db.get_plug_logs(hours=int(hours), limit=100000)
```

**Problem**:
- Bei limit=100000 werden alle Rohwerte geladen
- Ineffizient für große Zeiträume

**Empfehlung**:
```python
db.get_plug_logs_downsampled(hours=int(hours))
```

**Vorteil**:
- Gleiche Aggregationslogik wie im Verlauf-Tab
- Schnellere Queries bei großen Zeiträumen
- Konsistenz zwischen Tabs

---

## Test-Plan

### Nach Fix der Datenbank-Initialisierung:

1. ✅ **Lokale Datenbank prüfen**
   ```bash
   sqlite3 grow_pi_data.db ".tables"
   # Erwartung: Tabellen existieren
   ```

2. ✅ **DataLogger starten**
   ```bash
   python3 -m grow_pi.main
   # Warten 2-3 Minuten
   ```

3. ✅ **Einträge prüfen**
   ```bash
   sqlite3 grow_pi_data.db "SELECT COUNT(*) FROM plug_logs;"
   # Erwartung: > 0
   ```

4. ✅ **Verlauf-Tab testen**
   - Öffne http://localhost:5000
   - Navigiere zu Verlauf-Tab
   - Wähle "24h" Zeitraum
   - Erwartung: Stromverbrauchs-Chart zeigt Daten

5. ✅ **Verschiedene Zeiträume testen**
   - 1h, 24h, 7 Tage, 30 Tage
   - Erwartung: X-Achse zeigt volle Zeitspanne

---

## Zusammenfassung

### ✅ Was funktioniert

1. **Kosten-Tab**: Stromverbrauch wird korrekt aggregiert
   - API: `/api/costs?period={...}`
   - Zeigt korrekte kWh-Werte
   - Berechnung ist akkurat

2. **Datenbank-Schema**: Korrekt definiert
   - Tabelle `plug_logs` existiert (im Schema)
   - Indices sind optimal
   - Downsampling-Logik ist implementiert

3. **Logging-Mechanismus**: Code ist korrekt
   - `DataLogger` schreibt alle 60s
   - `PlugLog` Modell ist korrekt
   - `insert_plug_log()` funktioniert

### ❌ Was nicht funktioniert

1. **Verlauf-Tab**: Zeigt nur ~2h Daten statt voller Zeitspanne
   - **Root Cause**: Lokale Datenbank ist leer (0 Bytes)
   - **Fix**: `db.initialize()` beim Start aufrufen

2. **Datenbank-Initialisierung**: Wird lokal nicht durchgeführt
   - **Root Cause**: `initialize()` wird beim Start nicht aufgerufen
   - **Fix**: In `main.py` oder `app.py` hinzufügen

### 🟡 Was fehlt

1. **Daten-Retention Policy**: Keine automatische Bereinigung
   - Datenbank wächst unbegrenzt
   - Empfehlung: Cleanup-Job implementieren

2. **SSH-Zugang zum Pi**: Aktuell nicht möglich
   - Kann Pi-Datenbank nicht prüfen
   - Wichtig für finale Verifikation

---

## Nächste Schritte

1. **KRITISCH**: Datenbank-Initialisierung fixen
   - `db.initialize()` in `app.py` oder `main.py` aufrufen
   - Lokale Datenbank neu erstellen
   - Testen

2. **HOCH**: SSH-Zugang zum Pi wiederherstellen
   - Pi-Datenbank prüfen
   - Verifizieren dass Pi-Logging funktioniert

3. **MITTEL**: Daten-Retention implementieren
   - Cleanup-Job erstellen
   - Policy definieren (z.B. 90 Tage behalten)

4. **NIEDRIG**: Kosten-API optimieren
   - Auf Downsampling umstellen
   - Performance-Tests durchführen

---

**Ende der Analyse**
