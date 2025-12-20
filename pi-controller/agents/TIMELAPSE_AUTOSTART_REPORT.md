# Timelapse Auto-Enable Implementation Report

**Agent**: Builder
**Date**: 2025-12-20
**Task**: Timelapse automatisch bei Service-Neustart aktivieren
**Status**: COMPLETED

---

## Zusammenfassung

Timelapse wird jetzt bei jedem Service-Neustart automatisch aktiviert mit:
- `enabled: True`
- `interval_seconds: 600` (10 Minuten)

---

## Implementierung

### Geänderte Dateien

#### `/Users/denniswestermann/Desktop/Coding Projekte/GrowPi/pi-controller/grow_pi/utils/camera.py`

**Zeilen 116-139**: `CameraService.__init__()`

```python
def __init__(self, config: Optional[CameraConfig] = None):
    """Initialize camera service."""
    self.config = config or CameraConfig()
    self._camera: Optional['cv2.VideoCapture'] = None
    self._lock = threading.Lock()
    self._initialized = False
    self._last_capture_time = 0
    self._min_capture_interval = 0.1  # 100ms minimum between captures

    # Timelapse - AUTO-ENABLE on service start
    self.timelapse_config = TimelapseConfig(
        enabled=True,         # AUTO-ENABLED on startup
        interval_seconds=600  # 10 minutes default
    )
    self._timelapse_thread: Optional[threading.Thread] = None
    self._timelapse_running = False

    if CV2_AVAILABLE:
        self._init_camera()

        # Auto-start timelapse if camera initialized successfully
        if self._initialized and self.timelapse_config.enabled:
            self._start_timelapse()
            logger.info(f"Timelapse auto-enabled on startup (interval: {self.timelapse_config.interval_seconds}s)")
```

---

## Änderungen im Detail

### 1. TimelapseConfig Initialisierung (Zeilen 126-129)

**Vorher:**
```python
self.timelapse_config = TimelapseConfig()  # enabled=False (default)
```

**Nachher:**
```python
self.timelapse_config = TimelapseConfig(
    enabled=True,         # AUTO-ENABLED on startup
    interval_seconds=600  # 10 minutes default
)
```

**Rationale:** Explizite Aktivierung beim Service-Start statt manueller Konfiguration erforderlich.

---

### 2. Auto-Start Logik (Zeilen 136-139)

**Neu hinzugefügt:**
```python
# Auto-start timelapse if camera initialized successfully
if self._initialized and self.timelapse_config.enabled:
    self._start_timelapse()
    logger.info(f"Timelapse auto-enabled on startup (interval: {self.timelapse_config.interval_seconds}s)")
```

**Funktionsweise:**
1. Prüft ob Kamera erfolgreich initialisiert wurde (`self._initialized`)
2. Prüft ob Timelapse enabled ist (`self.timelapse_config.enabled`)
3. Startet Timelapse-Thread über `_start_timelapse()`
4. Loggt Aktivierung mit konfiguriertem Intervall

**Logging-Ausgabe:**
```
Timelapse auto-enabled on startup (interval: 600s)
```

---

## Verhalten

### Bei Service-Start (Cold Boot)
1. `get_camera_service()` wird aufgerufen (beim ersten API-Zugriff)
2. `CameraService.__init__()` erstellt Timelapse-Config mit `enabled=True`
3. Kamera wird initialisiert (`_init_camera()`)
4. Timelapse-Thread wird gestartet (`_start_timelapse()`)
5. Log: "Timelapse auto-enabled on startup (interval: 600s)"
6. Alle 600 Sekunden (10 Min) wird ein Foto aufgenommen

### Bei Warm Restart (Service Neustart)
- Gleicher Ablauf wie Cold Boot
- Timelapse wird **IMMER** neu gestartet
- Alte Bilder bleiben erhalten (rolling buffer: max 1000 Bilder)

### Bei Kamera-Fehler
- Wenn `CV2_AVAILABLE=False`: Kein Timelapse-Start
- Wenn `_init_camera()` fehlschlägt: Kein Timelapse-Start
- Log: Nur bei erfolgreicher Aktivierung

---

## Sicherheit

### Fehlerbehandlung
- Timelapse startet nur wenn Kamera verfügbar (`CV2_AVAILABLE`)
- Timelapse startet nur wenn Kamera initialisiert (`self._initialized`)
- Thread-Safe durch `threading.Lock()` in `_timelapse_loop()`

### Bestehende Features bleiben erhalten
- Manual ON/OFF über API: `/api/camera/timelapse/config` (POST)
- Interval-Anpassung: Weiterhin über API möglich
- Brightness Detection: Unverändert (v6.17.0 Feature)
- Rolling Buffer Cleanup: Unverändert (max_images: 1000)

---

## Testing

### Manuelle Tests (empfohlen)

1. **Service Neustart Test**:
   ```bash
   sudo systemctl restart grow-pi
   sudo journalctl -u grow-pi -f | grep -i timelapse
   ```
   Erwartete Ausgabe:
   ```
   Timelapse auto-enabled on startup (interval: 600s)
   ```

2. **Foto-Aufnahme Test** (nach 10 Min):
   ```bash
   ls -lah /opt/grow-pi/data/timelapse/$(date +%Y-%m-%d)/
   ```
   Erwartete Ausgabe:
   ```
   timelapse_20251220_143000.jpg
   ```

3. **API Status Check**:
   ```bash
   curl http://localhost:5000/api/camera/timelapse/config
   ```
   Erwartete Ausgabe:
   ```json
   {
     "success": true,
     "config": {
       "enabled": true,
       "interval_seconds": 600,
       ...
     }
   }
   ```

---

## Rollback

Falls Probleme auftreten, kann die Änderung rückgängig gemacht werden:

```bash
cd /opt/grow-pi
git diff grow_pi/utils/camera.py
git checkout grow_pi/utils/camera.py
sudo systemctl restart grow-pi
```

---

## Abhängigkeiten

- **OpenCV (cv2)**: Muss installiert sein
- **Kamera**: Microsoft LifeCam HD-3000 muss angeschlossen sein
- **Speicherplatz**: Min. 100 MB für 1000 Bilder (1920x1080 @ 95% JPEG Quality)

---

## Log-Monitoring

Nach Service-Restart relevante Logs prüfen:

```bash
sudo journalctl -u grow-pi -f | grep -E "Timelapse|Camera"
```

Erwartete Ausgaben:
```
Camera initialized: 1920x1080
Timelapse auto-enabled on startup (interval: 600s)
Timelapse started (interval: 600s)
```

---

## Zusammenfassung der Änderungen

| Datei | Zeilen | Änderung |
|-------|--------|----------|
| `grow_pi/utils/camera.py` | 126-129 | TimelapseConfig mit `enabled=True` initialisieren |
| `grow_pi/utils/camera.py` | 136-139 | Auto-start Logik nach Kamera-Init |

**Gesamt**: 2 Code-Änderungen, 1 Datei modifiziert

---

## Nächste Schritte

1. Änderungen auf Raspberry Pi deployen
2. Service neu starten: `sudo systemctl restart grow-pi`
3. Logs prüfen: 10 Minuten warten und Foto-Aufnahme verifizieren
4. Optional: Interval über API anpassen wenn gewünscht

---

**WICHTIG**: Diese Änderung betrifft NUR das Auto-Enable Feature. Alle bestehenden Timelapse-Features (Brightness Detection, Rolling Buffer, Date-Folders) bleiben unverändert.
