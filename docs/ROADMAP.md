# GrowPi Roadmap - Geplante Features

**Letzte Aktualisierung**: 2025-12-07
**Aktuelle Version**: v6.9.1
**Status**: Active Development - Bug Fixing Phase

---

## 🔴 KRITISCHE BUGS (Priorität 1)

Diese Bugs müssen VOR neuen Features behoben werden!

### Bug #1: Room/Entfeuchter-Steuerung funktioniert nicht

**Status**: 🔴 OFFEN
**Entdeckt**: 2025-12-07
**Symptome**:
- Steckdose reagiert nicht auf Steuerung (An/Aus)
- Automatik springt nicht an trotz Wertänderungen
- Fehler in Logs: `no such table: device_automation_config`

**Vermutete Ursache**:
- DB-Migration für `device_automation_config` fehlt oder wurde nicht ausgeführt
- Möglicherweise Smart-Plug-Integration unvollständig

**Zu prüfen**:
- [ ] DB-Tabelle `device_automation_config` existiert?
- [ ] Migration-File vorhanden und ausgeführt?
- [ ] Tuya Smart-Plug Verbindung funktioniert?
- [ ] DehumidifierController initialisiert korrekt?

---

### Bug #2: Zeitschaltung/Override funktioniert nicht

**Status**: 🔴 OFFEN
**Entdeckt**: 2025-12-07
**Symptome**:
- Zeitfenster-basierte Schaltung reagiert nicht
- Override-Funktion im UI ohne Wirkung

**Vermutete Ursache**:
- Abhängig von Bug #1 (device_automation_config fehlt)
- Scheduler-Logik greift nicht

**Zu prüfen**:
- [ ] DB-Tabelle `device_time_schedules` existiert?
- [ ] API `/api/room/schedules` liefert Daten?
- [ ] Scheduler-Loop läuft im Background?

---

### Bug #3: Kosten-Tracking API prüfen

**Status**: 🟡 ZU PRÜFEN
**Entdeckt**: 2025-12-07
**Symptome**:
- API-Verbindung möglicherweise fehlerhaft

**Zu prüfen**:
- [ ] Endpoint `/api/costs` erreichbar?
- [ ] DB-Tabelle für Kosten existiert?
- [ ] Logging funktioniert?

---

## 🚀 Nächste Features (Priorisiert)

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
