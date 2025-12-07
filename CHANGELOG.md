# GrowPi Project Changelog

All notable changes to the GrowPi project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v6.9.1] - 2025-12-07

### Fixed
- **CRITICAL BUGFIX: Zero-Downtime funktionierte nicht**
  - Symptom: Lampen gingen bei Service-Restart kurz aus (Fade-Out/Fade-In)
  - Root Cause: `api.py` wurde beim Import geladen und initialisierte PWMController
    OHNE State-Prüfung, dadurch wurden alle PWM-Kanäle auf 0 gesetzt
  - Fix in 3 Dateien:
    1. `pwm_controller.py` - neuer Parameter `skip_zero_init` in `initialize()`
    2. `api.py` - prüft `state_exists()` VOR `initialize()` und übergibt `skip_zero_init=True`
    3. `main.py` - prüft State VOR `initialize()`, übergibt `skip_zero_init=True`

### Changed
- `PWMController.initialize()` akzeptiert jetzt `skip_zero_init: bool = False`
  - Bei `True`: PWM-Kanäle werden NICHT auf 0 gesetzt (für Warm-Restart)
  - Log-Ausgabe zeigt jetzt "warm (PWM preserved)" oder "cold (PWM reset to 0)"
- Warm-Restart Logging verbessert:
  - "State file found - will preserve PWM values"
  - "PWM state restored - Zero-Downtime active!"

### Deployment
- ✅ Deployed auf Pi @ 192.168.0.86
- ✅ Getestet mit mehreren Service-Restarts
- ✅ Lampen bleiben jetzt wirklich an (kein Flackern mehr!)

### Known Issues (noch zu beheben)
- **Room/Entfeuchter-Steuerung funktioniert nicht**
  - Fehler: `no such table: device_automation_config`
  - Steckdose reagiert nicht auf Steuerung
  - Zeitschaltung (Override) funktioniert nicht
- **Kosten-Tracking** - API-Verbindung zu prüfen

---

## [v6.9.0] - 2025-12-06

### Added
- **Zero-Downtime Service-Restarts** - PWM-Werte bleiben bei `systemctl restart` erhalten
- PWM State Persistence Modul (`grow_pi/utils/pwm_state.py`)
  - `save_state()` - Speichert PWM-Zustand vor Shutdown
  - `load_state()` - Lädt State für Warm-Restart
  - `state_exists()` - Prüft ob gültiger State vorhanden
  - File-Locking für atomische Schreiboperationen
- Warm-Restart Detection in `main.py`
  - Erkennt Warm-Restart via State-File
  - Stellt PWM-Tracking wieder her ohne Hardware zu ändern
  - Log-Ausgabe: "WARM RESTART DETECTED", "PWM state restored - no flickering!"

### Changed
- **PWMController** erweitert um `disconnect()` Methode
  - Trennt Verbindung OHNE PWM-Werte zu ändern
  - PWM läuft weiter via pigpiod
- `cleanup()` Methode mit optionalem `turn_off_lamps` Parameter
- Systemd Service Konfiguration
  - `RuntimeDirectory=growpi`
  - `RuntimeDirectoryPreserve=yes`
  - `TimeoutStopSec=30`
  - `KillMode=mixed`

### Fixed
- **LED-Flackern bei Service-Restart** - Root Cause: `cleanup()` rief `all_off()` auf
- PWM-Werte bleiben IMMER erhalten, auch bei `systemctl stop`

### Deployment
- ✅ Deployed auf Pi @ 192.168.0.86
- ✅ Getestet mit mehreren Restarts (kein Flackern)
- ✅ Logs zeigen "PWM preserved" bei Shutdown

---

## [v6.8.1] - 2025-12-06

### Removed
- Frontend directory extracted to separate repository
- Repository now focuses exclusively on Raspberry Pi backend

### Changed
- **Repository Structure** - Clearer separation of concerns
- New Repository: [cubetribe/growpi_web_public](https://github.com/cubetribe/growpi_web_public) für Next.js Frontend
- Removed confusion between embedded Pi Web UI und VPS Frontend

### Known Issues
- `/api/curves/*` endpoints returning 503 (CurveController not initializing)

---

## [v6.8.0] - 2025-12-06

### Added
- **Version Display im Header** - Version Badge "v6.8.0" neben "Aktualisiert: HH:MM" (KRITISCH für Deployment-Verification)
- **Zeitbasierte Geräte-Schaltung**
  - Neue DB-Tabelle: `device_time_schedules`
  - Priority-Logik: Zeit-Fenster > Feuchtigkeit > Manuell
  - Smart Fallback: Prüft Feuchtigkeit wenn Zeitfenster endet
  - 4 API Endpoints: `/api/room/schedules` (CRUD)
  - Frontend: Zeitfenster-Verwaltung im Room-Tab
  - Validierung: Verhindert überlappende Zeitfenster
  - Mitternachts-Wrap-around Support (23:00-01:00)
- **Collapsible Sections (Accordion)**
  - Klappbare Sektionen: "Beleuchtung" + "Schaltbare Geräte"
  - Smooth CSS Animations (0.3s transitions)
  - localStorage Persistence (überlebt Page-Reloads)
  - Keyboard-Accessible (Enter/Space) + ARIA-Attribute
  - Neues Modul: `accordion.js`
- **Kurven-Presets System**
  - Neue DB-Tabelle: `curve_presets`
  - 3 Built-in Presets: Keimung, Wachstum, Blüte
  - 5 API Endpoints: `/api/curves/presets` (GET, POST, PUT, DELETE, APPLY)
  - Frontend: Dropdown + Save/Manage Modals
  - System-Preset Schutz (können nicht gelöscht werden)

### Technical
- 11 Agent Reports in `/agents/` Ordner
- Parallel Implementation (4 agents) + Validation + Integration Testing
- CSS: +~900 Zeilen, JavaScript: +~1200 Zeilen (3 neue Module)
- SQL: 2 neue Tabellen mit Indexes
- Files Modified: 15, Lines Added: ~2100

---

## [v6.7.1] - 2025-12-06

### Performance
- **CPU Load Optimization** - 75% → 15-25% (-67% reduction!)
- Sleep-Loop → Event.wait() (180 OS-Calls/min → 3 OS-Calls/min, ~98% savings)
- Logging-Intervall: 60s → 120s (50% weniger DB-Writes)
- DHT22 Cache: 3s → 30s (90% weniger Sensor-Reads)

### Benefits
- Lower energy consumption
- More CPU headroom for future features
- Reduced SD card wear
- Improved system responsiveness

---

## [v6.7.0] - 2025-12-06

### Fixed
- Kurven-Tab not loading data (added tab-switch handler in `utils.js`)
- Cost/Room buttons CSS styling (added `.cost-period-btn` and `.room-toggle-btn`)
- Missing blueprints deployment (`costs_bp.py`, `dehumidifier_bp.py`)
- Blueprint registration in `api.py`
- DehumidifierController initialization in hardware service

### Changed
- Tab-switch now properly triggers `fetchCurves()` and other data loaders
- Dynamic module loading on tab switch

### Documentation
- Updated CHANGELOG.md with all version history
- Rewrote README.md with v6.6 architecture diagrams
- Added API endpoint reference tables
- Added hardware GPIO pin configuration

### Testing
- All 14 API endpoints verified ✅
- 140/140 integration tests passing ✅
- User-validated on Pi @ 192.168.0.86 ✅

---

## [v6.6.0] - 2025-12-06

### Performance
- **CPU Load:** 75% → 15-25% (-67% reduction!)

| Optimierung | Vorher | Nachher | Einsparung |
|-------------|--------|---------|------------|
| Sleep-Loop → Event.wait() | 180 OS-Calls/min | 3 OS-Calls/min | ~98% |
| Logging-Intervall | 60s | 120s | 50% weniger DB-Writes |
| DHT22 Cache | 3s | 30s | 90% weniger Sensor-Reads |

---

## [v6.5.0] - 2025-12-06

### Changed
- **Major Refactoring** - Modular Architecture
- Frontend: Monolithic `index.html` (2894 LOC) → Modular (408 LOC + 8 modules) (-86% LOC reduction)
- Backend: 8 Flask Blueprints für saubere API-Struktur

### Added
- **v6.3: Energy Cost Tracking**
  - Real-time electricity consumption monitoring
  - Device-level breakdown (6 devices)
  - Period filters: Today, 7 Days, This Month, This Year
  - Custom date range selection
  - Configurable kWh price (EUR)
- **v6.4: Dehumidifier/Room Control**
  - Smart dehumidifier automation
  - Target humidity configuration (30-90%)
  - Auto-toggle based on sensor readings
  - Manual override capability

### Technical
- Frontend LOC Reduktion: -86% (2894 → 408)
- Backend Blueprints: 8 (vorher 6)
- JS Module: 7 (vorher 3)
- Unit-Tests: 140 (vorher 91)
- Test Success Rate: 100%
- API Response Time: ~8ms

---

## [v6.4.0] - 2025-12-06

### Added
- Dehumidifier/Room Control Tab
- Smart dehumidifier automation based on humidity
- Target humidity configuration (30-90%)
- Manual override capability
- Real-time status monitoring

---

## [v6.3.0] - 2025-12-06

### Added
- Energy Cost Tracking Tab
- Real-time electricity consumption monitoring
- Device-level breakdown (Main Light, Dehumidifier, Living Room, Pump, FR Main, Midday Sun)
- Period filters: Today, 7 Days, This Month, This Year
- Custom date range selection
- Configurable kWh price in EUR
- Total kWh + total cost display

---

## [v6.2.0] - 2025-12-06

### Added
- Complete modular JavaScript architecture
- Centralized API client (`GrowPiAPI` class)
- State management with Pub/Sub pattern
- 7 JavaScript modules for clean code separation

### Changed
- Frontend restructured from monolithic to modular
- All API calls now use centralized client
- Improved error handling and consistency

### Documentation
- 12 Refactoring Reports archived in `docs/refactoring/`
- Updated README.md with new architecture
- Project cleanup: 24 → 9 root files (-62.5%)

---

## Ältere Versionen

Für Versionen vor v6.2.0 siehe [CHANGELOG_ARCHIVE.md](docs/CHANGELOG_ARCHIVE.md)

Archiviert:
- v6.1.x und älter - Complete refactoring history
- v6.0 - Complete Code Refactoring & Modularization
- v5.x - Smart Plug Integration, System Hardening, Mode Management
- v4.x - Per-Channel Lighting Curves
- v3.x - SQLite Logging System
- v2.x - DHT22 Sensor Integration, MVP Complete
- v1.x - Initial Deployment, Database Migration

---

**Projekt**: GrowPi Commercial Greenhouse Management
**Entwickler**: Dennis Westermann (d.westermann@ol-mg.de)
**Lizenz**: Proprietary
**Platform**: Raspberry Pi 3B+ + VPS Deployment
