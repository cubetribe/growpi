# GrowPi Roadmap - Archiv

**Letzte Aktualisierung**: 2025-12-20
**Zweck**: Dokumentation aller abgeschlossenen Features und Fixes

---

## Inhaltsverzeichnis

- [v6.21.0 - Calendar DB Schema](#v6210---calendar-db-schema)
- [v6.20.0 - Grow Calendar](#v6200---grow-calendar)
- [v6.19.0 - Camera YUYV Format](#v6190---camera-yuyv-format)
- [v6.18.0 - Camera Auto-Detection](#v6180---camera-auto-detection)
- [v6.15.0 - Bezier Curve Editor](#v6150---bezier-curve-editor)
- [v6.14.0 - Bug Fixes (Smart Plug & Dehumidifier)](#v6140---bug-fixes)
- [v6.13.0 - Room Automation Status-Sync](#v6130---room-automation-status-sync)
- [v6.12.0 - Data Aggregation](#v6120---data-aggregation)
- [v6.11.0 - Verlauf-Seite Fixes](#v6110---verlauf-seite-fixes)
- [v6.10.0 - Multi-Line Preview Chart](#v6100---multi-line-preview-chart)
- [v6.9.1 - Zero-Downtime Bugfix](#v691---zero-downtime-bugfix)
- [v6.9.0 - PWM Zero-Downtime Restarts](#v690---pwm-zero-downtime-restarts)
- [v6.8.0 - Feature Pack](#v680---feature-pack)
- [v6.7.0 - Bug Fixes & Deployment](#v670---bug-fixes--deployment)
- [v6.6.0 - CPU Optimization](#v660---cpu-optimization)
- [v6.5.0 - Modular Architecture](#v650---modular-architecture)
- [v6.4.0 - Entfeuchter-Automatik](#v640---entfeuchter-automatik)
- [v6.3.0 - Kosten-Monitoring](#v630---kosten-monitoring)
- [Behobene Bugs](#behobene-bugs)

---

## v6.21.0 - Calendar DB Schema

**Datum**: 2025-12-20
**Status**: ✅ ABGESCHLOSSEN

- Calendar DB Schema mit get_connection() Context Manager
- Phase Tracking & Milestones

---

## v6.20.0 - Grow Calendar

**Datum**: 2025-12-20
**Status**: ✅ ABGESCHLOSSEN

- Grow Calendar mit Phase Tracking
- Milestones-System

---

## v6.19.0 - Camera YUYV Format

**Datum**: 2025-12-09
**Status**: ✅ ABGESCHLOSSEN

- Camera YUYV Format für bessere Timelapse-Qualität

---

## v6.18.0 - Camera Auto-Detection

**Datum**: 2025-12-09
**Status**: ✅ ABGESCHLOSSEN

**Problem:**
USB-Webcam wechselt Device-Nummer nach Reboot/USB-Reconnect:
- Nach Reboot: /dev/video0 → /dev/video1
- Hardcoded `device_id: 0` funktioniert nicht mehr

**Lösung:**
- Neue Funktion `find_lifecam_device()` in `camera.py`
- Sucht automatisch nach LifeCam HD-3000 via v4l2-ctl
- Fallback: Probiert video0/1/2 durch mit OpenCV
- Default `device_id: -1` triggert Auto-Detection

**Technische Details:**
- Subprocess: `v4l2-ctl --list-devices` (Timeout 5s)
- Regex: `/dev/video(\d+)` Parsing
- Fallback-Chain: Name → v4l2-ctl → OpenCV Probe → Default 0

---

## v6.18.0 - Separate JPEG-Qualitäten

**Datum**: 2025-12-09
**Status**: ✅ ABGESCHLOSSEN

**Änderungen:**
- `preview_jpeg_quality: 70` - Für Live-Preview (ressourcenschonend)
- `timelapse_jpeg_quality: 95` - Für Zeitraffer-Fotos (hohe Qualität)
- Preview FPS: 10 → 2 (90% weniger Ressourcenverbrauch)

---

## v6.15.0 - Bezier Curve Editor

**Datum**: 2025-12-07
**Status**: ✅ GRUNDFUNKTION ABGESCHLOSSEN

**Aktueller Stand**:
- Grundfunktionalität implementiert und deployed
- Keyframes können gesetzt/verschoben werden
- Mobile UI-Probleme noch offen (separates Issue)

---

## v6.14.0 - Bug Fixes

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

### Bug #9: SmartPlugController - Keine Erfolgsverifikation

**Problem:**
`turn_on()` und `turn_off()` gaben IMMER `True` zurück ohne Prüfung.

**Lösung:**
Nach dem Schaltbefehl den Status abfragen und verifizieren.

### Bug #10: DehumidifierController - Manuelle Steuerung Skip-Bug

**Problem:**
Bei manueller Steuerung wurde Early-Return gemacht wenn Status scheinbar korrekt.

**Lösung:**
Bei `TriggerType.MANUAL` IMMER den Befehl senden.

---

## v6.13.0 - Room Automation Status-Sync

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

**Problem:**
Controller speicherte `self._is_on` intern, synchronisierte aber nie mit echtem Tuya-Status.

**Fix:**
`_sync_device_status()` fragt echten Tuya-Status ab.

---

## v6.12.0 - Data Aggregation

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

**Umsetzung (Query-Time Aggregation):**

- Alle Rohdaten bleiben erhalten
- Intelligentes Downsampling bei API-Abfrage mit AVG():

| Zeitraum | Auflösung | Aggregation |
|----------|-----------|-------------|
| 0-4h | Minutengenau | Rohdaten |
| 4-24h | 5-Min-Intervalle | AVG() |
| 1-7 Tage | 15-Min-Intervalle | AVG() |
| 7-30 Tage | 30-Min-Intervalle | AVG() |
| >30 Tage | Stündlich | AVG() |

**Geänderte Dateien:**
- `db.py`: 3 neue Downsampling-Methoden
- `logs_bp.py`: Alle Endpoints mit automatischem Downsampling

---

## v6.11.0 - Verlauf-Seite Fixes

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

- Steckdosen-Namen werden korrekt angezeigt
- Zeitfilter funktioniert für alle 3 Charts synchron
- "1h" Button hinzugefügt
- Chart.js Date-Adapter für echte Zeit-Achsen
- Stromverbrauch-Daten werden angezeigt (Fix: API-Response-Format)

---

## v6.10.0 - Multi-Line Preview Chart

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

**Umsetzung:**
- SVG-basiertes Multi-Line-Chart
- Alle 4 Kanäle gleichzeitig sichtbar mit farbigen Linien
- Checkboxen zum Ein-/Ausblenden einzelner Kanäle
- X-Achse: 00:00 - 24:00 mit Zeitlabels
- Y-Achse: 0% - 100% mit %-Labels
- Grid-Linien für bessere Lesbarkeit
- localStorage Persistenz für Checkbox-Status
- Responsive Design für Mobile

---

## v6.9.1 - Zero-Downtime Bugfix

**Datum**: 2025-12-07
**Status**: ✅ ABGESCHLOSSEN

**Problem:** Zero-Downtime aus v6.9.0 funktionierte NICHT - Lampen gingen kurz aus

**Root Cause:**
- `api.py` wurde beim Flask-Import geladen
- `PWMController.initialize()` wurde OHNE State-Check aufgerufen
- Alle PWM-Kanäle wurden auf 0 gesetzt → Lampen aus

**Fix:**
- `PWMController.initialize()` mit neuem Parameter `skip_zero_init`
- `api.py` prüft `state_exists()` VOR initialize()
- `main.py` prüft State VOR initialize()

**Test-Ergebnis:**
```
VOR RESTART:  Ch2: 34%, Ch3: 65%
NACH RESTART: Ch2: 34%, Ch3: 65%  ← LAMPEN BLIEBEN AN!
```

---

## v6.9.0 - PWM Zero-Downtime Restarts

**Datum**: 2025-12-06
**Status**: ✅ ABGESCHLOSSEN

**Implementierung:**
- Neue `disconnect()` Methode im PWMController
- State-Persistence in `/run/growpi/pwm_state.json`
- Warm-Restart Erkennung beim Startup
- Systemd RuntimeDirectoryPreserve

**Dateien:**
- `grow_pi/utils/pwm_state.py` (NEU)
- `grow_pi/lamps/pwm_controller.py` (GEÄNDERT)
- `grow_pi/main.py` (GEÄNDERT)
- `systemd/grow-pi.service` (GEÄNDERT)

---

## v6.8.0 - Feature Pack

**Datum**: 2025-12-06
**Status**: ✅ ABGESCHLOSSEN

**Parallel-Agenten Workflow (11 Agents):**
- Feature #1: Version Display im Header (KRITISCH)
- Feature #2: Zeitbasierte Geräte-Schaltung (Priority-Logik + Fallback)
- Feature #3: Collapsible Sections (Accordion UI)
- Feature #4: Kurven-Presets System (Save/Load/Manage)

**Highlights:**
- Smart Fallback-Logik: Zeitfenster endet → prüfe Feuchtigkeit
- System-Presets: Keimung, Wachstum, Blüte
- localStorage Persistence für Accordion-Zustand

**Technical:**
- 2 neue DB-Tabellen (device_time_schedules, curve_presets)
- 9 neue API Endpoints
- 3 neue JS Module
- ~2100 LOC Added

---

## v6.7.0 - Bug Fixes & Deployment

**Datum**: 2025-12-06
**Status**: ✅ ABGESCHLOSSEN

**Frontend Fixes:**
- Fixed: Kurven-Tab not loading data
- Fixed: Cost/Room buttons CSS styling
- Added: Dynamic module loading on tab switch

**Backend Fixes:**
- Fixed: Missing blueprints deployment
- Fixed: Blueprint registration in `api.py`
- Fixed: DehumidifierController initialization

---

## v6.6.0 - CPU Optimization

**Datum**: 2025-12-06
**Status**: ✅ ABGESCHLOSSEN

**CPU Load:** 75% → 15-25% (-67% reduction!)

- Replaced `time.sleep(0.1)` loop with `threading.Event.wait()`
- Increased sensor logging interval from 60s to 120s
- DHT22 sensor cache lifetime: 3s → 30s

---

## v6.5.0 - Modular Architecture

**Datum**: 2025-12-06
**Status**: ✅ ABGESCHLOSSEN

**Frontend Refactoring** (-86% LOC reduction)
- **BEFORE**: Monolithic `index.html` (2894 LOC)
- **AFTER**: Modular architecture (408 LOC + 8 modules)

**Backend Refactoring** (8 Flask Blueprints)
- Clean separation of concerns
- Service layer pattern

---

## v6.4.0 - Entfeuchter-Automatik

**Datum**: 2025-12-05
**Status**: ✅ ABGESCHLOSSEN

**Features**:
- Tuya Smart Plug Integration (Bluetooth)
- Automatische Feuchtigkeitsregelung mit Hysterese
- Soll-Wert: 60% (±5% Hysterese)
- Auto/Manual Toggle
- Min. Laufzeit: 5 Minuten
- Zeitbasierte Schaltung (Schedule)

**Endpoints**:
- `GET /api/room` - Status
- `GET /api/room/config` - Automation-Config
- `POST /api/room/config` - Config aktualisieren
- `POST /api/room/dehumidifier` - Manual On/Off

---

## v6.3.0 - Kosten-Monitoring

**Datum**: 2025-12-05
**Status**: ✅ ABGESCHLOSSEN

**Features**:
- Stromverbrauch-Messung (kWh/h)
- kWh-Preis Konfiguration (€/kWh)
- Kosten-Breakdown: Heute / Diese Woche / Dieser Monat
- Gerätespezifische Kosten
- Historische Kosten-Trends

**Endpoints**:
- `GET /api/costs?period=today|week|month`
- `GET /api/costs/config`
- `POST /api/costs/config`

---

## Behobene Bugs

### Bug #1: Room/Entfeuchter-Steuerung
**Behoben**: 2025-12-07
- `dehumidifier_controller.set_humidity_reader()` wurde nie aufgerufen
- Tuya Device ID fehlte in der Datenbank
- DB-Migration lief nicht automatisch

### Bug #3: Kosten-Tracking
**Status**: Kein Bug - funktioniert

### Bug #4: DHT22 Sensor
**Behoben**: 2025-12-07
- Temporäres Timing-Problem nach Service-Restart

### Bug #5: Tuya Device ID
**Behoben**: 2025-12-07
- Device ID in DB eingetragen

### Bug #6: Kurven-Presets
**Behoben**: 2025-12-07
- `applySelectedPreset()` verbessert
- Fallback zu `fetchCurves()`

### Bug #7: Verlauf-Seite
**Behoben**: 2025-12-07
- Steckdosen-Namen korrekt
- Zeitfilter synchron
- Chart.js Date-Adapter

### Bug #9: SmartPlugController Verifikation
**Behoben**: 2025-12-07
- Erfolgsverifikation nach Schaltbefehl

### Bug #10: DehumidifierController Skip-Bug
**Behoben**: 2025-12-07
- Manual-Trigger sendet immer Befehl

---

## Implementierte Features (Übersicht)

| Feature | Version | Datum |
|---------|---------|-------|
| Kurven-Presets | v6.8.0 | 2025-12-06 |
| Collapsible Sections | v6.8.0 | 2025-12-06 |
| Version Display | v6.8.0 | 2025-12-06 |
| Zeitbasierte Schaltung | v6.8.0 | 2025-12-06 |
| Multi-Line Chart | v6.10.0 | 2025-12-07 |
| Data Aggregation | v6.12.0 | 2025-12-07 |
| Bezier Curve Editor | v6.15.0 | 2025-12-07 |
| Camera Auto-Detection | v6.18.0 | 2025-12-09 |
| Grow Calendar | v6.20.0 | 2025-12-20 |

---

**Ende des Archivs**
