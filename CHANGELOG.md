# GrowPi Project Changelog

All notable changes to the GrowPi project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [6.25.3] - 2026-03-02

### Added
- `LICENSE` with custom terms:
  - private/personal non-commercial use is free
  - commercial/professional use requires prior permission from rights holder

### Changed
- Root `README.md` rewritten for public repository release readiness:
  - consistent architecture/runtime description
  - explicit CI/CD (GitHub Actions -> Raspberry Pi runner) documentation
  - explicit source-available license note
- Public metadata cleanup in docs/examples:
  - internal host/IP values replaced with placeholders
  - internal agent/refactoring/report artifacts removed from tracked content

### Security
- Removed hardcoded Tuya cloud credential fallback from `pi-controller/grow_pi/utils/tuya_cloud.py`
- Tuya cloud integration now requires env vars only (`TUYA_ACCESS_ID`, `TUYA_ACCESS_SECRET`)

---

## [6.25.2] - 2026-03-02

### Added
- **GitHub Actions Auto-Deploy to Raspberry Pi**
  - New workflow: `.github/workflows/pi-autodeploy.yml`
  - New deploy script: `scripts/pi/github_runner_deploy.sh`
  - New setup helper: `scripts/pi/install_github_runner.sh`
  - New documentation: `docs/GITHUB_ACTIONS_PI_AUTODEPLOY.md`

### Changed
- README updated with current version and CI/CD deployment flow
- `.gitignore` updated to ignore local agent/report artifact folders

### Infrastructure
- Self-hosted GitHub Actions runner installed on Raspberry Pi (`growpi-01`, labels: `growpi,prod`)
- Deploy feedback now comes directly from Pi execution logs in GitHub Actions
- No inbound ports required (outbound HTTPS from runner only)

---

## [6.24.1] - 2026-02-03

### Fixed
- **PWM pin mapping**: Cool White (channel 3) now drives GPIO-18 / Pin 12; UV (channel 4) uses GPIO-12 / Pin 32. This matches the physical wiring on the production Pi so the Cool White channel responds again.

### Updated
- Documentation (`README.md`, `CLAUDE.md`, `docs/HARDWARE_PINOUT.md`, `docs/SPEC_RASPBERRY_PI.md`) refreshed to reflect the corrected wiring.
- Added troubleshooting report for v6.24.1 in `reports/v6.24.1/`.

---

## [6.24.0] - 2025-12-29

### Fixed
- **CRITICAL: DHT22 Sensor Freeze Bug** - `_direct_sensor_read()` now uses timeout-protected `_read_dht22_with_timeout()` to prevent blocking calls from freezing the entire service
- Root cause: Direct sensor access (`_dht_sensor.temperature`) could block forever if sensor hardware froze
- Fix: Delegate to existing process-isolated read with 5-second timeout and force-kill

### Technical Details
- Changed `_direct_sensor_read()` in `sensor_cache.py` to call `_read_dht22_with_timeout()`
- The timeout-protected function was already implemented in v6.22.5 but never used
- Circuit breaker can now properly count timeouts as failures
- System automatically recovers after sensor freeze (no manual reboot needed)

### Files Changed
- `pi-controller/grow_pi/utils/sensor_cache.py` - Use timeout-protected read

---

## [v6.21.0] - 2025-12-16

### Added
- **Ereignisliste (Milestones) für Kalender** 📅
  - Liste aller System-Milestones für aktuelle Phase (Keim/Wachstum/Blüte)
  - Tag-Range Anzeige (z.B. "Tag 15-21: Zweite Schwazze")
  - Category-Farben am linken Border (Training=Blau, Environment=Grün, etc.)
  - Toggle-Switch zum Ein-/Ausschalten einzelner Events
  - "+ Neues Event" Button für Custom Milestones
  - Custom Events löschen (System-Events sind geschützt)

- **Add Event Modal**
  - Titel, Beschreibung, Icon eingeben
  - Tag-Range (Ab Tag / Bis Tag) festlegen
  - Category-Auswahl (Training/Environment/Nutrients/Observation/Other)
  - Validierung und Fehlerbehandlung

### Technical Details
- `calendar.js`: +175 LOC (loadPhaseEvents, renderEventsList, toggleEvent, deleteEvent)
- `api.js`: +24 LOC (createMilestone, deleteMilestone)
- `calendar.css`: +178 LOC (Events Section, Toggle Switch, Event Items)
- `index.html`: +46 LOC (Events Section HTML, Add Event Modal)

### Files Modified
- `pi-controller/grow_pi/web/static/js/modules/calendar.js`
- `pi-controller/grow_pi/web/static/js/api.js`
- `pi-controller/grow_pi/web/static/css/calendar.css`
- `pi-controller/grow_pi/web/static/index.html`

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ⏳ User-Test ausstehend

---

## [v6.20.0] - 2025-12-16

### Added
- **Grow Calendar Status Dashboard** 📊
  - Große Tag-Anzeige: "Tag X" der aktuellen Phase (48px, Neon Green)
  - Phase-Info mit Icon und Namen (🌱 Keim / 🌿 Wachstum / 🌸 Blüte)
  - Grow-Startdatum und Phase-Startdatum sichtbar
  - Responsives Grid-Layout (3-spaltig Desktop, 1-spaltig Mobile)

- **Grow-Einstellungen Modal** ⚙️
  - Grow-Name und Sorte editierbar
  - Grow-Startdatum änderbar (HTML5 Date-Picker)
  - Phase-Startdatum änderbar (z.B. "Blüte begann am...")
  - Automatische Neuberechnung des aktuellen Tags
  - Smart-Saving: Nur geänderte Felder werden gesendet

### Changed
- **Backend API erweitert (calendar_bp.py):**
  - `GET /api/calendar/grows` liefert jetzt `phase_day` (berechneter Tag der Phase)
  - `PUT /api/calendar/grows/<id>` akzeptiert `start_date` und `phase_started_at`
  - Validierung: Datum darf nicht in der Zukunft liegen
  - phase_events Tabelle wird automatisch synchronisiert

### Technical Details
- `calendar_bp.py`: +68 LOC (phase_day Berechnung, Datum-Editierung)
- `calendar.js`: +150 LOC (Status Dashboard, Settings Modal)
- `calendar.css`: +120 LOC (Dashboard Styling, Responsive)
- `index.html`: +60 LOC (Dashboard HTML, Settings Modal HTML)

### Fixed
- Deployment: Fehlende Python-Module (tinytuya, python-dotenv) auf Pi installiert
- venv auf Pi neu erstellt wegen macOS-Symlink-Problemen

### Files Modified
- `pi-controller/grow_pi/web/blueprints/calendar_bp.py`
- `pi-controller/grow_pi/web/static/index.html`
- `pi-controller/grow_pi/web/static/js/modules/calendar.js`
- `pi-controller/grow_pi/web/static/css/calendar.css`

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ⏳ User-Test ausstehend

---

## [v6.19.0] - 2025-12-09

### Fixed
- **Camera Quality**: Umstellung von MJPEG auf YUYV Format für deutlich bessere Timelapse-Bildqualität
  - Problem: Doppel-Kompression (Kamera MJPEG → OpenCV → JPEG) reduzierte Qualität auf ~50%
  - Lösung: YUYV (unkomprimiert) vermeidet erste Kompression
  - Erwartete Verbesserung: +20-50% Bildqualität
  - Fallback auf MJPEG falls YUYV nicht unterstützt
  - Datei: `pi-controller/grow_pi/utils/camera.py` (Zeile 147-157)

### Technical Details
- **MJPEG Problem:**
  - Kamera komprimiert mit ~50-80% Qualität (hardcoded)
  - OpenCV dekodiert und re-encodiert mit 95%
  - Effektive Qualität: 0.5 * 0.95 = 47.5% (worst case)

- **YUYV Lösung:**
  - Unkomprimiertes YUV422 Format
  - Keine Kamera-seitige Kompression
  - Nur 1x JPEG-Encoding mit 95% Qualität
  - Nachteile: Höhere USB-Bandbreite (akzeptabel für Timelapse)

- **Fallback Logic:**
  - Versucht YUYV zu setzen
  - Prüft ob Kamera Format akzeptiert hat
  - Log: "Camera using YUYV format (uncompressed) for better quality"
  - Falls nicht: "YUYV not supported, falling back to MJPEG"

### Deployment
- ⏳ Wartet auf User-Genehmigung

---

## [v6.18.0] - 2025-12-09

### Added
- **Kamera Auto-Detection** 📹
  - Findet USB-Webcam automatisch unabhängig von Device-Nummer
  - `find_lifecam_device()` sucht nach LifeCam HD-3000 via v4l2-ctl
  - Fallback: Probiert /dev/video0, video1, video2 durch
  - CameraConfig: `device_id: -1` triggert Auto-Detection
  - Problem behoben: USB-Kamera wechselt Device-Nummer nach Reboot/Reconnect

- **Separate JPEG-Qualitätseinstellungen**
  - `preview_jpeg_quality: 70` - Für Live-Preview (ressourcenschonend)
  - `timelapse_jpeg_quality: 95` - Für Zeitraffer-Fotos (hohe Qualität)

### Changed
- **Preview FPS Optimierung**
  - FPS reduziert: 10 → 2 (90% weniger Ressourcenverbrauch)
  - Live-Preview bleibt smooth trotz niedriger Polling-Rate

- **CameraConfig Defaults**
  - `device_id`: 0 → -1 (Auto-Detection)
  - `preview_fps`: 10 → 2 (Resource-friendly)

### Fixed
- **Kamera-Ausfall nach Reboot/USB-Reconnect** - Root Cause behoben
  - Problem: USB-Webcam wechselte von /dev/video0 zu /dev/video1
  - Kurz-Fix: device_id von 0 auf 1 (funktioniert nur bis nächster Reboot)
  - Permanenter Fix: Auto-Detection findet Kamera dynamisch
  - Datei: `pi-controller/grow_pi/utils/camera.py`

### Technical Details
- `find_lifecam_device()`: 80 Zeilen Python (v4l2-ctl Integration)
- Subprocess Timeout: 5s (verhindert Blocking)
- Regex Pattern: `/dev/video(\d+)`
- Fallback-Chain: Name Detection → v4l2-ctl → OpenCV Probe → Default 0

### Deployment
- ⏳ Wartet auf User-Genehmigung

---

## [v6.17.0] - 2025-12-08

### Added
- **Timelapse Kamera mit Dunkelheits-Erkennung** 📸
  - Automatische Bildaufnahme in konfigurierbaren Intervallen (30s - 10min)
  - Intelligente Dunkelheits-Erkennung: Bilder werden nur gespeichert wenn ausreichend Licht vorhanden
  - Bilder nach Datum in Ordnern organisiert (`/timelapse/YYYY-MM-DD/`)
  - "Helligkeit testen" Button für Kalibrierung
  - JPEG-Format für spätere Zeitraffer-Video-Erstellung

- **Timelapse UI im Room-Tab**
  - Toggle: Timelapse aktivieren/deaktivieren
  - Intervall-Konfiguration (30-600 Sekunden)
  - Helligkeitsschwelle einstellbar (0-255)
  - Dunkle Bilder überspringen Toggle
  - Speicher-Info (MB + Anzahl Bilder)
  - Bilder-Galerie mit Lightbox-Vorschau
  - Ordner-Filter nach Datum

### New API Endpoints
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/camera/timelapse/stats` | GET | Statistiken (Config, Speicher, Counts) |
| `/api/camera/timelapse/folders` | GET | Liste der Datum-Ordner |
| `/api/camera/timelapse/images` | GET | Bilder-Liste (mit ?date= Filter) |
| `/api/camera/timelapse/image/<folder>/<file>` | GET | Einzelbild ausliefern |
| `/api/camera/timelapse/test-brightness` | GET | Helligkeit testen |

### New Files
- `timelapse.js` (~320 Zeilen) - Frontend-Modul
- CSS: ~400 Zeilen für Timelapse-Section und Galerie

### Technical Details
- **Brightness Detection Algorithm:**
  - Konvertiert Frame zu Graustufen
  - Berechnet Durchschnittshelligkeit (0-255)
  - Zählt Prozent "heller" Pixel über Schwellwert
  - Bild wird übersprungen wenn: avg < threshold ODER bright_pixels < min_percent

- **Default-Werte:**
  - `brightness_threshold`: 15 (0-255)
  - `min_bright_pixels_percent`: 10%
  - `interval_seconds`: 300 (5 Minuten)
  - `max_images`: 1000 (Auto-Cleanup)

- **Security:**
  - Directory Traversal Protection mit Regex-Validierung
  - Sanitized Pfade für Bildauslieferung

### Deployment
- ⏳ Wartet auf User-Genehmigung

---

## [v6.16.0] - 2025-12-08

### Fixed
- **KRITISCH: Bug #11 - Entfeuchtung schaltet nicht aus** 🚨
  - Problem: MANUAL Override wurde durch min_run_time blockiert
  - Root Cause: MANUAL Bypass kam NACH min_run_time Check (Zeile 644)
  - Fix: MANUAL Bypass jetzt VOR allen Timing Constraints
  - Ergebnis: MANUAL kann IMMER durchkommen, keine Blockierung mehr

- **Emergency Override bei kritischer Luftfeuchtigkeit**
  - Auto-Shutdown bei Humidity < 85% des low_threshold
  - Beispiel: threshold_low=55% → Emergency bei < 46.75%
  - Bypassed min_run_time für SAFETY

### Changed
- **Schnellere Reaktionszeit**
  - min_run_time Default: 300s → 60s
  - Schnellere Reaktion auf Luftfeuchtigkeit-Änderungen

- **API Cleanup - 21% Reduktion** 🧹
  - api.py: 1516 → 1192 Zeilen (-324 LOC)
  - Dehumidifier Legacy-Routen → dehumidifier_bp.py
  - Costs Legacy-Routen → costs_bp.py
  - Curves Legacy-Routen → curves_bp.py
  - Sauberere Blueprint-Architektur

### Technical Details
- `dehumidifier_controller.py`:
  - MANUAL Bypass jetzt in Zeile 644 (VOR min_run_time)
  - Emergency Override bei < 85% threshold_low
  - min_run_time Default: 60s
- `api.py`:
  - 9 Legacy-Routen entfernt/auskommentiert
  - Blueprints vollständig übernommen

### Deployment
- ⏳ Wartet auf User-Genehmigung

---

## [v6.15.0] - 2025-12-07

### Added
- **Interactive Bezier Curve Editor** 🎨
  - Ersetzt statische 24h-Vorschau durch interaktiven Editor
  - Draggable Keyframe Anchor Points
  - Catmull-Rom zu Bezier Konvertierung für glatte Kurven
  - Touch + Mouse Support
  - Fullscreen-Modus für Mobile

### New Files
- `curve-editor.js` (~950 Zeilen) - Editor-Logik
- `curve-editor.css` (~400 Zeilen) - Styles

### Known Issues
- 🟡 Smartphone UI-Probleme - Layout muss noch optimiert werden

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ Grundfunktionalität getestet

---

## [v6.14.0] - 2025-12-07

### Fixed
- **KRITISCH: Bug #9 + #10 - Room Steuerung funktioniert jetzt zuverlässig** 🎉
  - Bug #9: `SmartPlugController.turn_on()/turn_off()` verifiziert jetzt den Erfolg
    - Nach Schaltbefehl wird 0.4s gewartet und Status abgefragt
    - Nur bei verifiziertem Status wird `True` zurückgegeben
    - Gilt für WiFi (Local) und Cloud (BLE) Geräte
  - Bug #10: Manuelle Steuerung sendet jetzt IMMER den Befehl
    - Vorher: `if target_on == self._is_on: return None` blockierte Befehle
    - Jetzt: Bei `TriggerType.MANUAL` wird IMMER geschaltet
    - `min_run_time`/`min_off_time` werden bei MANUAL übersprungen

### Changed
- `smart_plug_controller.py`: `turn_on()`/`turn_off()` mit Verifikation
- `dehumidifier_controller.py`: `_ensure_state()` mit MANUAL Override-Logik

### Logs
```
Successfully turned ON bfc705014c6241667avzn8 (Cloud, verified)
Dehumidifier ON (trigger: manual, manual on)
Successfully turned OFF bfc705014c6241667avzn8 (Cloud, verified)
Dehumidifier OFF (trigger: manual, manual off)
```

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ Service neugestartet
- ✅ Manuelles Schalten funktioniert

---

## [v6.13.0] - 2025-12-07

### Fixed
- **KRITISCH: Bug #8 - Room Automation Status-Desync** 🔧
  - Problem: Controller speicherte internen Status, synchronisierte aber nie mit echtem Tuya-Gerätestatus
  - Wenn Gerät manuell/physisch geschaltet wurde, wusste der Controller nichts davon
  - Automation schaltete nicht zuverlässig

### Added
- **Neue Methode `_sync_device_status()`** in DehumidifierController
  - Fragt echten Tuya-Status vor jedem Schaltvorgang ab
  - Synchronisiert internen State mit echtem Gerätestatus
  - Loggt erkannte Desyncs

### Changed
- `_ensure_state()`: Ruft jetzt `_sync_device_status()` ZUERST auf
- `get_status()`: Synchronisiert auch vor API-Response
- Automation sollte jetzt zuverlässig funktionieren

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ Service neugestartet

---

## [v6.12.0] - 2025-12-07

### Added
- **Data Aggregation / Downsampling** für unendliche Datenspeicherung 🎉
  - Alle historischen Daten werden jetzt OHNE Limit gespeichert
  - Intelligentes Downsampling bei Abfrage (Query-Time):
    - 0-4h: Minutengenau (Rohdaten)
    - 4-24h: 5-Min-Durchschnitt (AVG)
    - 1-7 Tage: 15-Min-Durchschnitt (AVG)
    - 7-30 Tage: 30-Min-Durchschnitt (AVG)
    - >30 Tage: Stündlicher Durchschnitt (AVG)
  - Gilt für alle 3 Datentypen: Klima, Beleuchtung, Stromverbrauch
  - Ermöglicht Jahresansichten ohne Performance-Probleme

### Changed
- `db.py`: 3 neue Methoden für Downsampling-Queries
- `logs_bp.py`: Alle Endpoints nutzen automatisches Downsampling
- `api.js` + `history.js`: Limit-Parameter entfernt

### Fixed
- Stromverbrauch-Chart auf Verlauf-Seite zeigt jetzt alle historischen Daten

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ Service neugestartet

---

## [v6.11.0] - 2025-12-07

### Added
- **Verlauf-Seite: Synchronisierte Zeitfilter** 🎉
  - Alle 3 Charts (Klima, Beleuchtung, Stromverbrauch) zeigen jetzt dieselbe Zeitspanne
  - Neuer "1h" Zeitfilter für Echtzeit-Debugging
  - Chart.js Date-Adapter für echte Zeit-Achsen
  - Automatische Zeiteinheit (Stunden ≤24h, Tage >24h)
  - Fehlende historische Daten als Lücken dargestellt

- **Steckdosen-Namen auf Verlauf-Seite**
  - Zeigt jetzt richtige Namen statt Tuya-IDs (Power, BF, AD1 etc.)
  - Namen werden aus `/api/costs/config` geladen

### Fixed
- **Bug #7: Zeitfilter funktionierten nicht für alle Charts**
  - Vorher: Nur Klima-Chart reagierte auf Zeitfilter
  - Jetzt: Alle 3 Charts synchron mit gleicher X-Achse

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ history.js komplett überarbeitet
- ✅ Chart.js Date-Adapter hinzugefügt

---

## [v6.10.0] - 2025-12-07

### Added
- **Multi-Line Preview Chart** für Kurven-Seite 🎉
  - SVG-basiertes Linien-Chart statt Balken-Chart
  - Alle 4 Kanäle gleichzeitig sichtbar (Far Red, Warm White, Cool White, UV)
  - Farbige Linien mit Kanalfarben
  - Checkboxen zum Ein-/Ausblenden einzelner Kanäle
  - X-Achse: 00:00 - 24:00 mit Zeitlabels
  - Y-Achse: 0% - 100% mit %-Labels
  - Grid-Linien für bessere Lesbarkeit
  - localStorage Persistenz für Checkbox-Status
  - Responsive Design für Mobile

- **Kurven-Accordion** für bessere Übersicht
  - Alle 4 Lampen-Kanäle standardmäßig zugeklappt
  - Kanalname + aktuelle Intensität im Header sichtbar
  - Klick auf Header klappt auf/zu
  - Enable/Disable Toggle weiterhin funktional
  - localStorage Persistenz pro Kanal
  - Smooth CSS Animation
  - ARIA Keyboard Accessibility

### Fixed
- **Bug #6: Kurven-Presets** - `applySelectedPreset()` verbessert
  - Fallback zu `fetchCurves()` wenn Response leer
  - `updateLocalPreview()` nach Apply für sofortiges Feedback

### Changed
- Preview-Section Titel: "24h Vorschau" statt "Vorschau"
- Checkbox-basierte Kanalauswahl statt Tab-Wechsel

### Deployment
- ✅ Deployed auf Pi @ <PI_HOST>
- ✅ Multi-Line Chart funktioniert
- ✅ Accordion funktioniert
- ✅ Preset-Fix deployed

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
- ✅ Deployed auf Pi @ <PI_HOST>
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
- ✅ Deployed auf Pi @ <PI_HOST>
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
- User-validated on Pi @ <PI_HOST> ✅

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

**Projekt**: GrowPi Raspberry Pi Greenhouse Controller
**Rechteinhaber**: Dennis Westermann
**Lizenz**: GrowPi Non-Commercial License v1.0
**Plattform**: Raspberry Pi 3B+ + optional VPS/CI Integration
