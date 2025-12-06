# GrowPi Roadmap - Geplante Features

**Letzte Aktualisierung**: 2025-12-06
**Aktuelle Version**: v6.8.0
**Status**: Active Development

---

## 🚀 Nächste Features (Priorisiert)

### Feature #0: PWM Zero-Downtime (KRITISCH)

**Ziel**: PWM-Werte bleiben bei Service-Restart stabil - kein LED-Flackern

**Priorität**: KRITISCH (beeinträchtigt Pflanzenwachstum)

**Aufwand**: 2 Stunden

#### Problem-Beschreibung

Beim Neustart des GrowPi-Services (`sudo systemctl restart grow-pi`) werden alle PWM-Kanäle kurzzeitig auf 0% zurückgesetzt. Dies verursacht:
- Sichtbares Flackern der LED-Beleuchtung
- Stress für lichtempfindliche Pflanzen
- Unterbrechung der Photoperiode

**Root Cause** (identifiziert in Code-Analyse):
```python
# pwm_controller.py:252
def cleanup(self):
    if self.pi and self.pi.connected:
        self.all_off()  # <-- DAS VERURSACHT FLACKERN
        self.pi.stop()

# main.py:319
def stop(self):
    self.pwm_controller.cleanup()  # <-- RUFT all_off() AUF
```

**Key Insight**: Das System nutzt bereits `pigpiod` (pigpio daemon), der PWM-Werte **unabhängig** vom Python-Prozess hält. Das Flackern entsteht nur, weil explizit `all_off()` aufgerufen wird.

#### Lösungs-Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    SERVICE LAYER                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────────┐     ┌─────────────────┐                │
│  │ pigpiod.service │     │ grow-pi.service │                │
│  │ (Hardware PWM)  │◄────│ (Main App)      │                │
│  │ PERSISTIERT PWM │     │                 │                │
│  └─────────────────┘     └────────┬────────┘                │
│          ▲                        │                          │
│          │                        ▼                          │
│          │                ┌───────────────┐                  │
│          └────────────────│ PWMController │                  │
│                           │ disconnect()  │ ← NEU!          │
│                           └───────┬───────┘                  │
│                                   ▼                          │
│                          ┌────────────────┐                  │
│                          │ State Files    │                  │
│                          │ /run/growpi/   │                  │
│                          └────────────────┘                  │
│                                                              │
└─────────────────────────────────────────────────────────────┘

NEUSTART-FLOW:
1. SIGTERM → save_state() → disconnect() (NICHT all_off!)
2. pigpiod hält PWM-Werte stabil
3. Neuer Prozess → load_state() → verify PWM → weiter
```

#### User-Entscheidung (2025-12-06)

**Frage**: Soll bei `systemctl stop` PWM erhalten bleiben?
**Antwort**: **JA** - PWM-Werte bleiben IMMER erhalten, auch bei stop.
Lampen werden nur über explizite API-Calls ausgeschaltet.

#### Technische Umsetzung

**Neue Datei: `grow_pi/utils/pwm_state.py`**
```python
"""
PWM State Persistence - Zero-Downtime Restarts

Speichert PWM-Zustand in /run/growpi/ für nahtlose Service-Neustarts.
"""

STATE_DIR = '/run/growpi'
STATE_FILE = f'{STATE_DIR}/pwm_state.json'

def save_state(pwm_controller, mode: str = 'auto') -> bool:
    """Speichert aktuellen PWM-Zustand mit File-Locking."""

def load_state() -> Optional[Dict]:
    """Lädt gespeicherten PWM-Zustand."""

def state_exists() -> bool:
    """Prüft ob gültiger State existiert."""
```

**State-File Format**:
```json
{
  "version": 1,
  "timestamp": "2025-12-06T14:30:00.123456",
  "mode": "auto",
  "channels": {
    "1": {"gpio": 16, "name": "Far Red", "intensity": 75, "source": "curve"},
    "2": {"gpio": 13, "name": "Warm White", "intensity": 50, "source": "curve"},
    "3": {"gpio": 12, "name": "Cool White", "intensity": 80, "source": "manual"},
    "4": {"gpio": 18, "name": "UV", "intensity": 0, "source": "curve"}
  }
}
```

**Änderung: `grow_pi/lamps/pwm_controller.py`**

1. Neue Methode `disconnect()`:
```python
def disconnect(self) -> None:
    """
    Trennt Verbindung zu pigpiod OHNE PWM-Werte zu ändern.
    Für Service-Restarts: PWM bleibt via pigpiod stabil.
    """
    if self.pi and self.pi.connected:
        self.pi.stop()  # Nur trennen - PWM läuft weiter!
        logger.info("Disconnected from pigpiod (PWM preserved)")
    self._initialized = False
```

2. `cleanup()` mit Parameter erweitern:
```python
def cleanup(self, turn_off_lamps: bool = True) -> None:
    """Cleanup GPIO resources."""
    if self.pi and self.pi.connected:
        if turn_off_lamps:
            self.all_off()
        self.pi.stop()
    self._initialized = False
```

**Änderung: `grow_pi/main.py`**

1. Signal-Handler:
```python
def signal_handler(sig, frame):
    logger.info(f"Signal {sig} received - saving state...")
    if controller:
        controller.stop()  # PWM wird immer erhalten
    sys.exit(0)
```

2. `stop()` Methode:
```python
def stop(self) -> None:
    """Stop the controller gracefully. PWM bleibt IMMER erhalten."""
    self.running = False
    if STATE_PERSISTENCE_AVAILABLE:
        save_state(self.pwm_controller, _get_current_mode())
    self.pwm_controller.disconnect()  # NICHT cleanup()!
    logger.info("GrowPi Controller stopped (PWM preserved).")
```

3. Startup State-Recovery (in `initialize()`):
```python
if STATE_PERSISTENCE_AVAILABLE and state_exists():
    logger.info("Warm restart detected - restoring PWM state...")
    saved_state = load_state()
    for ch_str, ch_data in saved_state.get('channels', {}).items():
        self.pwm_controller.set_intensity(int(ch_str), ch_data['intensity'])
```

**Änderung: `systemd/grow-pi.service`**
```ini
[Service]
# Runtime directory für State-Files
RuntimeDirectory=growpi
RuntimeDirectoryMode=0755

# Graceful shutdown (30s Zeit)
TimeoutStopSec=30
KillMode=mixed
KillSignal=SIGTERM
```

#### Betroffene Dateien

| Datei | Aktion | Aufwand |
|-------|--------|---------|
| `grow_pi/utils/pwm_state.py` | **NEU** | 30 Min |
| `grow_pi/lamps/pwm_controller.py` | ÄNDERN | 15 Min |
| `grow_pi/main.py` | ÄNDERN | 20 Min |
| `systemd/grow-pi.service` | ÄNDERN | 10 Min |

#### Test-Verfahren

```bash
# 1. Lampen auf bekannten Wert setzen
curl -X POST http://192.168.0.86:5000/api/lamp/1 \
  -H "Content-Type: application/json" \
  -d '{"intensity": 75}'

# 2. Service neustarten
ssh admin@192.168.0.86 'sudo systemctl restart grow-pi'

# 3. Wert prüfen (sollte noch 75 sein!)
curl http://192.168.0.86:5000/api/status | jq '.lamps[0].intensity'
# Erwartet: 75 (NICHT 0!)

# 4. State-File prüfen
ssh admin@192.168.0.86 'cat /run/growpi/pwm_state.json'

# 5. Cold Boot Test (optional)
ssh admin@192.168.0.86 'sudo reboot'
# Nach Reboot: Lampen sollten Kurven-Werte haben
```

#### Akzeptanzkriterien

- [ ] `systemctl restart grow-pi` verursacht KEIN Flackern
- [ ] `systemctl stop grow-pi` lässt Lampen an
- [ ] State-File wird in `/run/growpi/pwm_state.json` geschrieben
- [ ] Warm-Restart stellt PWM-Werte aus State-File wieder her
- [ ] Cold-Boot berechnet PWM-Werte aus Kurven (kein State-File nach Reboot)
- [ ] Logging zeigt "PWM preserved" bei Shutdown
- [ ] Logging zeigt "Warm restart detected" bei Restart

#### Risiko-Bewertung

| Risiko | Wahrscheinlichkeit | Mitigation |
|--------|-------------------|------------|
| pigpiod Neustart | Niedrig | Reconnect-Logic vorhanden |
| Korrupter State-File | Sehr niedrig | Fallback auf Kurven-Berechnung |
| Timing-Issue | Niedrig | State wird vor disconnect() gespeichert |

#### Rollback-Plan

Falls Probleme auftreten:
1. `cleanup()` Parameter auf default `True` setzen
2. `stop()` auf alte Version zurücksetzen
3. `pwm_state.py` Imports auskommentieren

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
| 2025-12-06 | Roadmap komplett umstrukturiert: Chronologisch, Nächstes zuerst | Dennis + Claude |
| 2025-12-06 | Feature 2B.1 (Zeitbasierte Schaltung) hinzugefügt | Dennis + Claude |
| 2025-12-06 | Feature 3.1 (Version Display) + 3.2 (Collapsible) hinzugefügt | Dennis + Claude |
| 2025-12-06 | Roadmap überarbeitet - Phase 1+2 als erledigt markiert | Dennis + Claude |
| 2025-12-05 | Initial Draft - Phase 1 & 2 definiert | Dennis + Claude |

---

**Geschätzte Gesamtdauer (Features #1-#6)**: 6-10 Arbeitstage
