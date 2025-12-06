# Changelog

Alle wichtigen Änderungen am GrowPi Pi-Controller werden hier dokumentiert.

## [v6.6] - 2025-12-06

### Performance
- **CPU-Optimierung**: Reduzierung von ~75% auf ~15-25% CPU-Last
  - Sleep-Loops durch `threading.Event.wait()` ersetzt (3 DataLogger Threads)
  - Eliminiert ~180 unnötige OS-Kontextwechsel pro Minute
  - Logging-Intervalle von 60s auf 120s erhöht (Sensor, Lampen, Plugs)
  - DHT22-Sensor Cache von 3s auf 30s erhöht

### Changed
- `grow_pi/database/logger.py`:
  - Neues `_stop_event` für CPU-effizientes Thread-Warten
  - `sensor_interval`: 60s → 120s
  - `lamp_interval`: 60s → 120s
  - For-Loops mit `time.sleep(1)` durch `Event.wait(timeout=interval)` ersetzt
- `grow_pi/web/api.py`: `DHT_CACHE_SECONDS`: 3 → 30
- `grow_pi/web/services/hardware_service.py`: `DHT_CACHE_SECONDS`: 3 → 30
- `grow_pi/web/blueprints/temperature_bp.py`: `DHT_CACHE_SECONDS`: 3 → 30

### Technical Details
Das ursprüngliche Problem war eine ineffiziente Implementierung der Logging-Threads:
```python
# VORHER (ineffizient - 60 OS-Aufweckvorgänge pro Intervall):
for _ in range(60):
    if not self._running:
        break
    time.sleep(1)

# NACHHER (effizient - 1 OS-Aufruf pro Intervall):
self._stop_event.wait(timeout=120)
```

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
