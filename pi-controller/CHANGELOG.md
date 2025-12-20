# Changelog

Alle wichtigen Änderungen am GrowPi Pi-Controller werden hier dokumentiert.

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
