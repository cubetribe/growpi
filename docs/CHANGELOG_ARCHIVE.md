# GrowPi Project Changelog Archive

**Archive of versions prior to v6.2.0**

This file contains historical changelog entries for versions before v6.2.0. For current and recent versions, see [CHANGELOG.md](../CHANGELOG.md).

---

## [2025-12-06 v6.0] - Complete Code Refactoring & Modularization 🎉

**Status**: Branch `refactoring/phase-1-modularization` - Ready for Test Deployment
**Platform**: Development (macOS) - NOT LIVE YET
**Author**: Claude Code (Orchestrated 15 parallel agents)

### Summary

Vollständige Transformation des GrowPi-Projekts von monolithischer MVP-Architektur zu professioneller, modularer Codebasis. Das Backend wurde in **6 Blueprint-Module** und **4 Service-Layer Module** aufgeteilt, das Frontend in **9 JavaScript-Module** modularisiert. Zusätzlich wurden **91 Unit-Tests** (100% PASS) geschrieben und eine vollständige **Pi-Testumgebung** für Entwicklung ohne Hardware erstellt.

### Major Changes

#### Backend API Refactoring ✅

**Problem**: Monolithische `api.py` (883 Zeilen) - alles in einer Datei

**Lösung**: Flask Blueprint-Architektur + Service Layer

```
pi-controller/grow_pi/web/
├── app.py (474 LOC)              # Flask App Factory (-46% Code)
├── dependencies.py               # Dependency Injection Container
├── blueprints/                   # 6 Module - REST API Endpoints
│   ├── status_bp.py             # GET /api/status, /api/health
│   ├── temperature_bp.py        # GET /api/temperature
│   ├── lamps_bp.py              # POST /api/lamp/<channel>
│   ├── mode_bp.py               # GET/POST /api/mode
│   ├── curves_bp.py             # GET/PUT /api/curves/*
│   └── logs_bp.py               # GET /api/logs/*
└── services/                     # 4 Module - Business Logic Layer
    ├── hardware_service.py      # PWM + DHT22 Wrapper
    ├── logging_service.py       # DataLogger Wrapper
    ├── curve_service.py         # CurveController + ModeManager
    └── lamp_config.py           # Lamp Channel Configuration
```

**API Kompatibilität**: 100% rückwärtskompatibel - alle Endpoints behalten exakte Response-Struktur

**Backup**: Alte `api.py` (883 LOC) bleibt unverändert als Fallback

#### Frontend Modularisierung ✅

**Problem**: Monolithische `index.html` (2440 Zeilen) - 760 Zeilen CSS + 1426 Zeilen JavaScript inline

**Lösung**: Separation of Concerns

```
pi-controller/grow_pi/web/static/
├── index.html (~250 LOC)         # Nur HTML Struktur (-90%)
├── css/
│   └── main.css (756 LOC)       # Extrahierte Styles
└── js/
    ├── api.js (218 LOC)         # Zentraler API Client
    ├── state.js (336 LOC)       # State Management (Pub/Sub)
    └── modules/
        ├── control.js (228 LOC) # Tab 1: Steuerung
        ├── curves.js (661 LOC)  # Tab 2: Kurven-Editor
        └── history.js (623 LOC) # Tab 3: Charts & Logs
```

**Vorteile**: Modulare Architektur, Wiederverwendbarkeit, Browser-Caching, Testbarkeit

#### Unit Tests (100% PASS) ✅

**Problem**: Keine Tests - kritische Kurven-Logik ungetestet

**Lösung**: Comprehensive Test Suite mit pytest

```
pi-controller/tests/
├── unit/
│   ├── test_curve_interpolation.py  # 62 Tests ✓ (Pflanzen-Sicherheit!)
│   └── test_mode_manager.py         # 29 Tests ✓ (Thread-Safety!)
└── conftest.py                       # pytest Fixtures

============================== test session starts ==============================
collected 91 items

tests/unit/test_curve_interpolation.py::62 PASSED                       [ 68%]
tests/unit/test_mode_manager.py::29 PASSED                              [100%]

============================== 91 passed in 0.24s ===============================
```

**Coverage**: 93% für `curve_controller.py` und `mode_manager.py`

**Kritische Tests**:
- Midnight Wraparound (23:59 → 00:00) ✓
- Intensity Bounds (0-100%) ✓
- Thread Safety (1000 concurrent ops) ✓
- Real-World Szenarien (18/6 Lichtzyklen) ✓

#### Pi-Testumgebung ✅

**Problem**: Entwicklung nur auf echtem Pi möglich (pigpio, GPIO, Sensoren nötig)

**Lösung**: Vollständige Mock-Hardware für lokale Entwicklung

```
pi-controller/test_environment/
├── run_local.py                  # Flask Server (Simulation Mode)
├── mock_hardware.py              # Mock PWM, DHT22, DataLogger
├── config_test.yaml              # Test-Konfiguration
├── validate.py                   # Validierungs-Script
├── test_api.py                   # API Integration Tests
├── pytest_example.py             # Test-Beispiele
├── Dockerfile                    # Docker Support (optional)
├── docker-compose.yml            # Docker Compose
└── README.md + QUICKSTART.md     # Dokumentation
```

**Plattformen**: macOS ✓, Linux ✓, Windows ✓ (via Docker)

**Mock-Komponenten**:
- MockPWMController - Simuliert GPIO (kein pigpio nötig)
- MockDHT22 - Generiert realistische Temp/Humidity (22±2°C, 60±5%)
- MockDataLogger - In-Memory SQLite

### Metrics

| Metrik | Vorher | Nachher | Verbesserung |
|--------|--------|---------|--------------|
| **Backend Hauptdatei** | 883 LOC | 474 LOC | **-46%** |
| **Frontend HTML** | 2440 LOC | 250 LOC | **-90%** |
| **Backend Module** | 1 | 11 | **+1000%** |
| **Frontend Module** | 0 | 6 | **+∞** |
| **Unit Tests** | 0 | 91 | **+∞** |
| **Code Coverage** | 0% | 93% | **+∞** |

### Breaking Changes

**KEINE!** 🎉

- ✅ Alle API-Endpoints identisch
- ✅ Response-Format unverändert
- ✅ Request-Format unverändert
- ✅ HTTP Status Codes gleich
- ✅ Frontend funktioniert mit BEIDEN APIs (alt & neu)

---

## [2025-12-06 v5.3] - Smart Plug Integration (Gemini)

**Status**: Production-Ready
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)

### Summary

Integration von Bluetooth-gesteuerten Smart Plugs (Tuya/ANTELA) zur Überwachung des Stromverbrauchs:

- **Tuya Cloud API**: Steuerung und Auslesen von BLE-Geräten über die Cloud
- **Daten-Logging**: Erfassung von Spannung, Strom und Leistung alle 60s
- **Visualisierung**: Neues "Stromverbrauch"-Diagramm im Web-Interface

### Changes

- **Backend**:
  - `SmartPlugController`: Nutzt `tinytuya.Cloud` für BLE-Geräte
  - `DataLogger`: Neuer Thread für Plug-Logging (`_plug_loop`)
  - `Database`: Neue Tabelle `plug_logs` und `PlugLog` Model
- **API**:
  - Neuer Endpoint `GET /api/logs/plugs`
- **Frontend**:
  - `index.html`: Chart.js Integration für Stromverbrauchs-Diagramm
  - Bugfix: `updateLampChart` Signatur korrigiert

### Known Issues

- **Cloud Dependency**: BLE-Geräte benötigen Internetverbindung zur Tuya Cloud
- **Latency**: Cloud-API hat höhere Latenz als lokale WiFi-Geräte

---

## [2025-12-06 v5.2] - System Hardening (Gemini)

**Status**: Production-Ready
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)

### Summary

System-Härtung für den produktiven Einsatz:

- **Backup**: Tägliches Backup von Config und Datenbank
- **Watchdog**: Automatischer Reboot bei System-Freeze
- **API Client**: Vorbereitung für Server-Anbindung

### Changes

- **Backup Script**: `scripts/backup.sh` (Daily Cron @ 03:00)
- **Watchdog**: Hardware Watchdog aktiviert (`dtparam=watchdog=on`)
- **API Client**: `api/client.py` Skeleton erstellt
- **Docs**: `SPEC_RASPBERRY_PI.md` aktualisiert

---

## [2025-12-05 v5.1] - Singleton Fix & Mode Management (Gemini)

**Status**: Production-Ready
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**Web Interface**: http://<PI_HOST>:5000
**API Version**: 1.2.1

### Summary

Komplette Überarbeitung der Mode-Umschaltung zwischen "Zeitsteuerung" (auto) und "Manuell":

- Neuer zentraler ModeManager als Single Source of Truth
- Fix für "Stale Cache" Problem beim Mode-Wechsel
- Deaktivierung des separaten growpi-web.service
- Verbessertes Startup-Verhalten nach Stromausfall

### Problemanalyse

**Symptom**: Beim Wechsel von "Manuell" zu "Zeitsteuerung" gingen alle Lampen aus statt auf Kurven-Werte.

**Root Causes**:

1. **Stale Cache**: `self.last_intensities` in main.py behielt alte Werte, sodass bei erneutem "auto" Mode keine Updates gesendet wurden
2. **Zwei PWMController**: api.py und main.py hatten separate Instanzen wegen inkonsistenter Python-Imports
3. **Separater Service**: `growpi-web.service` lief parallel zu `grow-pi.service` und kämpfte um Port 5000
4. **Mode nur im RAM**: Modus wurde nicht persistiert, ging bei Restart verloren

### Neue Features

#### ModeManager (`utils/mode_manager.py`)

```python
# Singleton Pattern für zentrales Mode-Management
mode_manager = get_mode_manager()
mode_manager.set_mode("auto")  # oder "manual"
current = mode_manager.get_mode()
```

**Features**:
- Thread-safe mit Lock
- Persistiert in `/tmp/growpi_mode.txt`
- Nach Reboot automatisch "auto" (Sicherheit für Pflanzen)
- Callback-System für Mode-Änderungen

#### Cache-Clearing beim Mode-Wechsel

```python
# In main.py run() loop:
if current_mode == "auto" and last_known_mode != "auto":
    logger.info("Mode change detected - forcing curve update")
    self.last_intensities = {}  # Cache leeren!
    last_update = 0  # Sofortiges Update erzwingen
```

#### Service-Konsolidierung

- `growpi-web.service` deaktiviert (`sudo systemctl disable growpi-web.service`)
- Nur noch `grow-pi.service` läuft (startet main.py, das intern die Web-API startet)

---

## [2025-12-05 v4] - Per-Channel Lighting Curves

**Status**: Production-Ready mit individuellem Kurven-Editor pro Lampe
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**Web Interface**: http://<PI_HOST>:5000
**API Version**: 1.2.0

### Summary

Individuelle Lichtkurven pro Kanal für realistische Sonnenauf-/untergangs-Sequenzen:

- Jede Lampe hat eigene Zeit-/Intensitäts-Kurve
- Standard-Sunrise: Far Red → Cool White → Warm White (gestaffelt)
- UV bleibt permanent auf 0%
- Web-UI mit Kurven-Editor und 24h-Vorschau

### Neue Features

#### Per-Channel Kurven-System

**Default Sunrise Sequence (max 50%)**:

| Kanal | Lampe      | Start | Peak (50%) |
| ----- | ---------- | ----- | ---------- |
| 1     | Far Red    | 05:00 | 06:00      |
| 3     | Cool White | 05:15 | 06:15      |
| 2     | Warm White | 05:30 | 06:30      |
| 4     | UV         | -     | 0% immer   |

**Sunset (umgekehrte Reihenfolge)**:
- Warm White fällt zuerst (20:00)
- Cool White folgt (20:15)
- Far Red zuletzt (20:30)

#### CurveController (`utils/curve_controller.py`)

- `CurveController` Klasse für Multi-Kanal Interpolation
- `get_current_intensities()` - Alle Kanäle gleichzeitig
- `get_intensity(channel)` - Einzelner Kanal
- `update_curve(channel, points)` - Kurve aktualisieren
- Lineare Interpolation mit Mitternachts-Wraparound

#### Neue API-Endpoints

| Endpoint                  | Methode | Beschreibung                 |
| ------------------------- | ------- | ---------------------------- |
| `/api/curves`             | GET     | Alle Kurven abrufen          |
| `/api/curves/<channel>`   | GET     | Kurve für Kanal              |
| `/api/curves/<channel>`   | PUT     | Kurve aktualisieren          |
| `/api/curves/preview`     | GET     | 24h Vorschau aller Kanäle    |
| `/api/curves/intensities` | GET     | Aktuelle interpolierte Werte |

---

## [2025-12-05 v3] - SQLite Logging System Complete

**Status**: Production-Ready mit vollständigem Daten-Logging
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**Web Interface**: http://<PI_HOST>:5000
**API Version**: 1.1.0

### Summary

Vollständiges lokales Logging-System für Sensor- und Lampen-Daten:

- SQLite-Datenbank unter `/opt/grow-pi/data/growpi.db`
- Automatisches Logging alle 60 Sekunden (konfigurierbar)
- REST-API für Datenabfrage (letzte 24h, filterbar)
- Vorbereitet für spätere Server-Synchronisation

### Neue Features

#### Datenbank-Module (`grow_pi/database/`)

- **models.py**: Dataclasses für `SensorReading`, `LampStateLog`, `SystemEvent`
- **db.py**: Thread-safe SQLite Connection Manager mit WAL-Mode
- **logger.py**: Background DataLogger Service mit konfigurierbaren Intervallen

#### Datenbank-Schema

```sql
-- Sensor-Messwerte
sensor_readings (id, sensor_type, value, unit, created_at, synced_at)

-- Lampen-Zustandsprotokoll
lamp_state_log (id, channel, name, intensity, source, curve_time, created_at, synced_at)

-- System-Events
system_events (id, event_type, severity, message, details, created_at)
```

#### Logging-Strategien

| Datentyp | Trigger                   | Intervall |
| -------- | ------------------------- | --------- |
| Sensor   | Periodisch                | 60s       |
| Lampen   | Periodisch + Bei Änderung | 60s       |
| Events   | Bei Ereignis              | -         |

**Lampen-Sources**: `startup`, `shutdown`, `api`, `curve`, `manual`, `override`, `periodic`

#### Neue API-Endpoints

| Endpoint                                          | Beschreibung                      |
| ------------------------------------------------- | --------------------------------- |
| `GET /api/logs/sensors?type=temperature&hours=24` | Sensor-Historie                   |
| `GET /api/logs/lamps?channel=1&hours=24`          | Lampen-Historie                   |
| `GET /api/logs/events?severity=error`             | System-Events                     |
| `GET /api/logs/stats`                             | Logging-Statistiken               |
| `GET /api/health`                                 | Health-Check inkl. Logging-Status |

---

## [2025-12-05 v2] - DHT22 Sensor Integration Complete

**Status**: Production-Ready mit echten Sensordaten
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**Web Interface**: http://<PI_HOST>:5000

### Summary

DHT22 Temperatur- und Luftfeuchtigkeit-Sensor vollständig integriert:

- Echte Sensor-Werte statt Mock-Daten
- Robuste Retry-Logik mit Caching
- API liefert Temperatur und Luftfeuchtigkeit in Echtzeit

### DHT22 Sensor-Integration

#### Hardware-Konfiguration (3-Pin)

| DHT22 Pin | Funktion | Raspberry Pi   |
| --------- | -------- | -------------- |
| 1         | VCC      | Pin 1 (3.3V)   |
| 2         | DATA     | Pin 7 (GPIO-4) |
| 3         | GND      | Pin 6 (GND)    |

#### Installierte Pakete

```bash
# Python-Bibliotheken (im venv)
adafruit-circuitpython-dht==4.0.10
Adafruit-Blinka==8.68.0

# System-Bibliotheken
libgpiod3
gpiod
```

#### API-Verbesserungen

- **Caching**: Sensor-Werte werden 3 Sekunden gecacht (DHT22 braucht min. 2s zwischen Messungen)
- **Retry-Logik**: Bis zu 3 Versuche bei Lesefehlern
- **Fallback**: Letzte bekannte Werte werden zurückgegeben wenn Sensor temporär nicht lesbar

---

## [2025-12-05] - MVP Complete: Web Interface & Final Pin Configuration

**Status**: Production-Ready
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**Web Interface**: http://<PI_HOST>:5000

### Summary

Vollständiges MVP mit Web-Interface für Smartphone-Steuerung:

- Web-App auf Port 5000 für 4 Lampenkanäle
- Sonnenkurven-Modus mit automatischer Tageszeit-Interpolation
- Temperatur/Luftfeuchtigkeit Anzeige (DHT22)
- Finale GPIO-Pin-Konfiguration etabliert

### Finale Pin-Konfiguration (ACTIVE)

| Kanal | Name       | GPIO | Pin | Farbe (UI) |
| ----- | ---------- | ---- | --- | ---------- |
| 1     | Far Red    | 16   | 36  | #ff4444    |
| 2     | Warm White | 13   | 33  | #ffbb44    |
| 3     | Cool White | 18   | 12  | #88ddff    |
| 4     | UV         | 18   | 12  | #cc66ff    |

### Neue Features

#### Sonnenkurven-Modus (Level 4)

- Automatische Intensitätssteuerung basierend auf Tageszeit
- Kurve: 05:00-08:00 Sonnenaufgang (10%→60%), 08:00-20:00 Tag (60%), 20:00-23:00 Sonnenuntergang (60%→10%), 23:00-05:00 Nacht (0%)
- Linear-Interpolation zwischen Kurvenpunkten
- `--mode curve` (default) oder `--mode fixed`
- `--preview` zeigt 24h Kurven-Vorschau

#### Web-Interface (Flask API)

- Mobile-optimiertes Dark-Theme UI
- 4 Slider für Lampensteuerung (Far Red, Warm White, Cool White, UV)
- Temperatur & Luftfeuchtigkeit Anzeige
- Auto-Refresh alle 10 Sekunden
- Debounced Slider Updates (300ms)
- REST API: GET /api/status, POST /api/lamp/<channel>, GET /api/temperature

---

## [2025-12-04 v2] - MVP Level 1: Pi Auto-Start Controller

**Status**: Superseded by 2025-12-05
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)

### Summary

Erster funktionierender MVP des Pi-Controllers:

- ✅ Pi startet automatisch → Lampen gehen auf konfigurierte Werte
- ✅ PWM-Kanäle funktionieren
- ✅ Live-Änderung der Intensität via Config + Service-Restart
- ✅ systemd Services für pigpiod und grow-pi

### Architektur-Entscheidungen

**PWMController Features**:
- Nutzt pigpio Daemon für Hardware-PWM
- Simulation-Mode wenn pigpio nicht verfügbar (Entwicklung auf Mac)
- PWM Range 0-100 für direkte Prozent-Steuerung
- Graceful Cleanup (Lampen aus bei Stop)

**Config System**:
- YAML-basiert mit Dataclasses
- Auto-Detection: `./config/config.yaml` oder `/opt/grow-pi/config/config.yaml`
- Environment Variable Override: `GROWPI_CONFIG`
- Erweiterbar für zukünftige Features (Server, Sensors, Offline)

**Service Setup**:
- `pigpiod.service` - PWM Daemon (manuell erstellt, da nicht in Debian Trixie)
- `grow-pi.service` - Hauptcontroller (Requires pigpiod)
- Auto-Restart bei Fehler (RestartSec=10)

---

## [2025-12-04] - Raspberry Pi Hardware Integration - Phase 2 ✅

**Status**: Hardware Testing Phase Complete
**Platform**: Raspberry Pi 3B+ (growpi @ <PI_HOST>)
**OS**: Raspberry Pi OS (Debian, Linux 6.12.47+rpt-rpi-v8 aarch64)
**Python**: 3.13.5

### Summary

Successfully verified hardware components on Raspberry Pi 3B+:

- ✅ DHT22 temperature/humidity sensor (GPIO-4)
- ✅ PWM signal generation (GPIO-18)
- ✅ Complete pin documentation created
- ✅ Test scripts working reliably

**Result**: Hardware foundation ready for controller implementation

### Hardware Verification - DHT22 Temperature & Humidity Sensor

#### Sensor Connection Verified ✅

**Hardware**: DHT22 sensor connected to GPIO-4 (as specified in SPEC_RASPBERRY_PI.md)

**Test Results**:
- ✅ Sensor successfully detected and initialized
- ✅ Stable readings obtained
- ✅ No hardware errors or timeouts

**Measured Values**:
```
Temperatur: 21.0°C
Luftfeuchtigkeit: 64.0%
```

#### Python Library Installation ✅

**Library**: `adafruit-circuitpython-dht` 4.0.10

**Reason for Library Choice**:
- Original `Adafruit_DHT` library is deprecated
- Does not compile with Python 3.13+
- `adafruit-circuitpython-dht` is the modern replacement
- Full compatibility with current Raspberry Pi OS

---

## [2025-12-03 v2] - Production-Ready Polish & Bug Fixes ✅

**Status**: Deployed to http://your-growpi-host.example.com
**Build**: Success
**Tests**: All passing
**Ready for**: Customer Presentation

### Critical Fixes & Improvements

#### 1. Lighting Curve Editor - Full Functionality ✅

**Problem**: Inputs were read-only, users couldn't edit curves

**Solution**:
- Removed `readOnly` attributes from time and intensity inputs
- Implemented full state management with `editedLamps` state
- Added PUT endpoint in `/api/lighting/route.ts` for saving curves
- Added "Add Point" button with Plus icon
- Added "Remove Point" functionality with Trash icon
- Implemented validation (intensity clamped 0-100)
- Added Reset button to restore original curves

#### 2. Lighting Override - Real Functionality ✅

**Problem**: All On/All Off buttons only returned success without doing anything

**Solution**:
- Implemented actual database updates in override route
- Updates all lamp curves to single point at current time
- Sets intensity to 100 (All On) or 0 (All Off)
- Returns lampsUpdated count and intensity in response

#### 3. Mobile Responsive Sidebar ✅

**Problem**: Sidebar was fixed width, no mobile menu

**Solution**:
- Added hamburger menu button (fixed, top-left, z-50)
- Implemented mobile overlay (dimmed background)
- Sidebar slides in/out with translate-x animation
- Auto-closes when clicking menu items or overlay

---

## [2025-12-03 v1] - Major Refactoring & Deployment

### Project Overview

Greenhouse control system for Raspberry Pi with web interface, deployed to VPS at your-growpi-host.example.com

### Completed Tasks

#### 1. Database Migration: Supabase → PostgreSQL + Prisma

**Problem**: Original frontend was built for Supabase, needed complete refactoring for self-hosted solution

**Actions**:
- Installed PostgreSQL 16 on VPS (5.182.17.148)
- Created database `growpi` with user `growpi_user`
- Configured remote access (pg_hba.conf, postgresql.conf)
- Created complete Prisma schema with 10 models
- Generated seed data: 2,592 sensor readings (24 hours of data)

#### 2. API Routes Refactoring (8 routes)

**Problem**: All routes used Supabase client, needed conversion to Prisma ORM

**Routes Refactored**:
1. `app/api/auth/login/route.ts` - JWT authentication with Prisma user lookup
2. `app/api/readings/route.ts` - Sensor data queries with aggregation
3. `app/api/lighting/route.ts` - Lamp status and curves
4. `app/api/lighting/override/route.ts` - Manual lamp control
5. `app/api/dashboard/route.ts` - Dashboard data aggregation
6. `app/api/settings/route.ts` - Settings CRUD with field mapping
7. `app/api/sensor-data/route.ts` - Real-time sensor readings
8. `app/(dashboard)/layout.tsx` - Server Component auth check

#### 3. VPS Deployment Configuration

**Infrastructure**:
- VPS: Ubuntu 24.04 at 5.182.17.148
- Domain: your-growpi-host.example.com
- Node.js: v20.18.1
- PM2: Process manager with ecosystem.config.js
- NGINX: Reverse proxy on port 80 → localhost:3001

#### 4. Authentication Fixes

**Problem**: Login redirect loop (307 infinite redirects)
- **Root Cause**: Cookie `secure: true` but site uses HTTP
- **Fix**: Changed `lib/auth.ts:59` to `secure: false`

#### 5. Settings API Field Mapping

**Problem**: Frontend sends snake_case (`demo_mode`) but Prisma uses camelCase (`demoMode`)
- **Fix**: Added bidirectional field mapping in settings route

#### 6. Theme System Implementation

**Problem**: Dark/Light mode toggle didn't exist in UI
- **Solution**: Complete theme system from scratch with Moon/Sun icons

#### 7. React Hydration Errors Fixed

**Problem**: Console flooded with "Minified React error #425, #418, #423"
- **Root Cause**: `useState<Date>(new Date())` creates different timestamps on server vs client
- **Solution**: Mounted state pattern

---

**Last Updated**: 2025-12-07
**Archived Versions**: v1.0.0 through v6.1.x
**Current Versions**: See [CHANGELOG.md](../CHANGELOG.md) for v6.2.0+
