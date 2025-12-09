# GrowPi Roadmap - Geplante Features

**Letzte Aktualisierung**: 2025-12-09
**Aktuelle Version**: v6.18.0
**Status**: Active Development - Feature Phase 🚀

---

## ✅ NEUE FEATURES & FIXES (2025-12-09)

### Feature: Kamera Auto-Detection - IMPLEMENTIERT ✅

**Status**: ✅ IMPLEMENTIERT
**Implementiert am**: 2025-12-09
**Version**: v6.18.0

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

**Deployment:**
- ⏳ Wartet auf User-Genehmigung

---

### Optimization: Separate JPEG-Qualitäten - IMPLEMENTIERT ✅

**Status**: ✅ IMPLEMENTIERT
**Implementiert am**: 2025-12-09
**Version**: v6.18.0

**Änderungen:**
- `preview_jpeg_quality: 70` - Für Live-Preview (ressourcenschonend)
- `timelapse_jpeg_quality: 95` - Für Zeitraffer-Fotos (hohe Qualität)
- Preview FPS: 10 → 2 (90% weniger Ressourcenverbrauch)

**Rationale:**
- Live-Preview braucht keine hohe Qualität (70% reicht)
- Timelapse-Fotos sollten beste Qualität haben (95%)
- 2 FPS reicht für Live-Vorschau, spart CPU

---

## ✅ BEHOBENE BUGS (2025-12-07)

### Bug #1: Room/Entfeuchter-Steuerung - BEHOBEN ✅

**Status**: ✅ BEHOBEN
**Behoben am**: 2025-12-07 16:08

**Root Causes (alle behoben):**
1. `dehumidifier_controller.set_humidity_reader()` wurde nie aufgerufen
2. Tuya Device ID fehlte in der Datenbank
3. DB-Migration lief nicht automatisch

**Fixes:**
- ✅ Bugfix in `api.py`: `dehumidifier_controller.set_humidity_reader(read_dht22)` hinzugefügt
- ✅ Tuya Device ID in DB gesetzt: `bfc705014c6241667avzn8`
- ✅ `dehumidifier_controller.py`: DB-Verzeichnis wird automatisch erstellt

**Test-Ergebnis:**
```json
{
  "success": true,
  "message": "Dehumidifier turned ON",
  "humidity": 64.7,
  "is_on": true
}
```

---

### Bug #3: Kosten-Tracking - FUNKTIONIERT ✅

**Status**: ✅ KEIN BUG
**Geprüft am**: 2025-12-07 16:10

Kosten-Tracking funktioniert. Stromverbrauch wird korrekt angezeigt.

---

### Bug #4: DHT22 Sensor - BEHOBEN ✅

**Status**: ✅ BEHOBEN (war temporär)
**Behoben am**: 2025-12-07 16:05

Sensor funktioniert wieder nach Service-Restart. War vermutlich ein temporäres Timing-Problem.

---

### Bug #5: Tuya Device ID - BEHOBEN ✅

**Status**: ✅ BEHOBEN
**Behoben am**: 2025-12-07 16:08

Device ID wurde in DB eingetragen:
```sql
UPDATE switchable_devices SET tuya_device_id = 'bfc705014c6241667avzn8' WHERE id = 1;
```

---

## 🟡 OFFENE PUNKTE

### Bug #2: Zeitschaltung/Override - ZU TESTEN

**Status**: 🟡 ZU TESTEN
**Abhängigkeit**: Bug #1 ist jetzt behoben

Da die Entfeuchter-Steuerung jetzt funktioniert, sollte auch die Zeitschaltung funktionieren.

**Zu testen:**
- [ ] Zeitfenster im UI anlegen
- [ ] Prüfen ob Scheduler greift
- [ ] Override-Funktion testen

---

### Bug #6: Kurven-Presets funktionieren nicht - BEHOBEN ✅

**Status**: ✅ BEHOBEN
**Behoben am**: 2025-12-07

**Fix:**
- `applySelectedPreset()` in `curves.js` verbessert
- Fallback zu `fetchCurves()` wenn `response.curves` leer ist
- `updateLocalPreview()` nach Apply für sofortiges visuelles Feedback

---

### Feature: Kurven-Seite Accordion/Collapsible - IMPLEMENTIERT ✅

**Status**: ✅ IMPLEMENTIERT
**Implementiert am**: 2025-12-07
**Deployed**: 2025-12-07

**Umsetzung:**
- Alle 4 Kanäle standardmäßig zugeklappt
- Kanalname + aktuelle Intensität im Header sichtbar
- Klick auf Header klappt auf/zu
- Enable/Disable Toggle weiterhin funktional
- localStorage Persistence pro Kanal
- Smooth CSS Animation
- ARIA Keyboard Accessibility

---

### Feature: Multi-Line Preview Chart - IMPLEMENTIERT ✅

**Status**: ✅ IMPLEMENTIERT
**Implementiert am**: 2025-12-07
**Deployed**: 2025-12-07
**Version**: v6.10.0

**Umsetzung:**
- SVG-basiertes Multi-Line-Chart
- Alle 4 Kanäle gleichzeitig sichtbar mit farbigen Linien
- Checkboxen zum Ein-/Ausblenden einzelner Kanäle
- X-Achse: 00:00 - 24:00 mit Zeitlabels
- Y-Achse: 0% - 100% mit %-Labels
- Grid-Linien für bessere Lesbarkeit
- localStorage Persistenz für Checkbox-Status
- Responsive Design für Mobile

**Technische Details:**
- `renderPreview()` in `curves.js` komplett umgebaut
- Interpolation für alle aktiven Kanäle gleichzeitig
- SVG `<polyline>` für jede Kurve
- Checkbox-Event-Listener mit localStorage

---

### Bug #8: Room Automation - Status-Desync - TEILWEISE BEHOBEN 🟡

**Status**: 🟡 TEILWEISE BEHOBEN - WEITERE FIXES NÖTIG
**Erste Fixes**: 2025-12-07
**Version**: v6.13.0

**Problem 1 (behoben):**
- Controller speicherte `self._is_on` intern, synchronisierte aber nie mit echtem Tuya-Status
- ✅ FIX: `_sync_device_status()` fragt echten Tuya-Status ab

**Problem 2 (NEU ENTDECKT - KRITISCH):**
- `SmartPlugController.turn_on()/turn_off()` gibt IMMER `True` zurück
- Es wird NICHT geprüft, ob der Befehl tatsächlich erfolgreich war!
- Wenn `device.turn_off()` fehlschlägt, meldet der Code trotzdem Erfolg

**Problem 3 (NEU ENTDECKT):**
- In `_ensure_state()` (Zeile 641): `if target_on == self._is_on: return None`
- Bei manueller Steuerung sollte der Befehl IMMER gesendet werden
- Aktuell: Wenn Status-Sync sagt "Gerät ist an", wird beim Einschalten nichts gemacht

**Symptome:**
- User drückt "Einschalten" → Gerät schaltet nicht ein (kein Befehl gesendet)
- User drückt "Ausschalten" → Log sagt "OFF", aber Gerät bleibt an
- Status-Sync zeigt dann: `internal=False, actual=True -> updating`

**Zu beheben:**
1. `SmartPlugController`: Erfolg von `turn_on()/turn_off()` verifizieren
2. `DehumidifierController`: Bei manueller Steuerung IMMER Befehl senden (kein Early-Return)

**Bericht:** `/agents/bug8-status-desync-fix-report.md`

---

### Bug #9: SmartPlugController - Keine Erfolgsverifikation - BEHOBEN ✅

**Status**: ✅ BEHOBEN
**Entdeckt**: 2025-12-07 19:55
**Behoben**: 2025-12-07 20:00
**Version**: v6.14.0

**Problem:**
`SmartPlugController.turn_on()` und `turn_off()` in `smart_plug_controller.py`:

```python
def turn_on(self, device_id: str) -> bool:
    device = self.devices.get(device_id)
    if device:
        try:
            device.turn_on()  # ← Keine Prüfung ob erfolgreich!
            return True       # ← IMMER True!
        except Exception as e:
            logger.error(...)
```

**Root Cause:**
- `tinytuya.OutletDevice.turn_on()` gibt keinen Return-Wert
- Es wird nie geprüft, ob das Gerät tatsächlich geschaltet wurde
- Fehler werden nur bei Exceptions geloggt

**Lösung (zu implementieren):**
Nach dem Schaltbefehl den Status abfragen und verifizieren:

```python
def turn_on(self, device_id: str) -> bool:
    device = self.devices.get(device_id)
    if device:
        try:
            device.turn_on()
            time.sleep(0.5)  # Kurz warten
            # Verifizieren
            status = device.status()
            if status and status.get('dps', {}).get('1') == True:
                return True
            else:
                logger.error(f"turn_on failed verification for {device_id}")
                return False
        except Exception as e:
            logger.error(...)
            return False
```

**Betroffene Dateien:**
- `/pi-controller/grow_pi/lamps/smart_plug_controller.py`

---

### Bug #10: DehumidifierController - Manuelle Steuerung Skip-Bug - BEHOBEN ✅

**Status**: ✅ BEHOBEN
**Entdeckt**: 2025-12-07 19:55
**Behoben**: 2025-12-07 20:00
**Version**: v6.14.0

**Problem:**
In `dehumidifier_controller.py`, Methode `_ensure_state()`, Zeile 641:

```python
# State is already correct
if target_on == self._is_on:
    return None  # ← PROBLEM: Bei manueller Steuerung trotzdem senden!
```

**Symptom:**
1. User drückt "Einschalten"
2. `_sync_device_status()` läuft, setzt `self._is_on = True` (Gerät war schon an)
3. `target_on == self._is_on` (True == True) → `return None`
4. KEIN BEFEHL wird gesendet!
5. User denkt es hat geklappt, aber nichts passiert

**Lösung (zu implementieren):**
Bei manueller Steuerung (TriggerType.MANUAL) IMMER den Befehl senden:

```python
def _ensure_state(self, target_on: bool, trigger: TriggerType, details: str = "") -> Optional[bool]:
    self._sync_device_status()

    # Bei manueller Steuerung: IMMER Befehl senden (User will explizit schalten)
    if trigger != TriggerType.MANUAL:
        # Nur bei Automation den Early-Return machen
        if target_on == self._is_on:
            return None

    # ... Rest der Logik
```

**Betroffene Dateien:**
- `/pi-controller/grow_pi/utils/dehumidifier_controller.py`

---

### Bug #11: Datalog/History Problem - ZU UNTERSUCHEN 🔴

**Status**: 🔴 ZU UNTERSUCHEN
**Gemeldet**: 2025-12-07 20:10
**Version**: v6.15.0

**Symptome (vom User gemeldet):**
- Console zeigt `[History] Loading data for 24 hours (downsampled)`
- Unbekanntes Problem mit der History-Seite

**Console-Logs:**
```
[History] Loading data for 24 hours (downsampled)
[History] Range changed to 1 hours
[History] Loading data for 1 hours (downsampled)
```

**Hinweis:** `content.js` Fehler sind von Browser-Extension, nicht unser Code!

**Zu untersuchen:**
- [ ] Werden Daten korrekt geladen?
- [ ] Funktioniert die Chart-Darstellung?
- [ ] API-Response prüfen
- [ ] SQLite-Daten prüfen

---

### Bug #7: Verlauf-Seite - Teilweise behoben ✅

**Status**: 🟡 TEILWEISE BEHOBEN
**Behoben am**: 2025-12-07
**Version**: v6.11.0

**Behoben:**
- ✅ Steckdosen-Namen werden korrekt angezeigt
- ✅ Zeitfilter funktioniert für alle 3 Charts synchron
- ✅ "1h" Button hinzugefügt
- ✅ Chart.js Date-Adapter für echte Zeit-Achsen

**Noch offen:**
- ✅ Stromverbrauch-Daten werden jetzt angezeigt (Fix: API-Response-Format)

---

### Feature: Data Aggregation / Downsampling - IMPLEMENTIERT ✅

**Status**: ✅ IMPLEMENTIERT
**Implementiert am**: 2025-12-07
**Version**: v6.12.0

**Umsetzung (Option A - Query-Time Aggregation):**

- Alle Rohdaten bleiben erhalten (unendliche Speicherung)
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
- `api.js` + `history.js`: Limit-Parameter entfernt

**Bericht:** `/agents/data-aggregation-report.md`

---

## 🔧 TECHNISCHE SCHULDEN (Refactoring)

### Refactoring #1: api.py Modularisierung (KRITISCH)

**Status**: 📋 GEPLANT
**Plan erstellt**: 2025-12-07
**Detaillierter Plan**: [`docs/PLAN_API_REFACTORING.md`](./PLAN_API_REFACTORING.md)

**Problem:**
- `api.py` hat **1119 Zeilen** - viel zu groß für Wartbarkeit
- ~700 Zeilen sind **duplizierter Code** (Routes existieren auch in Blueprints)
- Nur 3 von 9 Blueprints sind registriert
- Fehleranfällig bei Agenten-Änderungen

**Ziel:**
- api.py von 1119 → ~200 Zeilen reduzieren
- Alle 9 Blueprints aktivieren
- Duplizierten Code entfernen
- `dependencies.py` aktivieren

**Analyse durch Opus-Agent:**
- Siehe `/agents/api-analysis-refactoring-plan.md`

**Geschätzter Aufwand:** ~2 Stunden

**Priorität:** HOCH (aber System erst stabilisieren)

---

## 🚀 Nächste Features (Priorisiert)

### Feature #-1: Timelapse Kamera mit Dunkelheits-Erkennung (PRIORITÄT) 🎯

**Status**: 📋 GEPLANT - WARTET AUF GENEHMIGUNG
**Erstellt**: 2025-12-08
**Geplante Version**: v6.17.0
**Geschätzter Aufwand**: 2-3 Tage
**Detaillierter Plan**: [`/agents/TIMELAPSE_CAMERA_PLAN.md`](/agents/TIMELAPSE_CAMERA_PLAN.md)

#### Ziel
Automatische Timelapse-Aufnahmen für spätere Zeitraffer-Video-Erstellung. Mit intelligenter Dunkelheits-Erkennung, damit nachts (wenn Lampen aus sind) keine schwarzen Bilder gespeichert werden.

#### Funktionalität

**Konfigurierbare Aufnahme:**
- Intervall: 30 Sekunden bis 10 Minuten (konfigurierbar)
- Format: JPEG für maximale Kompatibilität
- Speicherort: `/opt/grow-pi/data/timelapse/` (nach Datum sortiert)

**Dunkelheits-Filter (KRITISCH):**
- Analysiert Helligkeit jedes Frames vor dem Speichern
- Schwellwert konfigurierbar (0-255)
- "Helligkeit testen" Button für Live-Preview
- Verhindert schwarze/dunkle Bilder wenn Lampen aus sind

**UI im Room-Tab:**
- Timelapse aktivieren/deaktivieren
- Intervall einstellen
- Helligkeits-Schwellwert konfigurieren
- Bilder-Galerie mit Lightbox
- Speicherplatz-Anzeige

#### Verzeichnisstruktur

```
/opt/grow-pi/data/timelapse/
├── 2025-12-08/
│   ├── timelapse_20251208_060000.jpg
│   ├── timelapse_20251208_060030.jpg
│   └── ...
├── 2025-12-09/
│   └── ...
```

#### Neue API-Endpoints

| Endpoint | Beschreibung |
|----------|--------------|
| `GET /api/camera/timelapse/stats` | Statistiken (Config, Speicher) |
| `GET/POST /api/camera/timelapse/config` | Konfiguration |
| `GET /api/camera/timelapse/folders` | Datum-Ordner |
| `GET /api/camera/timelapse/images` | Bilder-Liste |
| `GET /api/camera/timelapse/image/<folder>/<file>` | Einzelbild |
| `GET /api/camera/timelapse/test-brightness` | Helligkeit testen |

#### Betroffene Dateien

**Backend:**
- `grow_pi/utils/camera.py` - TimelapseConfig + Brightness-Detection
- `grow_pi/web/api.py` - 6 neue Endpoints

**Frontend:**
- `static/js/modules/timelapse.js` (NEU)
- `static/index.html` - Room-Tab erweitern
- `static/css/main.css` - Galerie-Styles

#### Akzeptanzkriterien

- [ ] Timelapse aktivierbar/deaktivierbar
- [ ] Intervall konfigurierbar (30s - 600s)
- [ ] Dunkle Bilder werden automatisch übersprungen
- [ ] Helligkeits-Schwellwert konfigurierbar
- [ ] "Helligkeit testen" Button funktioniert
- [ ] Bilder nach Datum in Ordnern gespeichert
- [ ] Galerie mit Lightbox-Vorschau
- [ ] Speicher-Info angezeigt
- [ ] Auto-Cleanup bei Limit-Erreichen

---

### Feature #0: Interactive Bezier Curve Editor (PRIORITÄT) 🎯

**Status**: 🟡 FUNKTIONIERT - UI POLISH NÖTIG
**Erstellt**: 2025-12-07
**Deployed**: 2025-12-07
**Version**: v6.15.0

**Aktueller Stand**:
- ✅ Grundfunktionalität implementiert und deployed
- ✅ Keyframes können gesetzt/verschoben werden
- 🟡 **Smartphone UI-Probleme** - muss noch angepasst werden

**TODO (UI Polish)**:
- [ ] Mobile Layout verbessern
- [ ] Touch-Targets größer machen
- [ ] Fullscreen-Modus auf Mobile optimieren
- [ ] Responsive Design überarbeiten

**Priorität**: UI-Fixes für Mobile

**Ziel**: Kurvensteuerung wie Cubase Automation Curve / BIOS-Lüfterkurve - direkt zeichnen statt Zahlen tippen

#### Funktionalität

**Interaktiver Graph:**
- X-Achse = Zeit (00:00–24:00)
- Y-Achse = Intensität (0–100%)
- Draggable Keyframe Anchor Points
- Live Bezier/Spline Interpolation
- Touch + Mouse Support

**Keyframe-Bearbeitung:**
- Punkt setzen: Klick/Touch auf Kurve
- Punkt verschieben: Drag & Drop
- Punkt löschen: Doppelklick oder Long-Press
- Automatische Tabellen-Synchronisation unten

**Datenspeicherung:**
- State nur lokal im Frontend während Bearbeitung
- Bei Release (onMouseUp/onTouchEnd) → JSON an Backend

#### Mobile First / Fullscreen

**Mobile Verhalten:**
- Antippen der Grafik → automatischer Fullscreen im Querformat
- Touch-Gesten für Draggable Points
- Pinch-to-Zoom (optional)

**Desktop Verhalten:**
- Klick auf Grafik → vergrößerte Edit-Ansicht (Modal/Overlay)
- Keine Bildschirmrotation

#### Tech Stack

**Frontend:**
- React + D3.js oder Konva.js oder React-Flow
- KEIN Canvas mit dauerhafter 60fps-Loop
- SVG-basiert für Performance

**Backend:**
- Bestehender `/api/curves` Endpoint
- JSON-Format: `[{time: "HH:MM", intensity: number}, ...]`

#### UI Mockup

```
┌────────────────────────────────────────────────────────┐
│  ▼ Far Red (39%)                              [✓] Aktiv │
├────────────────────────────────────────────────────────┤
│ 100% ┤                      ●────────●                  │
│      │                    ╱          ╲                 │
│  80% ┤                  ╱              ╲               │
│      │                ╱                  ╲             │
│  60% ┤              ╱                      ╲           │
│      │            ╱                          ╲         │
│  40% ┤          ●                              ●       │
│      │        ╱                                  ╲     │
│  20% ┤      ╱                                      ╲   │
│      │    ╱                                          ╲ │
│   0% ┼──●────────────────────────────────────────────●─┤
│      └──┬────┬────┬────┬────┬────┬────┬────┬────┬────┬─┘
│       00:00 03:00 06:00 09:00 12:00 15:00 18:00 21:00 24:00
│                                                          │
│  [📱 Vollbild bearbeiten]                               │
└────────────────────────────────────────────────────────┘

Keyframes: (automatisch generiert)
┌──────────┬───────────┐
│ Zeit     │ Intensität│
├──────────┼───────────┤
│ 00:00    │ 0%        │
│ 06:00    │ 40%       │
│ 10:00    │ 100%      │
│ 14:00    │ 100%      │
│ 18:00    │ 40%       │
│ 24:00    │ 0%        │
└──────────┴───────────┘
```

#### Akzeptanzkriterien

- [ ] Keyframes können per Drag & Drop gesetzt/verschoben werden
- [ ] Bezier-Interpolation zwischen Punkten
- [ ] Mobile: Fullscreen-Modus im Querformat
- [ ] Desktop: Vergrößerte Bearbeitungsansicht
- [ ] Automatische Tabellen-Synchronisation
- [ ] JSON wird bei Release an Backend gesendet
- [ ] Alle 4 Kanäle unterstützt (Far Red, Warm White, Cool White, UV)
- [ ] Performance: Kein 60fps-Loop, nur Event-basierte Updates

#### Technische Umsetzung

**Dateien:**
- `static/js/modules/curve-editor.js` (NEU)
- `static/css/curve-editor.css` (NEU)
- `curves.js` (Integration)

**Bibliotheken (Auswahl):**
- Option A: D3.js (bewährt, flexibel)
- Option B: Konva.js (Canvas mit Touch-Support)
- Option C: Vanilla SVG + Event Handlers

---

### Feature #1: Device Status Dashboard

**Ziel**: Zentrale Übersicht aller schaltbaren Geräte mit Manual Override

**Aufwand**: 1-2 Tage

#### Anforderungen

**Dashboard Widget** (Collapsible!):
- Status aller schaltbaren Geräte (Entfeuchter, Heizung, etc.)
- Auto/Manual Toggle pro Gerät
- Aktueller Zustand: ON/OFF + Auto-Status
- Manuelles Überschreiben mit einem Klick
- Letzte Aktion + Trigger-Grund

**Device-Typen** (aktuell):
- Entfeuchter (bereits vorhanden)
- Heizung (geplant)
- Lüftung (geplant)

**Manual Override Flow**:
1. User sieht: "Entfeuchter: AUTO (läuft)"
2. User klickt: "Manual Override"
3. System wechselt: AUTO → MANUAL
4. User kann jetzt ON/OFF schalten
5. User kann zurück zu AUTO

**UI/UX**:
```
┌─────────────────────────────────────┐
│ ► Schaltbare Geräte                │ ← Collapsible!
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ▼ Schaltbare Geräte                │
├─────────────────────────────────────┤
│ Entfeuchter                         │
│ [AUTO] [MANUAL]  ● Läuft           │
│ Letzte Aktion: Auto (Feucht 67%)    │
├─────────────────────────────────────┤
│ Heizung (geplant)                   │
│ [AUTO] [MANUAL]  ○ Aus             │
│ Letzte Aktion: Manual (19:45)       │
└─────────────────────────────────────┘
```

#### Technische Umsetzung

**Frontend**:
- Neues Modul: `static/js/modules/devices.js`
- Widget auf Dashboard (`environment.js` erweitern)
- State Management via `state.js`

**Backend**:
- Erweitern: `dehumidifier_bp.py`
- Neuer Endpoint: `POST /api/room/mode` (auto/manual toggle)
- Status-Erweiterung in `GET /api/room`

#### Akzeptanzkriterien

- [ ] Dashboard zeigt alle schaltbaren Geräte
- [ ] Auto/Manual Toggle funktioniert
- [ ] Manual Override deaktiviert Auto-Modus
- [ ] Zurück zu Auto reaktiviert Automatik sofort
- [ ] Last Action wird angezeigt (Trigger + Timestamp)
- [ ] Mobile-optimiert (Touch-friendly)
- [ ] Collapsible Section (zugeklappt per default)

---

### Feature #2: Hochauflösende Kurven-Visualisierung

**Ziel**: Präzise 15-Minuten-Schritte in Chart-Visualisierung

**Aufwand**: 0.5 Tage

#### Anforderungen

**Aktuelle Chart-Auflösung**:
- 24 Steps (1 Step = 1 Stunde)
- Zu grob für 15-Minuten-Änderungen

**Neue Chart-Auflösung**:
- 96 Steps (1 Step = 15 Minuten)
- Genauigkeit: Alle 15 Minuten ein Datenpunkt
- Ermöglicht präzise Visualisierung

**Betroffene Komponente**:
- Oberes Chart auf Kurvenseite (`modules/curves.js`)
- Recharts Konfiguration

#### Technische Umsetzung

**Frontend** (`curves.js`):
```javascript
// VORHER: 24 Steps (stündlich)
const steps = Array.from({ length: 24 }, (_, i) => ({
  time: `${i.toString().padStart(2, '0')}:00`,
  ...
}));

// NACHHER: 96 Steps (15-Minuten)
const steps = Array.from({ length: 96 }, (_, i) => ({
  time: formatTime(i * 15), // 0, 15, 30, 45, ...
  ...
}));

function formatTime(minutes) {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}`;
}
```

**Performance**:
- Chart bleibt flüssig (Recharts optimiert für 96 Punkte)
- Keine Backend-Änderungen nötig (nur Frontend)

#### Akzeptanzkriterien

- [ ] Chart zeigt 96 Datenpunkte (alle 15 Minuten)
- [ ] X-Achse zeigt lesbare Zeitstempel (z.B. 06:00, 06:15, 06:30)
- [ ] Interpolation bleibt korrekt
- [ ] Performance: Chart lädt < 500ms
- [ ] Mobile-View: X-Achse lesbar (ggf. nur jede Stunde labeln)

---

## 💡 Future Features (Ideen)

- **Multi-Geräte-Szenarien** (z.B. "Nacht-Modus")
- **Heizungs-Steuerung** (Temperatur-basiert)
- **Lüftungs-Automation** (zeitbasiert + Temperatur)
- **VPD-Optimierung** (Vapor Pressure Deficit)
- **Push-Benachrichtigungen** (Telegram/Email)

---

## ✅ Erledigte Features

### **v6.9.1 (2025-12-07) - Zero-Downtime BUGFIX**

**Problem gelöst:** Zero-Downtime aus v6.9.0 funktionierte NICHT - Lampen gingen kurz aus

**Root Cause:**
- `api.py` wurde beim Flask-Import geladen
- `PWMController.initialize()` wurde OHNE State-Check aufgerufen
- Alle PWM-Kanäle wurden auf 0 gesetzt → Lampen aus
- Erst danach wurde State geladen und Werte wiederhergestellt → Fade-In

**Fix:**
- ✅ `PWMController.initialize()` mit neuem Parameter `skip_zero_init`
- ✅ `api.py` prüft `state_exists()` VOR initialize()
- ✅ `main.py` prüft State VOR initialize()

**Test-Ergebnis:**
```
VOR RESTART:  Ch2: 34%, Ch3: 65%
NACH RESTART: Ch2: 34%, Ch3: 65%  ← LAMPEN BLIEBEN AN!
```

**Dateien:**
- `grow_pi/lamps/pwm_controller.py` (GEÄNDERT)
- `grow_pi/web/api.py` (GEÄNDERT)
- `grow_pi/main.py` (GEÄNDERT)

---

### **v6.9.0 (2025-12-06) - PWM Zero-Downtime Restarts (Initial)**

**Problem gelöst:** LED-Flackern bei Service-Restart (TEILWEISE - siehe v6.9.1)

**Implementierung:**
- ✅ Neue `disconnect()` Methode im PWMController
- ✅ State-Persistence in `/run/growpi/pwm_state.json`
- ✅ Warm-Restart Erkennung beim Startup
- ✅ Systemd RuntimeDirectoryPreserve

**Dateien:**
- `grow_pi/utils/pwm_state.py` (NEU)
- `grow_pi/lamps/pwm_controller.py` (GEÄNDERT)
- `grow_pi/main.py` (GEÄNDERT)
- `systemd/grow-pi.service` (GEÄNDERT)

---

### **v6.8.0 (2025-12-06) - Feature Pack: Usability & Automation**

**Parallel-Agenten Workflow (11 Agents):**
- ✅ Feature #1: Version Display im Header (KRITISCH)
- ✅ Feature #2: Zeitbasierte Geräte-Schaltung (Priority-Logik + Fallback)
- ✅ Feature #3: Collapsible Sections (Accordion UI)
- ✅ Feature #4: Kurven-Presets System (Save/Load/Manage)

**Highlights:**
- Smart Fallback-Logik: Zeitfenster endet → prüfe Feuchtigkeit (nicht einfach AUS!)
- System-Presets: Keimung, Wachstum, Blüte (wissenschaftlich realistisch)
- localStorage Persistence für Accordion-Zustand
- Deployment-Verification via Version Badge

**Technical:**
- 2 neue DB-Tabellen (device_time_schedules, curve_presets)
- 9 neue API Endpoints
- 3 neue JS Module (accordion.js + Updates)
- ~2100 LOC Added

---

### v6.7.0 (2025-12-06) - Bug Fixes & Deployment

**Frontend Fixes:**
- Fixed: Kurven-Tab not loading data (added tab-switch handler in `utils.js`)
- Fixed: Cost/Room buttons CSS styling (added `.cost-period-btn` and `.room-toggle-btn`)
- Added: Dynamic module loading on tab switch

**Backend Fixes:**
- Fixed: Missing blueprints deployment (`costs_bp.py`, `dehumidifier_bp.py`)
- Fixed: Blueprint registration in `api.py`
- Fixed: DehumidifierController initialization

**Documentation:**
- Updated CHANGELOG.md with all version history
- Rewrote README.md with v6.6 architecture diagrams

---

### v6.6.0 (2025-12-06) - CPU Optimization

**CPU Load:** 75% → 15-25% (-67% reduction!)

- Replaced `time.sleep(0.1)` loop with `threading.Event.wait()`
- Increased sensor logging interval from 60s to 120s
- DHT22 sensor cache lifetime: 3s → 30s

---

### v6.5.0 (2025-12-06) - Modular Architecture

**Frontend Refactoring** (-86% LOC reduction)
- **BEFORE**: Monolithic `index.html` (2894 LOC)
- **AFTER**: Modular architecture (408 LOC + 8 modules)

**Backend Refactoring** (8 Flask Blueprints)
- Clean separation of concerns
- Service layer pattern

---

### v6.4.0 (2025-12-05) - Entfeuchter-Automatik

**Features**:
- Tuya Smart Plug Integration (Bluetooth)
- Automatische Feuchtigkeitsregelung mit Hysterese
- Soll-Wert: 60% (±5% Hysterese)
- Auto/Manual Toggle
- Min. Laufzeit: 5 Minuten (Schutz vor häufigem Schalten)
- Zeitbasierte Schaltung (Schedule) - **BASIC IMPLEMENTATION**

**Endpoints**:
- `GET /api/room` - Status (Temp, Humidity, Entfeuchter)
- `GET /api/room/config` - Automation-Config
- `POST /api/room/config` - Config aktualisieren
- `POST /api/room/dehumidifier` - Manual On/Off

**UI**: Room-Tab im Web-Interface

---

### v6.3.0 (2025-12-05) - Kosten-Monitoring

**Features**:
- Stromverbrauch-Messung (kWh/h)
- kWh-Preis Konfiguration (€/kWh)
- Kosten-Breakdown: Heute / Diese Woche / Dieser Monat
- Gerätespezifische Kosten (Lampen, Entfeuchter)
- Historische Kosten-Trends

**Endpoints**:
- `GET /api/costs?period=today|week|month`
- `GET /api/costs/config`
- `POST /api/costs/config`

**UI**: Kosten-Tab im Web-Interface

---

## 📋 Change Log

| Datum | Änderung | Autor |
|-------|----------|-------|
| 2025-12-07 | **ALLE BUGS BEHOBEN:** Entfeuchter, DHT22, Tuya-ID funktionieren | Dennis + Claude |
| 2025-12-07 | Refactoring-Plan für api.py erstellt (PLAN_API_REFACTORING.md) | Dennis + Claude |
| 2025-12-07 | Opus-Agent Analyse: api.py hat 700 Zeilen duplizierten Code | Dennis + Claude |
| 2025-12-07 | Bug #4 + #5 dokumentiert: DHT22 Sensor-Fehler, Tuya Config veraltet | Dennis + Claude |
| 2025-12-07 | Bug #1 teilweise behoben: DB-Migration funktioniert, aber Tuya-ID fehlt | Dennis + Claude |
| 2025-12-07 | v6.9.1 Zero-Downtime BUGFIX - PWM-Init Problem behoben | Dennis + Claude |
| 2025-12-07 | KRITISCHE BUGS dokumentiert: Room, Zeitschaltung, Kosten | Dennis + Claude |
| 2025-12-06 | v6.9.0 PWM Zero-Downtime implementiert und getestet | Dennis + Claude |
| 2025-12-06 | Roadmap komplett umstrukturiert: Chronologisch, Nächstes zuerst | Dennis + Claude |
| 2025-12-06 | Feature 2B.1 (Zeitbasierte Schaltung) hinzugefügt | Dennis + Claude |
| 2025-12-06 | Feature 3.1 (Version Display) + 3.2 (Collapsible) hinzugefügt | Dennis + Claude |
| 2025-12-06 | Roadmap überarbeitet - Phase 1+2 als erledigt markiert | Dennis + Claude |
| 2025-12-05 | Initial Draft - Phase 1 & 2 definiert | Dennis + Claude |

---

**Geschätzte Gesamtdauer (Features #1-#6)**: 6-10 Arbeitstage
