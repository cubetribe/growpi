# UMFASSENDE ANALYSE: Luftfeuchtigkeits-Steuerungsproblem

**Erstellt**: 2025-12-07
**Status**: ROOT CAUSE IDENTIFIZIERT
**Priorität**: KRITISCH

---

## Problem-Beschreibung

- Wenn Luftfeuchtigkeits-Werte verändert werden, springt der Zähler "komisch hin und her"
- Pfeiltasten (hoch/runter) lassen den Wert auf 30 oder 40 "random" springen
- UI wirkt "wackelig"

---

## ROOT CAUSE ANALYSIS

Das Problem ist eine **klassische Race-Condition zwischen User-Input und Auto-Refresh Polling**.

### Ursache 1: Fehlende Input-Event-Listener (KRITISCH)

Die Input-Felder `targetHumidity`, `thresholdHigh`, `thresholdLow` haben **KEINE `input` oder `change` Event-Listener**:

```javascript
// environment.js Zeilen 21-23
const targetHumidity = document.getElementById('targetHumidity');
const thresholdHigh = document.getElementById('thresholdHigh');
const thresholdLow = document.getElementById('thresholdLow');
```

Diese Elemente werden in `setupEventListeners()` (Zeile 354-374) **nicht registriert**!

### Ursache 2: Polling während User-Eingabe (HOCHPROBLEMATISCH)

```javascript
// environment.js Zeilen 55-62
statusInterval = setInterval(() => {
    fetchRoomStatus();    // Alle 10 Sekunden
    fetchSchedules();
}, 10000);
```

**Ablauf bei User-Eingabe:**

1. User klickt auf Input-Feld und ändert Wert von "60" zu "62"
2. Browser zeigt "62" im Input-Feld
3. Nach maximal 10 Sekunden wird `fetchRoomStatus()` aufgerufen
4. Backend antwortet mit aktuellen Wert aus Datenbank (z.B. 60)
5. `updateDehumidifierDisplay()` wird aufgerufen
6. **BOOM**: `.value = 60` überschreibt den gerade eingegebenen Wert "62"

### Ursache 3: "Wackeln" durch Pfeiltasten

Wenn User Pfeiltasten nutzt:
- Browser updatet intern das `value`-Attribut
- `updateDehumidifierDisplay()` wird vom Polling aufgerufen
- Wert wird mit Backend-Wert überschrieben
- Resultat: Der Wert "springt" zurück auf Server-Wert

**Die "30 oder 40" sind wahrscheinlich alte Werte aus der Datenbank.**

---

## CODE-SNIPPETS DER PROBLEMATISCHEN STELLEN

### Problem 1: Keine Input-Event-Handler

**Datei**: `environment.js`, Zeilen 354-374

```javascript
function setupEventListeners() {
    // FEHLER: targetHumidity, thresholdHigh, thresholdLow haben KEINE Listener!
    dehumidifierOn?.addEventListener('click', () => controlDehumidifier('on'));
    dehumidifierOff?.addEventListener('click', () => controlDehumidifier('off'));
    // ...
}
```

### Problem 2: Polling überschreibt User-Input

**Datei**: `environment.js`, Zeilen 134-136

```javascript
// In updateDehumidifierDisplay():
if (targetHumidity) targetHumidity.value = dehumidifier.config.target;
if (thresholdHigh) thresholdHigh.value = dehumidifier.config.threshold_high;
if (thresholdLow) thresholdLow.value = dehumidifier.config.threshold_low;
// ^^^ Das ist der ROOT CAUSE des "Wackelns"!
```

---

## RACE-CONDITION SEQUENZ

```
Zeit   | Aktion                          | Input | DB  | UI
───────┼─────────────────────────────────┼───────┼─────┼────
00:00  | Page laden                      | -     | 60  | 60
00:01  | User tippt "62"                 | "62"  | 60  | 62 ✓
00:05  | fetchRoomStatus() startet       | "62"  | 60  | 62
00:06  | API antwortet: target=60        | "62"  | 60  | 62
00:07  | updateDehumidifierDisplay()     | -     | 60  | 60 ✗
       | targetHumidity.value = 60       |       |     |
```

---

## FIX-VORSCHLÄGE

### PRIORITÄT 1 (KRITISCH) - Focus-State Tracking

```javascript
// Am Anfang von environment.js hinzufügen:
let isUserEditing = {
    targetHumidity: false,
    thresholdHigh: false,
    thresholdLow: false
};

// In setupEventListeners() hinzufügen:
targetHumidity?.addEventListener('focus', () => {
    isUserEditing.targetHumidity = true;
});
targetHumidity?.addEventListener('blur', () => {
    isUserEditing.targetHumidity = false;
});
// Ähnlich für thresholdHigh und thresholdLow
```

### PRIORITÄT 2 (KRITISCH) - updateDehumidifierDisplay() modifizieren

```javascript
function updateDehumidifierDisplay(dehumidifier) {
    // Update config input values - NUR wenn User NICHT gerade bearbeitet
    if (targetHumidity && !isUserEditing.targetHumidity) {
        targetHumidity.value = dehumidifier.config.target;
    }
    if (thresholdHigh && !isUserEditing.thresholdHigh) {
        thresholdHigh.value = dehumidifier.config.threshold_high;
    }
    if (thresholdLow && !isUserEditing.thresholdLow) {
        thresholdLow.value = dehumidifier.config.threshold_low;
    }
}
```

### PRIORITÄT 3 (OPTIONAL) - Dirty-State Tracking

```javascript
let dirtyState = {
    targetHumidity: false,
    thresholdHigh: false,
    thresholdLow: false
};

targetHumidity?.addEventListener('input', () => {
    dirtyState.targetHumidity = true;
});

// Nach saveRoomConfig():
dirtyState.targetHumidity = false;
```

---

## BETROFFENE DATEIEN

| Datei | Problem |
|-------|---------|
| `pi-controller/grow_pi/web/static/js/modules/environment.js` | Race-Condition, fehlende Event-Listener |

---

## ZUSAMMENFASSUNG

| # | Bug | Severity | Fix-Zeit |
|---|-----|----------|----------|
| 1 | Input-Wert wird vom Poll überschrieben | KRITISCH | 10 Min |
| 2 | Keine focus/blur Handler | KRITISCH | 10 Min |
| 3 | Kein "Dirty State" Tracking | MITTEL | 15 Min |

**Empfehlung**: Fix 1 und 2 sofort implementieren.
