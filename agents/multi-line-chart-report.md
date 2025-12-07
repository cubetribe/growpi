# Multi-Line Preview Chart - Implementierungsbericht

**Datum:** 2025-12-07
**Agent:** Opus 4.5
**Status:** IMPLEMENTIERT - Wartet auf Deployment

---

## Zusammenfassung

Das Balken-Preview-Chart auf der Kurven-Seite wurde erfolgreich durch ein Multi-Line SVG Chart ersetzt. Das neue Chart zeigt alle 4 Lichtkanal-Kurven gleichzeitig als farbige Linien an.

---

## Geaenderte Dateien

### 1. `/pi-controller/grow_pi/web/static/js/modules/curves.js`

**Aenderungen:**
- Neue Konstanten hinzugefuegt:
  - `channelNames` - Namen der Kanaele (Far Red, Warm White, Cool White, UV)
  - `previewChannelVisibility` - Sichtbarkeitsstatus pro Kanal
  - `PREVIEW_STORAGE_KEY` - localStorage Key fuer Persistenz

- Neue Funktionen:
  - `renderPreview()` - Komplett neu geschrieben fuer SVG Multi-Line Chart
  - `calculateAllChannelsPreview()` - Berechnet Interpolation fuer alle 4 Kanaele
  - `loadPreviewChannelVisibility()` - Laedt Checkbox-Status aus localStorage
  - `savePreviewChannelVisibility()` - Speichert Checkbox-Status
  - `togglePreviewChannel()` - Toggle-Funktion fuer Checkboxen
  - `createPreviewCheckboxes()` - Erstellt die Checkbox-UI dynamisch

- Modifizierte Funktionen:
  - `initCurvesTab()` - Laedt jetzt Checkbox-Visibility beim Start
  - `fetchCurves()` - Erstellt Checkboxen nach dem Laden
  - `updateLocalPreview()` - Vereinfacht, nutzt jetzt Multi-Line Rendering

**Technische Details:**
- SVG-basiertes Chart (kein externes Library)
- Lineare Interpolation zwischen Kurvenpunkten
- 96 Datenpunkte (15-Minuten-Aufloesung)
- Y-Achse: 0-100% mit Labels
- Grid-Linien fuer bessere Lesbarkeit
- Gefuellte Flaechen unter den Linien (transparent)

### 2. `/pi-controller/grow_pi/web/static/css/main.css`

**Neue CSS-Klassen:**
```css
.preview-chart              - Container fuer SVG (height: 120px)
.preview-svg                - SVG Element Styles
.preview-line               - Linien-Styles (stroke-width: 2)
.preview-grid-line          - Grid-Linien (rgba weiss)
.preview-axis-label         - Y-Achsen-Labels (0%, 50%, 100%)
.preview-channel-checkboxes - Checkbox-Container
.preview-channel-checkbox   - Label mit Checkbox
.preview-channel-dot        - Farbiger Punkt pro Kanal
.preview-channel-name       - Kanal-Name Text
```

**Responsive Design:**
- Media Query fuer `max-width: 400px`
- Kleinere Checkboxen und Fonts auf Mobile

### 3. `/pi-controller/grow_pi/web/static/index.html`

**Minimale Aenderung:**
- Preview-Titel von "24h Vorschau (aktueller Kanal)" zu "24h Vorschau" geaendert
- Kommentar hinzugefuegt wo Checkboxen eingefuegt werden

---

## Features

### Multi-Line Chart
- 4 farbige Linien (eine pro Kanal)
- Farben: Far Red (#ff4444), Warm White (#ffbb44), Cool White (#88ddff), UV (#cc66ff)
- Transparente Flaechen unter den Linien fuer Tiefeneffekt
- Grid-Linien horizontal (0%, 50%, 100%) und vertikal (00:00, 06:00, 12:00, 18:00, 24:00)

### Checkbox-Steuerung
- 4 Checkboxen ueber dem Chart
- Farbiger Punkt neben jedem Kanal-Namen
- Standard: Alle 4 aktiviert
- Click togglet Liniensichtbarkeit
- Status wird in localStorage gespeichert (`growpi-preview-channels`)

### UI-Struktur
```
+----------------------------------------------------------+
| [x] Far Red  [x] Warm White  [x] Cool White  [x] UV      |
+----------------------------------------------------------+
| 100% |----------------------------------------           |
|      |       /\                                          |
|  50% |------/--\---------/\--------------------------    |
|      |     /    \       /  \                             |
|   0% |----/------\-----/----\------------------------    |
|      00:00  06:00  12:00  18:00  24:00                   |
+----------------------------------------------------------+
```

---

## Deployment-Befehle

**WICHTIG: Noch nicht ausgefuehrt - Wartet auf Genehmigung!**

```bash
# 1. curves.js kopieren
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/static/js/modules/curves.js admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/js/modules/curves.js

# 2. main.css kopieren
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/static/css/main.css admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/css/main.css

# 3. index.html kopieren
sshpass -p 'Mi83xer#' scp /Users/denniswestermann/Desktop/Coding\ Projekte/GrowPi/pi-controller/grow_pi/web/static/index.html admin@192.168.0.86:/opt/grow-pi/grow_pi/web/static/index.html

# 4. Service neustarten (OPTIONAL - nur wenn noetig)
sshpass -p 'Mi83xer#' ssh admin@192.168.0.86 "sudo systemctl restart grow-pi"
```

**Hinweis:** Da es sich um statische Dateien (JS, CSS, HTML) handelt, sollte ein Browser-Refresh (Ctrl+Shift+R / Cmd+Shift+R) ausreichen. Ein Service-Neustart ist nur erforderlich, wenn der Browser die Dateien gecached hat.

---

## Screenshots

### Vorher (Balken-Chart)
![Vorher](/.playwright-mcp/curves-before-multiline.png)

- Einzelne Balken fuer aktiven Kanal
- Nur ein Kanal gleichzeitig sichtbar
- Titel: "24h Vorschau (aktueller Kanal)"

### Nachher (Multi-Line Chart)
*(Screenshot nach Deployment verfuegbar)*

- 4 farbige Linien
- Alle Kanaele gleichzeitig
- Checkboxen zur Steuerung
- Titel: "24h Vorschau"

---

## Testplan

1. [ ] Deployment der Dateien auf den Pi
2. [ ] Browser-Cache leeren (Ctrl+Shift+R)
3. [ ] Kurven-Tab oeffnen
4. [ ] Pruefen: Alle 4 Linien sichtbar
5. [ ] Pruefen: Checkboxen funktionieren (Toggle)
6. [ ] Pruefen: localStorage Persistenz (Seite neu laden)
7. [ ] Pruefen: Kurven editieren aktualisiert Chart
8. [ ] Pruefen: Mobile Responsive Design

---

## Bekannte Limitationen

- Keine Tooltips beim Hovern ueber Linien (koennte spaeter hinzugefuegt werden)
- Keine Animation beim Toggle der Linien
- Chart-Breite basiert auf Container-Breite beim ersten Render

---

## Naechste Schritte

1. **Genehmigung vom User einholen** fuer Deployment
2. Dateien auf Pi kopieren
3. Browser-Test durchfuehren
4. Screenshot vom neuen Chart machen
5. Optional: Service-Neustart falls noetig
