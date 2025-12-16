# Timelapse Camera Implementation Plan for GrowPi

**Erstellt**: 2025-12-08
**Status**: PLAN ERSTELLT - Wartet auf Genehmigung
**Geplante Version**: v6.17.0
**Geschätzter Aufwand**: 2-3 Tage

---

## Executive Summary

Implementierung einer Timelapse-Kamera-Funktion mit automatischer Dunkelheits-Erkennung. Die Bilder werden in JPEG-Format gespeichert und können später zu einem Zeitraffer-Video zusammengefügt werden.

---

## 1. Architektur-Übersicht

```
+------------------+     +--------------------+     +------------------+
|   Frontend UI    |---->|   Flask API        |---->|  Camera Service  |
|   (Room Tab)     |<----|   (/api/camera/*)  |<----|  (camera.py)     |
+------------------+     +--------------------+     +------------------+
                                                            |
                                                            v
                         +--------------------+     +------------------+
                         |  Image Gallery     |<----|  File Storage    |
                         |  (Browser)         |     |  (/timelapse/)   |
                         +--------------------+     +------------------+
```

**Komponenten:**
- **CameraService** (bestehend): Erweitert mit Dunkelheits-Erkennung
- **TimelapseConfig** (bestehend): Erweitert mit Helligkeits-Schwellwert
- **Flask API Routes**: Neue Endpoints für Timelapse-Management
- **Frontend Module** (neu): `timelapse.js` für UI-Interaktion
- **Frontend HTML**: Room-Tab erweitert mit Timelapse-Sektion

---

## 2. Anforderungen (vom User)

### 2.1 Funktionale Anforderungen

| # | Anforderung | Priorität |
|---|-------------|-----------|
| 1 | Bilder in konfigurierbarem Intervall speichern (30s - 5min) | HOCH |
| 2 | JPEG-Format für spätere Zeitraffer-Erstellung | HOCH |
| 3 | Dunkelheits-Filter: Keine Bilder wenn Lampen aus | HOCH |
| 4 | Konfigurations-UI im Room-Tab | HOCH |
| 5 | Verzeichnis konfigurierbar | MITTEL |
| 6 | Bilder-Galerie zum Durchsuchen | MITTEL |
| 7 | Verzeichnis im Browser öffnen können | MITTEL |

### 2.2 Nicht-Funktionale Anforderungen

- Performance: Capture darf Hauptsystem nicht blockieren
- Speicherplatz: Automatische Bereinigung alter Bilder
- Robustheit: Fehlertoleranz bei Kamera-Problemen

---

## 3. Backend-Änderungen

### 3.1 Erweiterte `TimelapseConfig` Dataclass

**Datei**: `/pi-controller/grow_pi/utils/camera.py`

```python
@dataclass
class TimelapseConfig:
    """Timelapse configuration."""
    enabled: bool = False
    interval_seconds: int = 300  # 5 Minuten default (30s - 300s konfigurierbar)
    output_dir: str = "/opt/grow-pi/data/timelapse"
    max_images: int = 1000
    # NEU: Dunkelheits-Erkennung
    skip_dark_images: bool = True
    brightness_threshold: int = 15  # 0-255, unter diesem Wert = "zu dunkel"
    min_bright_pixels_percent: float = 10.0  # Min. X% der Pixel müssen hell sein
```

### 3.2 Neue Methode: `_analyze_brightness()`

```python
def _analyze_brightness(self, frame) -> dict:
    """
    Analysiert Frame-Helligkeit für Dunkelheits-Erkennung.

    Algorithmus:
    1. Konvertiere zu Graustufen
    2. Berechne Durchschnitts-Helligkeit (0-255)
    3. Berechne Prozentsatz "heller" Pixel
    4. Entscheide: Zu dunkel wenn BEIDE unter Schwellwert

    Returns:
        dict mit:
        - average_brightness: 0-255
        - bright_pixel_percent: Prozent heller Pixel
        - is_too_dark: Boolean
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    avg_brightness = gray.mean()
    threshold = self.timelapse_config.brightness_threshold
    bright_pixels = (gray > threshold).sum()
    bright_percent = (bright_pixels / gray.size) * 100

    is_too_dark = (
        avg_brightness < threshold or
        bright_percent < self.timelapse_config.min_bright_pixels_percent
    )

    return {
        'average_brightness': round(avg_brightness, 1),
        'bright_pixel_percent': round(bright_percent, 1),
        'is_too_dark': is_too_dark,
        'threshold': threshold
    }
```

### 3.3 Modifizierte `_capture_timelapse_image()`

**Ablauf:**
1. Frame aufnehmen
2. Helligkeit analysieren (wenn `skip_dark_images=True`)
3. Wenn zu dunkel → Skip mit Log
4. Sonst → JPEG encodieren und speichern
5. Alte Bilder bereinigen

**Verzeichnisstruktur:**
```
/opt/grow-pi/data/timelapse/
    2025-12-08/
        timelapse_20251208_060000.jpg
        timelapse_20251208_060500.jpg
        ...
    2025-12-09/
        timelapse_20251209_060000.jpg
        ...
```

### 3.4 Neue API-Endpoints

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/api/camera/timelapse/stats` | GET | Statistiken (Config, Speicher, Anzahl) |
| `/api/camera/timelapse/config` | GET | Aktuelle Konfiguration |
| `/api/camera/timelapse/config` | POST | Konfiguration aktualisieren |
| `/api/camera/timelapse/folders` | GET | Liste der Datum-Ordner |
| `/api/camera/timelapse/images` | GET | Bilder-Liste (mit Pagination) |
| `/api/camera/timelapse/image/<folder>/<file>` | GET | Einzelnes Bild ausliefern |
| `/api/camera/timelapse/test-brightness` | GET | Helligkeit aktuell testen |

---

## 4. Frontend-Änderungen

### 4.1 Neues JavaScript-Modul: `timelapse.js`

**Funktionen:**
- `initTimelapseModule()` - Initialisierung
- `fetchTimelapseConfig()` - Config laden
- `saveTimelapseConfig()` - Config speichern
- `testBrightness()` - Helligkeits-Test
- `fetchFolders()` - Ordner-Liste laden
- `fetchImages()` - Bilder-Liste laden
- `openLightbox()` - Bild-Vorschau

### 4.2 HTML-Erweiterung im Room-Tab

```html
<!-- Timelapse Kamera Section -->
<section class="section timelapse-section">
    <h2>Timelapse Kamera</h2>

    <!-- Enable Toggle -->
    <div class="timelapse-toggle-row">
        <div class="curve-toggle" id="timelapseToggle"></div>
        <span>Timelapse aktiv</span>
    </div>

    <!-- Konfiguration -->
    <div class="timelapse-config">
        <!-- Intervall (30s - 300s) -->
        <div class="config-row">
            <label>Intervall (Sekunden)</label>
            <input type="number" id="timelapseInterval" min="30" max="600">
        </div>

        <!-- Dunkelheits-Filter Toggle -->
        <div class="config-row">
            <div class="curve-toggle" id="skipDarkToggle"></div>
            <span>Dunkle Bilder überspringen</span>
        </div>

        <!-- Helligkeits-Schwellwert -->
        <div class="config-row">
            <label>Helligkeitsschwelle (0-255)</label>
            <input type="number" id="brightnessThreshold" min="0" max="255">
        </div>

        <!-- Helligkeit testen -->
        <button id="btnTestBrightness">Helligkeit testen</button>
        <div id="brightnessTestResult"></div>

        <!-- Speichern Button -->
        <button id="btnSaveTimelapseConfig">Speichern</button>
    </div>

    <!-- Speicher-Info -->
    <div class="timelapse-storage">
        <span>Speicher:</span>
        <span id="timelapseStorageInfo">0 MB (0 Bilder)</span>
    </div>

    <!-- Bilder-Galerie -->
    <div class="timelapse-gallery-section">
        <h3>Bilder-Galerie</h3>
        <select id="timelapseFolderSelect"></select>
        <button id="btnRefreshGallery">Aktualisieren</button>
        <div id="timelapseGallery" class="timelapse-gallery"></div>
    </div>
</section>
```

### 4.3 CSS-Styles

- Grid-basierte Galerie (responsive)
- Lightbox für Vollbild-Ansicht
- Status-Anzeige für Helligkeits-Test (grün=OK, rot=zu dunkel)

---

## 5. Dunkelheits-Erkennung - Algorithmus

### 5.1 Warum dieser Ansatz?

**Problem**: Nachts sind die Grow-Lampen aus → Bilder wären komplett schwarz oder nur mit Streulicht.

**Lösung**: Kombinierte Helligkeits-Analyse:

1. **Durchschnitts-Helligkeit**: Schnelle Prüfung ob Bild generell dunkel
2. **Prozent heller Pixel**: Verhindert False-Positives bei einzelnen hellen Spots (z.B. LED-Statusleuchten)

### 5.2 Empfohlene Default-Werte

| Parameter | Default | Beschreibung |
|-----------|---------|--------------|
| `brightness_threshold` | 15 | Pixel unter diesem Wert gelten als "dunkel" |
| `min_bright_pixels_percent` | 10% | Mind. 10% der Pixel müssen hell sein |

### 5.3 Test-Funktion

User kann über "Helligkeit testen" Button prüfen, ob aktuelle Lichtverhältnisse ausreichen:
- Zeigt: Durchschnitts-Helligkeit, Prozent heller Pixel
- Status: "OK" (grün) oder "ZU DUNKEL" (rot)

---

## 6. Datei-Management

### 6.1 Verzeichnisstruktur

```
/opt/grow-pi/data/timelapse/
├── 2025-12-08/
│   ├── timelapse_20251208_060000.jpg
│   ├── timelapse_20251208_060030.jpg  (bei 30s Intervall)
│   └── ...
├── 2025-12-09/
│   └── ...
└── ...
```

### 6.2 Namenskonvention

- Pattern: `timelapse_YYYYMMDD_HHMMSS.jpg`
- Beispiel: `timelapse_20251208_143022.jpg`

### 6.3 Speicherplatz-Management

- `max_images`: Standard 1000 Bilder
- Älteste Bilder werden automatisch gelöscht wenn Limit erreicht
- Storage-Info in UI anzeigen (MB + Anzahl)

---

## 7. Implementierungs-Reihenfolge

### Phase 1: Backend Core (Tag 1)

1. **TimelapseConfig erweitern**
   - Neue Felder hinzufügen
   - Config-Persistierung prüfen

2. **Dunkelheits-Erkennung implementieren**
   - `_analyze_brightness()` Methode
   - Test mit verschiedenen Lichtverhältnissen

3. **Capture-Methode modifizieren**
   - Ordnerstruktur nach Datum
   - Dunkelheits-Check integrieren

4. **Neue API-Endpoints**
   - Stats, Config, Folders, Images, Test-Brightness

### Phase 2: Frontend UI (Tag 2)

1. **JavaScript-Modul erstellen**
   - `timelapse.js` mit allen Funktionen
   - API-Integration

2. **HTML in Room-Tab**
   - Konfiguration-Sektion
   - Galerie-Sektion

3. **CSS-Styles**
   - Galerie-Grid
   - Lightbox
   - Responsive Design

### Phase 3: Integration & Test (Tag 3)

1. **End-to-End Tests**
   - Capture mit verschiedenen Intervallen
   - Dunkelheits-Erkennung testen
   - Galerie durchsuchen

2. **Edge-Cases testen**
   - Kamera nicht verfügbar
   - Speicherplatz voll
   - Viele Bilder (Performance)

3. **Deployment auf Pi**
   - Config-Migration
   - Service-Restart

---

## 8. Betroffene Dateien

### Backend (Python)

| Datei | Änderung |
|-------|----------|
| `grow_pi/utils/camera.py` | TimelapseConfig, _analyze_brightness(), _capture_timelapse_image() |
| `grow_pi/web/api.py` | 6 neue API-Endpoints |
| `grow_pi/web/static/js/api.js` | API-Client-Erweiterungen |

### Frontend (JS/CSS/HTML)

| Datei | Änderung |
|-------|----------|
| `static/js/modules/timelapse.js` | NEU - Komplettes Modul |
| `static/index.html` | Room-Tab HTML erweitern |
| `static/css/main.css` | Timelapse-Styles hinzufügen |

---

## 9. Dependencies

**Keine neuen Python-Pakete erforderlich**:
- `cv2` (OpenCV) - bereits vorhanden
- `numpy` - bereits vorhanden via OpenCV

**Frontend**: Vanilla JavaScript (keine neuen Libraries)

---

## 10. Risiken & Mitigationen

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| Speicherplatz läuft voll | Mittel | `max_images` Limit + Auto-Cleanup |
| Kamera-Timeout während Capture | Niedrig | Try-Catch + Retry-Logik |
| Thread-Safety-Probleme | Niedrig | Bestehender Lock verwenden |
| Falsche Dunkelheits-Erkennung | Mittel | Test-Button + konfigurierbare Schwellwerte |

---

## 11. Future Enhancements (Out of Scope)

- Video-Generierung aus Bildern (ffmpeg)
- Cloud-Sync für Timelapse-Bilder
- Motion-Detection-Option
- Zeitfenster-Scheduling (nur zu bestimmten Zeiten aufnehmen)
- Multi-Kamera-Support

---

## 12. Akzeptanzkriterien

- [ ] Timelapse kann aktiviert/deaktiviert werden
- [ ] Intervall ist konfigurierbar (30s - 600s)
- [ ] Dunkle Bilder werden automatisch übersprungen
- [ ] Helligkeits-Schwellwert ist konfigurierbar
- [ ] "Helligkeit testen" Button funktioniert
- [ ] Bilder werden nach Datum in Ordnern gespeichert
- [ ] Galerie zeigt Bilder mit Lightbox-Vorschau
- [ ] Speicher-Info wird angezeigt
- [ ] Auto-Cleanup bei Limit-Erreichen

---

## 13. Genehmigung

**Status**: Wartet auf User-Genehmigung

**Nach Genehmigung**:
1. @architect → Finale Architektur-Review
2. @builder → Implementierung in 3 Phasen
3. @validator → Cross-File-Konsistenz prüfen
4. @scribe → CHANGELOG.md aktualisieren

---

**Erstellt von**: @Plan Agent
**Review-Datum**: 2025-12-08
**Next Steps**: User-Genehmigung abwarten
