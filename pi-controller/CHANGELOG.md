# Changelog

Alle wichtigen Änderungen am GrowPi Pi-Controller werden hier dokumentiert.

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
