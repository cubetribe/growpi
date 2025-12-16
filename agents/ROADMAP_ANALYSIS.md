# ROADMAP ANALYSIS

**Erstellt**: 2025-12-07
**Roadmap Version**: v6.15.0
**Analyst**: Master Orchestrator

---

## Zusammenfassung

Die Roadmap enthält eine Mischung aus:
- **Behobenen Bugs** (bereits erledigt)
- **Offenen Bugs** (zu untersuchen/testen)
- **Technischen Schulden** (Refactoring)
- **Neuen Features** (teilweise implementiert)

---

## Extrahierte Items

### OFFENE BUGS (Priorität: HOCH)

| ID | Titel | Typ | Status | Priorität | Abhängigkeiten |
|----|-------|-----|--------|-----------|----------------|
| R1 | Bug #2: Zeitschaltung/Override | bug | pending | high | Bug #1 (behoben) |
| R2 | Bug #8: Room Automation Status-Desync | bug | pending | critical | - |
| R3 | Bug #11: Datalog/History Problem | bug | pending | high | - |

### TEILWEISE BEHOBENE ITEMS (Verifikation nötig)

| ID | Titel | Typ | Status | Priorität | Abhängigkeiten |
|----|-------|-----|--------|-----------|----------------|
| R4 | Bug #7: Verlauf-Seite | bug | partially-fixed | medium | - |

### TECHNISCHE SCHULDEN

| ID | Titel | Typ | Status | Priorität | Abhängigkeiten |
|----|-------|-----|--------|-----------|----------------|
| R5 | Refactoring #1: api.py Modularisierung | tech-debt | pending | high | System erst stabilisieren |

### FEATURES (UI Polish)

| ID | Titel | Typ | Status | Priorität | Abhängigkeiten |
|----|-------|-----|--------|-----------|----------------|
| R6 | Feature #0: Bezier Curve Editor - Mobile UI Polish | feature | pending | medium | Grundfunktion implementiert |
| R7 | Feature #1: Device Status Dashboard | feature | pending | low | - |
| R8 | Feature #2: Hochauflösende Kurven-Visualisierung | feature | pending | low | - |

---

## Detailanalyse pro Item

### R1 - Bug #2: Zeitschaltung/Override

**Beschreibung**: Die Zeitschaltung für den Entfeuchter wurde bisher nicht getestet, da Bug #1 (Room/Entfeuchter-Steuerung) erst kürzlich behoben wurde.

**Zu testen**:
- Zeitfenster im UI anlegen
- Prüfen ob Scheduler greift
- Override-Funktion testen

**Betroffene Dateien** (vermutlich):
- `pi-controller/grow_pi/utils/dehumidifier_controller.py`
- `pi-controller/grow_pi/web/blueprints/dehumidifier_bp.py`
- `frontend/static/js/modules/environment.js` (oder room.js)

**Risiko**: Niedrig (Grundfunktion existiert)

---

### R2 - Bug #8: Room Automation Status-Desync (KRITISCH)

**Beschreibung**: Der Status-Sync zwischen internem State und echtem Tuya-Gerätestatus funktioniert nicht zuverlässig.

**Bekannte Probleme**:
1. ✅ Problem 1 behoben: `_sync_device_status()` implementiert
2. **Problem 2 (KRITISCH)**: `SmartPlugController.turn_on()/turn_off()` gibt IMMER `True` zurück - keine Verifikation!
3. **Problem 3**: `_ensure_state()` hat Early-Return bei manueller Steuerung

**Symptome**:
- User drückt "Einschalten" → Gerät schaltet nicht ein
- User drückt "Ausschalten" → Log sagt "OFF", aber Gerät bleibt an

**Betroffene Dateien**:
- `/pi-controller/grow_pi/lamps/smart_plug_controller.py` (Bug #9)
- `/pi-controller/grow_pi/utils/dehumidifier_controller.py` (Bug #10)

**Risiko**: HOCH (User-facing, kritische Funktion)

**Hinweis**: Bug #9 und #10 sind als "BEHOBEN" markiert (v6.14.0), aber R2 ist noch "TEILWEISE BEHOBEN". Es gibt einen bestehenden Report: `/agents/bug9-10-plug-control-fix-report.md`

---

### R3 - Bug #11: Datalog/History Problem

**Beschreibung**: Unklares Problem mit der History-Seite.

**Bekannte Symptome**:
- Console zeigt `[History] Loading data for 24 hours (downsampled)`
- Unklar ob Daten korrekt geladen werden

**Zu untersuchen**:
- Werden Daten korrekt geladen?
- Funktioniert die Chart-Darstellung?
- API-Response prüfen
- SQLite-Daten prüfen

**Betroffene Dateien** (vermutlich):
- `frontend/static/js/modules/history.js`
- `pi-controller/grow_pi/web/blueprints/logs_bp.py`
- `pi-controller/grow_pi/db.py`

**Risiko**: Mittel (Datenvisualisierung)

---

### R4 - Bug #7: Verlauf-Seite (Teilweise behoben)

**Beschreibung**: Mehrere Probleme wurden behoben, aber es ist unklar ob alles funktioniert.

**Behoben**:
- Steckdosen-Namen werden korrekt angezeigt
- Zeitfilter funktioniert für alle 3 Charts synchron
- "1h" Button hinzugefügt
- Chart.js Date-Adapter für echte Zeit-Achsen
- Stromverbrauch-Daten werden jetzt angezeigt

**Risiko**: Niedrig (meiste Fixes bereits deployed)

---

### R5 - Refactoring #1: api.py Modularisierung

**Beschreibung**: `api.py` hat 1119 Zeilen mit ~700 Zeilen dupliziertem Code.

**Problem**:
- Nur 3 von 9 Blueprints sind registriert
- Routes existieren sowohl in api.py als auch in Blueprints
- Fehleranfällig bei Änderungen

**Ziel**:
- api.py von 1119 → ~200 Zeilen
- Alle 9 Blueprints aktivieren
- Duplizierten Code entfernen

**Plan existiert**: `docs/PLAN_API_REFACTORING.md`

**Risiko**: HOCH (große Änderungen, Regression möglich)

**Abhängigkeit**: System erst stabilisieren!

---

### R6 - Feature #0: Bezier Curve Editor - Mobile UI Polish

**Beschreibung**: Grundfunktion ist implementiert, aber Mobile-UI braucht Polish.

**TODO**:
- Mobile Layout verbessern
- Touch-Targets größer machen
- Fullscreen-Modus auf Mobile optimieren
- Responsive Design überarbeiten

**Betroffene Dateien**:
- `frontend/static/js/modules/curve-editor.js`
- `frontend/static/css/curve-editor.css`

**Risiko**: Niedrig (nur UI-Verbesserungen)

---

### R7 - Feature #1: Device Status Dashboard

**Beschreibung**: Zentrale Übersicht aller schaltbaren Geräte mit Manual Override.

**Status**: Nicht implementiert
**Aufwand**: 1-2 Tage

**Risiko**: Niedrig (neues Feature)

---

### R8 - Feature #2: Hochauflösende Kurven-Visualisierung

**Beschreibung**: Präzise 15-Minuten-Schritte statt 1-Stunden-Schritte im Chart.

**Status**: Nicht implementiert
**Aufwand**: 0.5 Tage

**Risiko**: Niedrig (Frontend-only)

---

## Empfohlene Reihenfolge

Basierend auf Priorität und Abhängigkeiten:

1. **R2** - Bug #8: Status-Desync (KRITISCH, User-facing)
2. **R3** - Bug #11: Datalog/History (Untersuchung nötig)
3. **R1** - Bug #2: Zeitschaltung/Override (Testen)
4. **R4** - Bug #7: Verlauf-Seite (Verifikation)
5. **R5** - Refactoring api.py (nach Stabilisierung)
6. **R6** - Bezier Editor Mobile UI (Nice-to-have)
7. **R7** - Device Dashboard (Future)
8. **R8** - Hochauflösende Kurven (Future)

---

## Offene Fragen

1. **R2/Bug #8**: Wurde v6.14.0 mit den Fixes für Bug #9 und #10 tatsächlich deployed? Der Status ist widersprüchlich (Bug #9/#10 = BEHOBEN, Bug #8 = TEILWEISE BEHOBEN)

2. **R3/Bug #11**: Was genau ist das Problem? Console-Logs allein sind nicht aussagekräftig. Werden Daten angezeigt oder nicht?

3. **R5/Refactoring**: Wann ist das System "stabil genug" für das Refactoring?

---

**Nächster Schritt**: MULTI_AGENT_PLAN.md erstellen und mit R2 beginnen.
