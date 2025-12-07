# Bezier Curve Editor Implementation Report

**Datum**: 2025-12-07
**Status**: Implementierung abgeschlossen
**Branch**: refactoring/phase-1-modularization

---

## Zusammenfassung

Ein interaktiver Bezier Curve Editor wurde implementiert, der die statische 24h-Vorschau durch ein visuelles Bearbeitungswerkzeug ersetzt. Der Editor ermoeglicht das direkte Zeichnen und Bearbeiten von Lichtkurven aehnlich wie Cubase Automation Curves oder BIOS-Luefterkurven.

---

## Erstellte Dateien

### 1. `/pi-controller/grow_pi/web/static/js/modules/curve-editor.js`
**Zeilen**: ~950 Zeilen
**Funktion**: Hauptmodul fuer den interaktiven Bezier Curve Editor

**Features**:
- SVG-basierter interaktiver Graph (kein Canvas mit 60fps-Loop)
- Draggable Keyframe Anchor Points
- Catmull-Rom zu Bezier Kurven-Konvertierung fuer glatte Kurven
- Touch und Mouse Support
- Fullscreen-Modus fuer Mobile (Querformat)
- Automatische Tabellen-Synchronisation

**Exportierte Klasse/Funktionen**:
```javascript
export class BezierCurveEditor { ... }
export function createCurveEditor(container, channel, initialPoints, options) { ... }
```

### 2. `/pi-controller/grow_pi/web/static/css/curve-editor.css`
**Zeilen**: ~400 Zeilen
**Funktion**: Styling fuer den Curve Editor

**Features**:
- Dark Theme passend zum GrowPi Design
- Glassmorphism-Effekte
- Touch-freundliche Hit-Areas
- Responsive Design
- Fullscreen-Overlay mit Animationen
- Reduced Motion Support (Accessibility)

---

## Geaenderte Dateien

### 1. `/pi-controller/grow_pi/web/static/js/modules/curves.js`
**Aenderungen**:
- Import des neuen `curve-editor.js` Moduls
- Neue State-Variable `curveEditors = {}` fuer Editor-Instanzen
- Erweiterte `renderCurves()` Funktion:
  - Initialisiert Bezier-Editor fuer jeden Kanal
  - Richtet onChange/onSave Callbacks ein
  - Synchronisiert Editor mit Punkte-Tabelle
- Neue Funktion `renderPointsTable(channel)` fuer partielle Updates
- Neue Funktion `setupPointsEventListeners(container, channel)` fuer Event-Handling
- Aktualisierte `setupCurveEventListeners()` mit Editor-Synchronisation

### 2. `/pi-controller/grow_pi/web/static/index.html`
**Aenderungen**:
- CSS-Link fuer `curve-editor.css` hinzugefuegt

---

## Verwendete Browser-APIs

### SVG APIs
- `document.createElementNS('http://www.w3.org/2000/svg', ...)` - SVG-Element-Erstellung
- SVG `<path>` mit kubischen Bezier-Kurven (`C` Command)
- SVG `<linearGradient>`, `<filter>` fuer visuelle Effekte

### Event APIs
- `MouseEvent` (click, mousedown, mousemove, mouseup)
- `TouchEvent` (touchstart, touchmove, touchend, touchcancel)
- `KeyboardEvent` (keydown fuer Escape)
- `PointerEvent` ID Tracking fuer Multi-Touch

### Screen Orientation API
- `screen.orientation.lock('landscape')` - Sperrt Bildschirm im Querformat (Mobile)
- `screen.orientation.unlock()` - Entsperrt Bildschirm

### Fullscreen API
- Manuell implementiert mit CSS-Overlay (besser Browser-kompatibel als native Fullscreen API)

### LocalStorage
- Wird von `curves.js` bereits verwendet (uebernommen)

---

## Architektur-Entscheidungen

### 1. SVG statt Canvas
**Grund**: Event-basierte Updates ohne 60fps-Loop, besser fuer Akku-Verbrauch auf mobilen Geraeten.

### 2. Catmull-Rom zu Bezier Konvertierung
**Grund**: Catmull-Rom Splines sind einfacher zu kontrollieren (Punkte liegen AUF der Kurve), aber SVG unterstuetzt nur Bezier. Die Konvertierung erfolgt mit konfigurierbarer Spannung (tension = 0.3).

### 3. Separate Editor-Instanz pro Kanal
**Grund**: Jeder Kanal hat seinen eigenen visuellen Editor, der unabhaengig bearbeitet werden kann. Die globale 24h-Vorschau zeigt weiterhin alle Kanaele zusammen.

### 4. Dual-Sync (Editor <-> Tabelle)
**Grund**: Benutzer koennen sowohl visuell als auch per Tabellen-Eingabe arbeiten. Aenderungen in einem werden sofort im anderen reflektiert.

---

## Benutzerinteraktion

### Desktop
| Aktion | Ergebnis |
|--------|----------|
| Klick auf leere Stelle | Neuen Punkt setzen |
| Punkt ziehen | Punkt verschieben |
| Doppelklick auf Punkt | Punkt loeschen |
| Klick auf "Vollbild" | Vergroesserte Bearbeitungsansicht |

### Mobile
| Aktion | Ergebnis |
|--------|----------|
| Tippen auf leere Stelle | Neuen Punkt setzen |
| Punkt ziehen | Punkt verschieben |
| Lang druecken (0.8s) auf Punkt | Punkt loeschen |
| Doppel-Tippen auf Punkt | Punkt loeschen |
| Tippen auf "Vollbild" | Fullscreen im Querformat |

---

## Konfigurierbare Parameter

```javascript
const EDITOR_CONFIG = {
    // SVG dimensions
    width: 400,
    height: 200,
    padding: { top: 20, right: 20, bottom: 30, left: 45 },

    // Keyframe styling
    keyframeRadius: 10,
    keyframeRadiusTouch: 14,
    keyframeStrokeWidth: 2,

    // Curve styling
    curveStrokeWidth: 2.5,

    // Grid
    gridLinesX: 8, // Every 3 hours
    gridLinesY: 4, // 0%, 25%, 50%, 75%, 100%

    // Interaction
    snapToGridTime: 15, // minutes
    snapToGridIntensity: 5, // percent
    longPressDeleteMs: 800,
    doubleTapDeleteMs: 300,
};
```

---

## Bekannte Einschraenkungen

### 1. Orientation Lock
Die `screen.orientation.lock()` API ist nicht in allen Browsern verfuegbar oder erfordert spezielle Berechtigungen. Bei nicht unterstuetzten Browsern funktioniert der Fullscreen-Modus trotzdem, nur ohne automatische Rotation.

### 2. Keine API-Aufrufe waehrend Drag
Waehrend des Ziehens werden keine Server-Requests gesendet. Erst beim Release (mouseup/touchend) wird `onSave` aufgerufen. Der eigentliche API-Call erfolgt erst beim Klick auf "Kurven Speichern".

### 3. Punkte-Kollision
Wenn zwei Punkte weniger als 5 Minuten auseinander liegen, wird kein neuer Punkt gesetzt. Dies verhindert unbeabsichtigte Dopplungen.

### 4. Browser-Kompatibilitaet
Getestet/unterstuetzt:
- Chrome/Edge (Desktop + Mobile)
- Firefox (Desktop + Mobile)
- Safari (Desktop + iOS)

Nicht unterstuetzt:
- Internet Explorer (keine ES6 Module)

---

## Dateien-Uebersicht

```
pi-controller/grow_pi/web/static/
├── css/
│   ├── main.css          (unveraendert)
│   └── curve-editor.css  (NEU - 400 Zeilen)
├── js/
│   └── modules/
│       ├── curves.js     (GEAENDERT - Editor-Integration)
│       └── curve-editor.js (NEU - 950 Zeilen)
└── index.html            (GEAENDERT - CSS-Link)
```

---

## Test-Checkliste

- [x] Punkte per Klick/Tippen setzen
- [x] Punkte per Drag & Drop verschieben
- [x] Punkte per Doppelklick/Lang-Druecken loeschen
- [x] Bezier-Kurve wird korrekt gerendert
- [x] Tabelle synchronisiert sich mit Editor
- [x] Editor synchronisiert sich mit Tabelle
- [x] Fullscreen-Modus funktioniert
- [x] Mobile Touch-Gesten funktionieren
- [x] "Kurven Speichern" sendet korrekte Daten
- [x] JSON Import aktualisiert Editor
- [x] Preset-Anwendung aktualisiert Editor

---

## Naechste Schritte (Optional)

1. **Undo/Redo**: Lokaler History-Stack fuer Rueckgaengig-Funktion
2. **Bezier-Handles**: Sichtbare Kontrollpunkte fuer feinere Kurvensteuerung
3. **Zoom**: Rein-/Rauszoomen fuer praezise Bearbeitung
4. **Copy/Paste**: Punkte oder ganze Kurven zwischen Kanaelen kopieren

---

**Erstellt von**: Claude Opus 4.5
**Projekt**: GrowPi Greenhouse Management System
