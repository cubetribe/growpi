# API Debug Report - GrowPi v6.19.0

**Datum**: 2025-12-16 09:37 CET
**Agent**: Debug Agent
**Status**: ✅ ALLE FEHLER BEHOBEN

---

## Problem-Übersicht

Mehrere kritische API-Endpoints gaben 500/503 Fehler zurück:
- `/api/curves/presets` - 500 Internal Server Error
- `/api/calendar/milestones?phase=flowering` - 500 Internal Server Error
- `/api/calendar/month/2025-12` - 500 Internal Server Error
- `/api/curves/intensities` - 503 Service Unavailable

---

## Root-Cause-Analyse

### Fehlende Python Dependencies

Die Virtual Environment auf dem Raspberry Pi hatte **zwei kritische Module nicht installiert**:

1. **`tinytuya`** - Für Smart Plug Controller Integration
2. **`python-dotenv`** - Für .env File Parsing

### Fehler-Kette

```
API Request
  ↓
Blueprint Import
  ↓
Database Import (__init__.py)
  ↓
Logger Import (logger.py)
  ↓
SmartPlugController Import (smart_plug_controller.py)
  ↓
❌ import tinytuya → ModuleNotFoundError
```

**Konsequenz**: Sobald eine API Route die Datenbank importieren wollte, brach der gesamte Import-Chain zusammen.

### Log-Evidenz

```
Dec 16 09:33:48 growpi grow-pi[528724]: 2025-12-16 09:33:48,041 - grow_pi.web.api - ERROR - Exception on /api/curves/presets [GET]
Dec 16 09:33:48 growpi grow-pi[528724]: Traceback (most recent call last):
  File "/opt/grow-pi/grow_pi/lamps/smart_plug_controller.py", line 5, in <module>
    import tinytuya
ModuleNotFoundError: No module named 'tinytuya'
```

```
Dec 16 09:35:36 growpi grow-pi[529213]: ModuleNotFoundError: No module named 'dotenv'
```

---

## Durchgeführte Fixes

### 1. Installation tinytuya

```bash
cd /opt/grow-pi
source venv/bin/activate
pip install tinytuya
```

**Installierte Abhängigkeiten**:
- `tinytuya==1.17.4`
- `colorama==0.4.6`
- `cryptography==46.0.3`
- `cffi==2.0.0`
- `pycparser==2.23`

### 2. Installation python-dotenv

```bash
pip install python-dotenv
```

**Installierte Version**:
- `python-dotenv==1.2.1`

### 3. Service Neustart

```bash
sudo systemctl restart grow-pi
```

**Restart-Status**: ✅ Erfolgreicher Warm Restart mit PWM-State-Preservation

---

## Verifikation

### API Endpoint Tests (POST-FIX)

#### 1. `/api/curves/presets` ✅

```json
{
  "success": true,
  "presets": [
    {
      "id": 3,
      "name": "123",
      "curves_json": {...},
      "created_at": "2025-12-07T20:52:06.714446"
    },
    {
      "id": 8,
      "name": "Bloom 2 UV",
      "curves_json": {...}
    }
    // ... 7 presets total
  ]
}
```

#### 2. `/api/calendar/milestones?phase=flowering` ✅

```json
{
  "success": true,
  "count": 14,
  "milestones": [
    {
      "id": "ms-flow-001",
      "title": "Flip zu 12/12",
      "phase": "flowering",
      "day_offset_min": 1,
      "day_offset_max": 1
    }
    // ... 14 milestones total
  ]
}
```

#### 3. `/api/calendar/month/2025-12` ✅

```json
{
  "success": true,
  "month": "2025-12",
  "days_count": 8,
  "calendar": {
    "2025-12-07": {
      "entries": [...]
    }
    // ... 8 days with entries
  }
}
```

#### 4. `/api/curves/intensities` ✅

```json
{
  "success": true,
  "timestamp": "2025-12-16T09:36:34.943755",
  "channels": {
    "1": {"name": "Far Red", "intensity": 0, "enabled": true},
    "2": {"name": "Warm White", "intensity": 0, "enabled": true},
    "3": {"name": "Cool White", "intensity": 0, "enabled": true},
    "4": {"name": "UV", "intensity": 0, "enabled": false}
  }
}
```

### Service Status ✅

```
● grow-pi.service - GrowPi Greenhouse Controller
     Loaded: loaded (/etc/systemd/system/grow-pi.service; enabled; preset: enabled)
     Active: active (running) since Tue 2025-12-16 09:36:04 CET
   Main PID: 529389 (python)
      Tasks: 8
```

**Uptime**: 1min+ ohne Fehler
**PWM State**: Preserved (60%, 60%, 60%, 0%)
**Zero-Downtime**: ✅ Aktiv

---

## Datenbank-Status

### Korrekte Datenbank-Location

**NICHT**: `/opt/grow-pi/grow_pi_data.db` (0 Bytes, leer)
**KORREKT**: `/opt/grow-pi/data/growpi.db` (44 MB)

### Vorhandene Tabellen

```
curve_presets             grows                     plug_logs
daily_logs                lamp_curves               sensor_readings
device_automation_config  lamp_state_log            switchable_devices
device_state_log          phase_events              sync_status
device_time_schedules     phase_milestones          system_events
```

**Migrationen angewendet**:
- ✅ `20251206_device_time_schedules.sql`
- ✅ `20251212_grow_calendar.sql`
- ✅ `20251213_phase_milestones.sql`

---

## Zusammenfassung

### Probleme Behoben

| Endpoint | Status Vorher | Status Nachher | Fix |
|----------|--------------|----------------|-----|
| `/api/curves/presets` | 500 | 200 ✅ | tinytuya + dotenv |
| `/api/calendar/milestones` | 500 | 200 ✅ | tinytuya + dotenv |
| `/api/calendar/month` | 500 | 200 ✅ | tinytuya + dotenv |
| `/api/curves/intensities` | 503 | 200 ✅ | tinytuya + dotenv |

### Keine Restfehler

- ✅ Service läuft stabil
- ✅ Keine Import-Fehler mehr
- ✅ Datenbank korrekt initialisiert
- ✅ Alle Calendar-Features funktionsfähig
- ✅ Alle Curve-Features funktionsfähig

---

## Lessons Learned

### Problem-Ursache

Das Problem entstand wahrscheinlich beim letzten Deployment, bei dem die `requirements.txt` nicht vollständig synchron mit dem Code war. Die Module `tinytuya` und `python-dotenv` wurden im Code verwendet, aber nicht als Dependencies deklariert.

### Empfehlungen

1. **requirements.txt aktualisieren**:
   ```txt
   tinytuya==1.17.4
   python-dotenv==1.2.1
   ```

2. **Deployment-Checklist**:
   - Vor Deployment: `pip freeze > requirements.txt`
   - Nach Deployment: `pip install -r requirements.txt`
   - Service-Neustart mit Health-Check

3. **Monitoring verbessern**:
   - Automated Health-Check nach Deployment
   - Kritische Endpoints in Startup-Test integrieren

---

## Nächste Schritte

### Optional (falls gewünscht):

1. **requirements.txt aktualisieren** auf dem Pi
2. **Deployment-Dokumentation** erweitern
3. **Health-Check Endpoint** implementieren

### Status: READY FOR PRODUCTION

Alle Fehler behoben, System läuft stabil.

---

**Ende des Reports**
