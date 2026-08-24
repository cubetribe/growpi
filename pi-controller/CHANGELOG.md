# Changelog

Alle wichtigen Änderungen am GrowPi Pi-Controller werden hier dokumentiert.

## [v6.25.3] - 2026-03-02 - Public Release Hardening & License Update

## [v6.25.4] - 2026-03-06 - Boot Safety & Power Diagnostics

### Fixed
- **Split-Process Cold-Boot Regression**
  - `grow_pi/web/api.py` und `grow_pi/web/app.py` attachen den PWM-Controller jetzt ohne Zero-Init
  - Verhindert, dass `growpi-web` die vom Controller gesetzten Kurvenwerte beim Boot wieder auf 0 setzt
- **PWM Drift Recovery**
  - `grow_pi/main.py` vergleicht Sollwerte jetzt zusätzlich mit dem echten pigpio-Hardwarezustand
  - Bei Abweichungen werden Kurvenwerte erneut auf die GPIOs geschrieben
- **Frontend Bootstrap Crash**
  - `grow_pi/web/static/js/state.js` exportiert `GrowPiState` jetzt korrekt als ES-Modul
  - `grow_pi/web/static/index.html` initialisiert UI-Module defensiv, damit ein einzelner Frontend-Fehler nicht mehr die komplette Web-Oberfläche blockiert

### Added
- **Raspberry Pi Power Diagnostics**
  - Neues Modul `grow_pi/utils/power_monitor.py`
  - `/api/health` enthält jetzt `system.power` mit `vcgencmd get_throttled` Flags
- **Persistent Journald Setup**
  - Neue Drop-In-Datei: `systemd/99-growpi-journald.conf`
  - `install.sh` aktiviert persistente Journale und flush't nach der Installation

### Changed
- `systemd/grow-pi.service` und `systemd/growpi-web.service` verwenden jetzt gültiges `OOMPolicy=kill`

### Validation
- Fokus-Tests für PWM-Attach, Curve-Reconcile und Power-Parsing ergänzt
- Live-Incident-Quick-Fix am Produktions-Pi durchgeführt: Lampenstatus wieder mit Kurvensollwert synchronisiert
- Web-Quick-Fix live verifiziert: UI lädt wieder, Kamera-Preview sichtbar, Status-Badge online

### Security
- **Hardcoded credential fallback entfernt**
  - `grow_pi/utils/tuya_cloud.py` nutzt keine eingebauten Tuya-Cloud-Credentials mehr
  - Cloud-Integration funktioniert nur noch mit gesetzten Umgebungsvariablen (`TUYA_ACCESS_ID`, `TUYA_ACCESS_SECRET`)

### Changed
- `VERSION` auf `6.25.3` erhöht (wird im Frontend über `/api/version` angezeigt)
- Dokumentation auf public/sanitized Stand gebracht (keine internen Host/IP-Werte mehr)
- Lizenzmodell auf Non-Commercial Source-Available umgestellt (siehe Root-`LICENSE`)

## [v6.25.2] - 2026-03-02 - Split-Process Consistency Hardening

### Fixed
- **`/api/status` liefert wieder echte Lampenwerte**
  - Blueprint-Dependencies werden im aktiven `web/api.py` jetzt korrekt initialisiert
  - Status-Endpoint liest den PWM-State pro Request nur einmal und gibt konsistente Kanalwerte zurück
- **Fehler beim PWM-Setzen werden nicht mehr als Erfolg behandelt**
  - `set_lamp` liefert bei fehlgeschlagenem Hardware-Write jetzt einen 500-Fehler
  - Mode-Wechsel (`manual`/`auto`) protokolliert fehlgeschlagene Kanal-Updates statt stillschweigend fortzufahren
- **Auto-Kurven-Update robuster bei Hardwarefehlern**
  - Controller aktualisiert `last_intensities` nur noch bei erfolgreichem PWM-Write
  - Verhindert Cache-Drift zwischen Sollwert und realem Lampenzustand

### Changed
- **Kurven-Intensitäten API aktualisiert Kurven explizit aus DB**
  - `/api/curves/intensities` lädt vor der Berechnung neu aus der Datenbank
  - Erhöht Konsistenz in Split-Process-Szenarien

### Added
- Unit-Tests für Controller-Kurven-Synchronisierung:
  - `tests/unit/test_main_curve_sync.py`
- GitHub Actions Auto-Deploy Unterstützung:
  - `../.github/workflows/pi-autodeploy.yml`
  - `../scripts/pi/github_runner_deploy.sh`
  - `../scripts/pi/install_github_runner.sh`
  - `../docs/GITHUB_ACTIONS_PI_AUTODEPLOY.md`

### Infrastructure
- Self-hosted Runner auf Pi möglich ohne eingehende Ports
- Deployment-Status wird direkt im GitHub Actions Run zurückgemeldet

### Validation
- `venv/bin/python -m pytest -q tests/unit` -> **156 passed**
- `venv/bin/python -m py_compile` auf geänderten Modulen -> **PASS**

## [v6.25.1] - 2026-03-02 - Curve/State Sync Hardening

### Fixed
- **Auto-Kurven nach Process-Splitting synchronisiert**
  - Controller lädt Kurven vor jedem Auto-Update aus der Datenbank nach (`reload_from_database()`)
  - Änderungen aus der Web-UI werden dadurch im Controller-Prozess zuverlässig wirksam
- **Ist-Zustand aus echter Hardware statt Prozess-Cache**
  - `PWMController.get_current_state()` liest bei pigpio die aktuellen Duty-Cycles direkt vom Daemon
  - Web-Status und physischer Lampenzustand bleiben konsistent auch bei getrennten Prozessen

### Added
- Unit-Tests für PWM-State-Synchronisierung:
  - `tests/unit/test_pwm_controller_state_sync.py`

---

## [v6.25.0] - 2026-03-02 - Process Splitting & Runtime Hardening

### Added
- **Process Splitting (Controller/Web)**
  - `grow-pi.service` läuft jetzt als reiner Controller-Prozess (`python -m grow_pi.main --no-web`)
  - `growpi-web.service` läuft separat als Web/API-Prozess
  - Installer aktiviert beide Services automatisch
- **Cross-Process Mode Synchronization**
  - `ModeManager.get_mode()` synchronisiert den Modus bei Dateiveränderungen (`/run/growpi/mode.txt`)
  - Auto/Manual-Mode bleibt konsistent zwischen Controller- und Web-Prozess

### Changed
- **Lazy Web Import in Controller**
  - `main.py` lädt `grow_pi.web.api` nur noch bei aktiviertem Web-Betrieb
  - Verhindert unnötige Web/Sensor-Initialisierung im Controller-Prozess bei `--no-web`
- **Web Service Hardening**
  - `growpi-web.service`: `Restart=on-failure`, Startlimits, Security-Hardening, kontrollierte Stop-/Start-Timeouts
  - Gemeinsames `RuntimeDirectory=growpi` für prozessübergreifende Runtime-Dateien
- **Deployment Workflow**
  - `install.sh` installiert/aktiviert jetzt `grow-pi.service` und `growpi-web.service`
  - Hardware-Watchdog-Setup bleibt enthalten
- **System Event Logging Robustness**
  - `SystemEvent` validiert `event_type` jetzt schema-basiert statt mit starrer Whitelist
  - Verhindert Laufzeitfehler bei neuen Event-Typen wie `mode_change` und `sensor_reinit`

### Validation
- `pytest -q tests/unit` -> **147 passed**
- `python3 -m py_compile` auf geänderten Kernmodulen -> **PASS**

---

## [v6.24.1] - 2026-02-03 - Cool White Pin Fix

### Fixed
- **PWM pin mapping mismatch**: Channel 3 (Cool White) now drives GPIO-18 / Pin 12 as wired on the production Pi; channel 4 (UV) moves to GPIO-12 / Pin 32. This restores Cool White output and keeps UV available for future use.

### Added
- **Runtime Watchdog Monitor (Controller intern)**
  - Dedizierter Monitor-Thread prüft Main-Loop-Heartbeat und kritische Worker-Komponenten (Web-Thread, DataLogger, Dehumidifier)
  - `WATCHDOG=trigger` bei Teil-Ausfällen, damit systemd sofort neu startet statt den Timeout abzuwarten
  - Watchdog-Ping-Intervall wird dynamisch aus `WATCHDOG_USEC` abgeleitet (50%-Regel)
- **Background Runtime Health Exports**
  - `DataLogger.get_runtime_health()` und `DehumidifierController.get_runtime_health()`
  - `web/api.py:get_runtime_health()` als aggregierter Runtime-Health-Endpoint für den Hauptprozess
- **Hardware Watchdog Setup**
  - Neue systemd-Manager-Drop-in-Datei: `systemd/99-growpi-watchdog.conf`
  - `install.sh` aktiviert Kernel-Watchdog (`dtparam=watchdog=on`) und installiert Manager-Watchdog-Konfiguration

### Changed
- **systemd Unit Hardening (`systemd/grow-pi.service`)**
  - Restart-Policy auf `on-failure` mit schnelleren Recovery-Zyklen
  - Crash-Loop-Schutz mit `StartLimitIntervalSec`, `StartLimitBurst`, `StartLimitAction=reboot-force`
  - Zusätzliche Sicherheits- und Laufzeitgrenzen (`ProtectSystem`, `ProtectHome`, `PrivateTmp`, `TasksMax`, `OOMPolicy=restart`)
- **Web API Standalone Start**
  - Direktstart (`python -m grow_pi.web.api`) läuft jetzt stabil ohne Debug-Reloader (`debug=False`, `use_reloader=False`)

### Validation
- Unit-Tests ergänzt:
  - `tests/unit/test_systemd_watchdog.py`
  - `tests/unit/test_datalogger_runtime_health.py`
- Testlauf: `147 passed` (`pytest -q tests/unit`)

### Documentation
- Updated pin tables in `README.md`, `docs/HARDWARE_PINOUT.md`, `docs/SPEC_RASPBERRY_PI.md`, and `CLAUDE.md` to prevent future mis-wiring.
- Added `reports/v6.24.1/00-analysis-report.md` to capture the failure investigation.

---

## [v6.23.0] - 2025-12-26 - Tank-Mode Hardening

### Added
- **Circuit Breaker Pattern für DHT22 Sensor** (pybreaker)
  - Automatische Abschaltung nach 5 Fehlern
  - 30 Sekunden Erholungszeit, dann Auto-Recovery
  - Graceful Degradation mit Cache-Fallback
  - Process Isolation verhindert kompletten System-Freeze
- **Health Check API Endpoints** (Observability Layer)
  - `GET /api/health/` - Comprehensive Health Check (mit System-Metriken)
  - `GET /api/health/ready` - Kubernetes Readiness Probe
  - `GET /api/health/live` - Kubernetes Liveness Probe
  - `GET /api/health/metrics` - Prometheus-Style Metriken
- **Incident Snapshot System**
  - Automatische Snapshots bei kritischen Fehlern
  - Speicherort: `/var/log/grow-pi/incidents/`
  - Enthält: Sensor-Status, DB-Status, Thread-Info, System-Metriken
  - Auto-Cleanup (max 100 Snapshots)
- **Structured Logging Utilities**
  - Log-Formatter mit Thread-Info und Modul-Namen
  - Severity-basierte Farbcodierung
  - JSON-Export-Option für Log-Aggregation
- **systemd Watchdog Integration**
  - Service Type: `notify` mit `WatchdogSec=60`
  - Watchdog-Ping-Intervall: 30 Sekunden
  - Automatischer Service-Restart bei Hang (SIGKILL nach 60s)
  - sd_notify Integration (READY, WATCHDOG, STOPPING)

### Changed
- **Database Robustness**
  - SQLite Connect Timeout: 5s → 30s
  - Retry-on-Busy mit exponential backoff (3 Retries, 100ms base delay)
  - atexit Handler für sauberes Connection Cleanup
- **Thread-Safety Improvements**
  - Sensor Cache: Alle Operationen jetzt thread-safe (RLock)
  - Mode Manager: Thread-safe get/set Operations (Lock)
  - PWM State: Thread-safe State Save/Load (Lock + fcntl file lock)
  - Lock Ordering Convention dokumentiert (Cache → Mode → PWM)
- **DataLogger Robustness**
  - Event-basiertes Warten statt busy loops (`threading.Event.wait()`)
  - 5 Retries pro Loop-Iteration mit exponential backoff
  - Graceful Degradation bei Fehlern (System läuft weiter)
  - System-Events für persistente Fehler

### Fixed
- **Race Conditions** in sensor_cache.py eliminiert
- **Potential Deadlocks** in mode_manager.py verhindert
- **Database Connection Leaks** bei ungraceful Shutdown
- **Sensor Freeze Bug** - DHT22 Freeze blockiert nicht mehr gesamtes System

### Dependencies
- **pybreaker>=1.0.1** (NEU) - Circuit Breaker Pattern
- **psutil>=5.9.0** (bereits vorhanden) - System-Metriken

### Technical Debt Reduction
- Alle kritischen Code-Pfade jetzt thread-safe
- Lock Ordering Convention dokumentiert (verhindert Deadlocks)
- Per-Thread SQLite Connections (threading.local())
- Comprehensive Error Recovery Strategies

### Deployment-Hinweise
Nach Update auf v6.23.0:
1. Neue Dependencies installieren: `pip install pybreaker>=1.0.1`
2. systemd Service-Datei aktualisieren: `sudo cp systemd/grow-pi.service /etc/systemd/system/`
3. systemd neu laden: `sudo systemctl daemon-reload`
4. Service neu starten: `sudo systemctl restart grow-pi`
5. Watchdog verifizieren: `journalctl -u grow-pi -f | grep "Watchdog"`
6. Health Check testen: `curl http://localhost:5000/api/health`

### Breaking Changes
Keine - vollständig rückwärtskompatibel

---

## [v6.22.0] - 2025-12-20

### Added
- **Pi Health Monitoring Dashboard Widget**
  - Live System-Metriken: CPU-Temperatur, RAM, Disk, Uptime
  - Farbcodierte Status-Anzeigen (normal/warning/critical)
  - API-Endpoint `/api/health` erweitert mit `system` Object
  - Frontend-Modul `health.js` mit Auto-Refresh (30s)
  - Schwellwerte: CPU <60°C, RAM <70%, Disk <70%
- **TinyTuya Lokale Steuerung**
  - Scan auf Pi ausgeführt (4 Tuya-Geräte gefunden)
  - Lokale Verbindung getestet (Main Light: 109.6W @ 233.2V)
  - `devices.json` auf Pi aktualisiert (ANTELA: BLE → WiFi)
- **Timelapse Auto-Enable**
  - Bei Service-Neustart wird Timelapse automatisch aktiviert
  - Standard-Intervall: 600 Sekunden (10 Minuten)
  - Verhindert manuelle Konfiguration nach jedem Reboot

### Changed
- **Performance-Optimierungen**
  - Cache-TTL reduziert: 60s → 10s (bessere Responsiveness bei lokaler Steuerung)
  - Plug-Polling-Intervall: 60s (jede Minute Stromerfassung)
  - System-Metriken-Cache mit 30s TTL (reduziert psutil-Calls)
- **Version-Management**
  - `dependencies.py` lädt Version jetzt dynamisch aus VERSION-Datei
  - Keine hardcodierte Version mehr

### Fixed
- Tuya Cloud API Quota-Limit umgangen durch lokale TinyTuya-Steuerung
- Version-Anzeige im Frontend jetzt konsistent mit VERSION-Datei

### Dependencies
- `psutil` (v5.9.6+) für System-Metriken
- `tinytuya` (v1.14.1) für lokale Tuya-Steuerung

### Deployment-Hinweis
Nach Änderungen an der VERSION-Datei oder Code-Updates:
1. Dateien auf Pi übertragen
2. Service neu starten: `sudo systemctl restart grow-pi`
3. Browser Hard-Refresh (Cmd+Shift+R / Strg+Shift+R) für Frontend-Version-Anzeige

---

## [v6.21.1] - 2025-12-20

### Fixed
- **DHT22 Sensor Robustness**
  - 5 Retry-Versuche bei Sensor-Initialisierung (nach Hard-Reset)
  - Cache-Invalidierung nach 3 aufeinanderfolgenden Fehlern
  - Sauberes Sensor-Cleanup bei Service-Shutdown (`sensor.exit()`)
  - System-Events für Sensor-Ausfälle (`sensor_read_failure`, `sensor_persistent_error`)

### Known Issues
- **Tuya Smart Plug API**: Quota-Limit erreicht (Error 28841004)
  - Ursache: Polling-Intervall zu aggressiv (60s)
  - Workaround: Lokale Steuerung über `python-kasa` oder `tinytuya` geplant

---

## [v6.21.0] - 2025-12-17

### Fixed
- **Calendar DB Schema** - `get_connection()` Context Manager für saubere DB-Verbindungen
- Database Locking Issues behoben

---

## [v6.20.0] - 2025-12-17

### Added
- **Grow Calendar** mit Phase Tracking
  - Grow-Phasen: Keimung, Vegetation, Blüte, Ernte
  - Milestones mit Datum und Beschreibung
  - Timeline-Visualisierung im Web-Interface
  - API Endpoints: `/api/calendar/*`

---

## [v6.19.0] - 2025-12-10

### Changed
- **Camera YUYV Format** für bessere Timelapse-Qualität
  - Umstellung von MJPEG auf YUYV Raw-Format
  - Höhere Bildqualität bei gleichem Speicherverbrauch
  - Optimierte Kompression für Timelapse-Aufnahmen

---

## [v6.18] - 2025-12-09

### Added
- **Kamera Auto-Detection**
  - `find_lifecam_device()` findet USB-Webcam dynamisch
  - Nutzt v4l2-ctl für Device-Erkennung by name
  - Fallback auf OpenCV Probing (video0/1/2)
  - Default `device_id: -1` triggert Auto-Detection
- **Separate JPEG-Qualitäten**
  - `preview_jpeg_quality: 70` (Live-Preview)
  - `timelapse_jpeg_quality: 95` (Timelapse-Fotos)

### Changed
- Preview FPS: 10 → 2 (Resource-friendly)
- CameraConfig: `device_id` default 0 → -1

### Fixed
- USB-Webcam wechselt nicht mehr Device nach Reboot

---

## [v6.17] - 2025-12-08

### Added
- **Timelapse mit Dunkelheits-Erkennung**
  - Automatische Bildaufnahme in Intervallen
  - Brightness Detection Algorithm
  - Datum-basierte Ordnerstruktur
- **Humidity Auto-Control Fix**
  - `start_dehumidifier_controller()` wird jetzt korrekt aufgerufen

---

## [v6.16] - 2025-12-08

### Fixed
- **Humidity Control Bug** - MANUAL Override jetzt zuverlässig

---

## [v6.15] - 2025-12-07

### Added
- **Bezier Curve Editor** - Interaktiver Kurven-Editor

---

## [v6.14] - 2025-12-07

### Fixed
- **Room Control** - Plug Verification & MANUAL Override

---

## [v6.7] - 2025-12-06

### Performance
- **CPU-Optimierung Phase 2**: Reduzierung von ~75% auf ~28% CPU-Last
  - Kamera-Polling von 500ms auf 10s erhöht (weniger Snapshot-Anfragen)
  - Main-Loop Sleep von 1s auf 5s erhöht
  - DataLogger Sleep-Loops durch `threading.Event.wait()` ersetzt
  - Logging-Intervalle von 60s auf 120s erhöht
  - DHT22 Cache von 3s auf 30s erhöht

### Changed
- `camera.js`: Refresh-Intervall 500ms → 10s
- `main.py`: Main-Loop Sleep 1s → 5s
- `logger.py`: Event-basiertes Warten, Intervalle 120s
- DHT22 Cache auf 30s in allen relevanten Dateien

---

## [v6.5] - 2025-12-06

### Added
- **Live-Kamera Livestream** auf der Start-Seite
  - USB-Webcam Support (Microsoft LifeCam HD-3000 getestet)
  - 1280x720 Auflösung (720p)
  - ~2 FPS Polling für Live-Ansicht
  - Automatische 180° Rotation (Kamera kopfüber montiert)
  - Status-Badge zeigt Auflösung an
- Neuer Camera-Service (`grow_pi/utils/camera.py`)
  - OpenCV-basierte Snapshot-Capture
  - MJPEG-Format für effiziente Übertragung
  - Timelapse-Grundstruktur vorbereitet
- API-Endpoints:
  - `GET /api/camera/snapshot` - JPEG-Bild abrufen
  - `GET /api/camera/status` - Kamera-Status (Verfügbarkeit, Auflösung)
  - `POST /api/camera/config` - Kamera-Konfiguration
  - `GET/POST /api/camera/timelapse/config` - Timelapse-Einstellungen
- Frontend Camera-Modul (`js/modules/camera.js`)
- Tab "Steuerung" umbenannt zu "Start"

### Dependencies
- `opencv-python-headless` hinzugefügt

---

## [v6.4] - 2025-12-06

### Added
- **Room Environment Tab** für Raumklima-Steuerung
  - Live-Anzeige von Temperatur und Luftfeuchtigkeit
  - Entfeuchtungssteuerung via Tuya Smart Plug
  - Konfigurierbare Schwellwerte (Hysterese-Logik)
- Tuya Cloud API Integration für Smart Plugs

---

## [v6.3] - 2025-12-06

### Added
- **Kosten-Tab** mit Energieverbrauchsberechnung
  - Tages-, Wochen-, Monatsansicht
  - Benutzerdefinierter Zeitraum
  - Konfigurierbare kWh-Preise
- Smart Plug Stromverbrauchsmessung

---

## [v6.2] - 2025-12-05

### Added
- **Verlauf-Tab** mit historischen Daten
  - Temperatur/Luftfeuchtigkeit Charts
  - Lampen-Intensitäts-Charts
  - Stromverbrauchs-Charts
  - System-Event-Logs
- SQLite Datenbank für Logging
- Zeitraum-Auswahl (1h, 24h, 7d, 30d)

---

## [v6.1] - 2025-12-05

### Added
- **Kurven-Tab** mit grafischem Editor
  - Per-Kanal Kurveneditor
  - Zeitpunkte hinzufügen/entfernen
  - JSON-Import/Export
  - Live-Preview der Kurven

---

## [v6.0] - 2025-12-05

### Added
- **Web-Interface** (Flask-basiert)
  - Mobile-optimiertes Design (Dark Theme)
  - Temperatur/Luftfeuchtigkeit Live-Anzeige
  - 4-Kanal Lampensteuerung mit Slidern
  - Auto/Manuell Modus-Umschaltung
- REST API für alle Steuerungsfunktionen
- Modular strukturiertes Frontend (ES6 Modules)

---

## [v5.0] - 2025-12-05

### Added
- **DHT22 Temperatursensor** auf GPIO 4
- Kurven-Interpolation für Sonnensimulation
- CurveController mit linearer Interpolation
- Mode-Manager (auto/manual)

---

## [v4.0] - 2025-12-04

### Added
- **4-Kanal PWM LED-Steuerung**
  - Far Red (GPIO 16)
  - Warm White (GPIO 13)
  - Cool White (GPIO 12)
  - UV (GPIO 18)
- pigpio-basierte PWM (Hardware-PWM)
- YAML-Konfiguration

---

## [v1.0] - 2025-12-03

### Added
- Initiales Projekt-Setup
- Grundstruktur für Pi-Controller
- Systemd Service-Integration
