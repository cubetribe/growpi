# Feature-Spezifikation: Grow-Kalender & Daily Log

**Version:** 1.0  
**Erstellt:** 2025-12-12  
**Status:** Geplant  
**Priorität:** Hoch  
**Geschätzter Aufwand:** 10-12 Stunden (MVP)

---

## 1. Übersicht

### Ziel
Ein Kalender-Tab für ambitionierte Hobbygärtner, der:
- **Phasen-Tracking** ermöglicht (Seedling → Veggie → Bloom)
- **Vordefinierte Events** relativ zum Phasen-Start anzeigt
- **Daily Logs** für Dokumentation von Düngung, Bewässerung und Beobachtungen bietet
- **Notizen** pro Tag speichert

### Zielgruppe
Hobbygärtner, die ihren Grow-Zyklus dokumentieren und später auswerten möchten.

### Zukunftsvision
Die gesammelten Daten sollen später für einen KI-Chatbot verfügbar sein, der basierend auf dem aktuellen Tag und der Phase personalisierte Empfehlungen geben kann.

---

## 2. Funktionale Anforderungen

### 2.1 Phasen-Management

**Drei Phasen:**

| Phase | Key | Englisch | Typische Dauer |
|-------|-----|----------|----------------|
| Keimphase | `seedling` | Seedling | 7-14 Tage |
| Vegetative Phase | `veggie` | Veggie | 14-60 Tage |
| Blütephase | `bloom` | Bloom | 50-70 Tage |

**User-Aktionen:**
- Neuen Grow starten (Name vergeben)
- Phase manuell setzen ("Heute beginnt Bloom")
- Grow beenden/archivieren

**Automatische Berechnung:**
- Aktueller Tag innerhalb der Phase (z.B. "Bloom Tag 21")
- Anstehende Events basierend auf Phasen-Offset

---

### 2.2 Event-Templates (Vordefinierte Ereignisse)

Events werden relativ zum Phasen-Start definiert. Negative Werte = vor Phasen-Start.

**Beispiel-Events (Bloom):**

| Tag | Event | Beschreibung |
|-----|-------|--------------|
| -5 | Defoliation | Laub entfernen vor Blüte-Start |
| 1 | Blüte-Start | Lichtzyklus auf 12/12 umstellen |
| 14 | Stretch-Ende prüfen | Pflanzen strecken sich nicht mehr |
| 21 | Erste Blüten sichtbar | Kontrolle der Blütenentwicklung |
| 42 | Spülen beginnen | Bei 8-Wochen-Sorten |
| 56-70 | Ernte-Fenster | Je nach Sorte |

**User kann:**
- Eigene Events hinzufügen
- System-Events nicht löschen (nur ausblenden)
- Events für alle Phasen definieren

---

### 2.3 Daily Log (Tägliche Dokumentation)

**Erfasste Daten pro Tag:**

| Feld | Typ | Pflicht | Bedingung |
|------|-----|---------|-----------|
| Gedüngt | Boolean | Nein | - |
| EC-Wert | Float (0.0-5.0) | Nein | Nur wenn gedüngt=true |
| pH-Wert | Float (4.0-8.0) | Nein | Nur wenn gedüngt=true |
| Bewässert | Boolean | Nein | - |
| Wassermenge | Integer (ml) | Nein | Nur wenn bewässert=true |
| Beobachtungen | Multi-Select | Nein | - |
| Notizen | Text (max 2000) | Nein | - |

**Beobachtungen (Vorauswahl):**

```javascript
const OBSERVATIONS = [
  { key: 'burnt_tips', label: 'Verbrannte Spitzen', label_en: 'Burnt Tips', icon: '🔥' },
  { key: 'yellowing', label: 'Gelbe Blätter', label_en: 'Yellowing', icon: '💛' },
  { key: 'drooping', label: 'Hängende Blätter', label_en: 'Drooping', icon: '🥀' },
  { key: 'curling', label: 'Eingerollte Blätter', label_en: 'Curling', icon: '🌀' },
  { key: 'spots', label: 'Flecken auf Blättern', label_en: 'Spots', icon: '🔵' },
  { key: 'pests', label: 'Schädlinge', label_en: 'Pests', icon: '🐛' },
  { key: 'mold', label: 'Schimmel', label_en: 'Mold', icon: '🦠' },
  { key: 'slow_growth', label: 'Langsames Wachstum', label_en: 'Slow Growth', icon: '🐌' },
  { key: 'healthy', label: 'Alles gut', label_en: 'Healthy', icon: '✅' },
];
```

---

### 2.4 Kalender-Ansicht

**Monatsübersicht:**
- Standard-Kalender-Grid (Mo-So)
- Navigation: Monat vor/zurück
- Farbcodierung nach Phase:
  - Seedling: Grün (`#4ade80`)
  - Veggie: Blau (`#60a5fa`)
  - Bloom: Lila (`#c084fc`)

**Tages-Indikatoren (Icons):**
- 💧 = Bewässert
- 🧪 = Gedüngt
- ⚠️ = Beobachtung (Problem)
- ✅ = Alles gut
- 📅 = Event an diesem Tag

**Klick auf Tag:** Öffnet Daily-Log-Modal

---

## 3. Datenmodell (SQLite)

### 3.1 Tabelle: `grows`

```sql
CREATE TABLE grows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,                    -- "Winter Grow 2025"
    strain TEXT,                           -- Sortenname (optional)
    started_at DATETIME NOT NULL,          -- Grow-Startdatum
    current_phase TEXT DEFAULT 'seedling', -- seedling/veggie/bloom
    phase_started_at DATETIME,             -- Wann aktuelle Phase begann
    ended_at DATETIME,                     -- NULL wenn aktiv
    is_active BOOLEAN DEFAULT 1,
    notes TEXT,                            -- Allgemeine Grow-Notizen
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_grows_active ON grows(is_active);
```

### 3.2 Tabelle: `phase_events`

```sql
CREATE TABLE phase_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phase TEXT NOT NULL,                   -- seedling/veggie/bloom
    day_offset INTEGER NOT NULL,           -- -5, 1, 21, 60 (relativ zu Phase-Start)
    title TEXT NOT NULL,                   -- "Defoliation"
    title_en TEXT,                         -- "Defoliation" (English)
    description TEXT,                      -- Ausführliche Beschreibung
    is_system BOOLEAN DEFAULT 0,           -- System-Presets nicht löschbar
    is_enabled BOOLEAN DEFAULT 1,          -- Kann ausgeblendet werden
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_phase_events_phase ON phase_events(phase, day_offset);
```

### 3.3 Tabelle: `daily_logs`

```sql
CREATE TABLE daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grow_id INTEGER NOT NULL,
    date DATE NOT NULL,                    -- 2025-01-03
    
    -- Düngung
    fertilized BOOLEAN DEFAULT 0,
    ec_value REAL,                         -- 0.0 - 5.0
    ph_value REAL,                         -- 4.0 - 8.0
    fertilizer_notes TEXT,                 -- Welcher Dünger, Mischung etc.
    
    -- Bewässerung
    watered BOOLEAN DEFAULT 0,
    water_amount INTEGER,                  -- in ml
    
    -- Beobachtungen
    observations TEXT,                     -- JSON Array: ["burnt_tips", "yellowing"]
    
    -- Freitext
    notes TEXT,                            -- Allgemeine Notizen
    
    -- Meta
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (grow_id) REFERENCES grows(id) ON DELETE CASCADE,
    UNIQUE(grow_id, date)                  -- Ein Log pro Tag pro Grow
);

CREATE INDEX idx_daily_logs_grow_date ON daily_logs(grow_id, date);
```

---

## 4. API-Endpoints

### 4.1 Grows

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/api/calendar/grows` | Alle Grows (aktive + archivierte) |
| GET | `/api/calendar/grows/active` | Nur aktiver Grow |
| POST | `/api/calendar/grows` | Neuen Grow anlegen |
| PUT | `/api/calendar/grows/:id` | Grow aktualisieren |
| PUT | `/api/calendar/grows/:id/phase` | Phase setzen |
| DELETE | `/api/calendar/grows/:id` | Grow löschen |

**POST `/api/calendar/grows` - Body:**
```json
{
  "name": "Winter Grow 2025",
  "strain": "Northern Lights",
  "started_at": "2025-01-01",
  "current_phase": "seedling"
}
```

**PUT `/api/calendar/grows/:id/phase` - Body:**
```json
{
  "phase": "bloom",
  "phase_started_at": "2025-01-15"
}
```

---

### 4.2 Events

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/api/calendar/events` | Alle Event-Templates |
| GET | `/api/calendar/events?phase=bloom` | Events für Phase |
| POST | `/api/calendar/events` | Custom Event anlegen |
| PUT | `/api/calendar/events/:id` | Event bearbeiten |
| DELETE | `/api/calendar/events/:id` | Event löschen (nur Custom) |

**GET `/api/calendar/events` - Response:**
```json
{
  "events": [
    {
      "id": 1,
      "phase": "bloom",
      "day_offset": -5,
      "title": "Defoliation",
      "description": "Laub entfernen vor Blüte-Start",
      "is_system": true,
      "is_enabled": true
    }
  ]
}
```

---

### 4.3 Daily Logs

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/api/calendar/logs?month=2025-01` | Logs für Monat |
| GET | `/api/calendar/logs/:date` | Log für bestimmten Tag |
| POST | `/api/calendar/logs` | Log erstellen/aktualisieren |
| DELETE | `/api/calendar/logs/:id` | Log löschen |

**GET `/api/calendar/logs?month=2025-01` - Response:**
```json
{
  "grow": {
    "id": 1,
    "name": "Winter Grow 2025",
    "current_phase": "bloom",
    "phase_started_at": "2025-01-15",
    "phase_day": 3
  },
  "logs": [
    {
      "id": 42,
      "date": "2025-01-17",
      "phase": "bloom",
      "phase_day": 3,
      "fertilized": true,
      "ec_value": 1.8,
      "ph_value": 6.2,
      "watered": true,
      "water_amount": 500,
      "observations": ["burnt_tips"],
      "notes": "Leichte Überdüngung vermutet"
    }
  ],
  "events": [
    {
      "date": "2025-01-10",
      "title": "Defoliation",
      "phase": "bloom",
      "day_offset": -5
    }
  ]
}
```

**POST `/api/calendar/logs` - Body:**
```json
{
  "grow_id": 1,
  "date": "2025-01-17",
  "fertilized": true,
  "ec_value": 1.8,
  "ph_value": 6.2,
  "watered": true,
  "water_amount": 500,
  "observations": ["burnt_tips"],
  "notes": "Leichte Überdüngung vermutet"
}
```

---

## 5. UI-Design

### 5.1 Kalender-Tab Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Kalender                              [+ Neuer Grow]       │
├─────────────────────────────────────────────────────────────┤
│  Aktueller Grow: Winter Grow 2025                           │
│  Phase: 🌸 Bloom - Tag 3                                    │
│  [Seedling] [Veggie] [Bloom ✓]     ← Phase-Buttons          │
├─────────────────────────────────────────────────────────────┤
│        ◄  Januar 2025  ►                                    │
│  ┌─────┬─────┬─────┬─────┬─────┬─────┬─────┐               │
│  │ Mo  │ Di  │ Mi  │ Do  │ Fr  │ Sa  │ So  │               │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤               │
│  │     │     │  1  │  2  │  3  │  4  │  5  │               │
│  │     │     │ 🌱  │ 🌱  │ 🌱  │ 🌱  │ 🌱  │ ← Seedling    │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤               │
│  │  6  │  7  │  8  │  9  │ 10  │ 11  │ 12  │               │
│  │ 🌱  │ 🌿  │ 🌿  │ 🌿  │ 📅  │ 🌿  │ 🌿  │ ← Event!     │
│  │     │💧🧪│ 💧 │     │ 💧 │💧⚠️│ 💧 │ ← Indikatoren  │
│  ├─────┼─────┼─────┼─────┼─────┼─────┼─────┤               │
│  │ 13  │ 14  │ 15  │ 16  │ 17  │ 18  │ 19  │               │
│  │ 🌿  │ 🌿  │ 🌸  │ 🌸  │ 🌸  │     │     │ ← Bloom Start│
│  │ 💧 │💧🧪│ 📅 │ 💧 │💧🧪⚠️│     │     │               │
│  └─────┴─────┴─────┴─────┴─────┴─────┴─────┘               │
│                                                             │
│  Legende: 🌱 Seedling  🌿 Veggie  🌸 Bloom                  │
│           💧 Bewässert  🧪 Gedüngt  ⚠️ Problem  📅 Event    │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Daily-Log-Modal

```
┌─────────────────────────────────────────────────────────────┐
│  17. Januar 2025                                     [X]    │
│  🌸 Bloom - Tag 3                                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Düngung ──────────────────────────────────────────────┐ │
│  │ [✓] Gedüngt                                            │ │
│  │                                                        │ │
│  │ EC-Wert:  [1.8    ]     pH-Wert:  [6.2    ]           │ │
│  │                                                        │ │
│  │ Dünger-Notizen:                                        │ │
│  │ ┌────────────────────────────────────────────────────┐ │ │
│  │ │ BioBizz Bloom + CalMag                             │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Bewässerung ──────────────────────────────────────────┐ │
│  │ [✓] Bewässert          Menge: [500   ] ml             │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Beobachtungen ────────────────────────────────────────┐ │
│  │ [✓] 🔥 Verbrannte Spitzen    [ ] 💛 Gelbe Blätter     │ │
│  │ [ ] 🥀 Hängende Blätter      [ ] 🌀 Eingerollte       │ │
│  │ [ ] 🔵 Flecken               [ ] 🐛 Schädlinge        │ │
│  │ [ ] 🦠 Schimmel              [ ] ✅ Alles gut         │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌─ Notizen ──────────────────────────────────────────────┐ │
│  │ ┌────────────────────────────────────────────────────┐ │ │
│  │ │ Leichte Überdüngung vermutet.                      │ │ │
│  │ │ EC beim nächsten Mal auf 1.5 reduzieren.           │ │ │
│  │ │                                                    │ │ │
│  │ └────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│                    [Speichern]    [Abbrechen]               │
└─────────────────────────────────────────────────────────────┘
```

---

## 6. Dateistruktur (Neue/Geänderte Dateien)

### Backend

```
pi-controller/grow_pi/
├── database/
│   └── migrations/
│       └── 007_calendar_tables.sql      # NEU: DB Schema
├── web/
│   └── blueprints/
│       └── calendar_bp.py               # NEU: API Blueprint
└── utils/
    └── calendar_manager.py              # NEU: Business Logic
```

### Frontend

```
pi-controller/grow_pi/web/static/
├── js/
│   └── modules/
│       └── calendar.js                  # NEU: Kalender-Modul (~400 LOC)
├── css/
│   └── calendar.css                     # NEU: Kalender-Styles (~200 LOC)
└── index.html                           # GEÄNDERT: Neuer Tab
```

---

## 7. System-Events (Vorinstalliert)

### Seedling Phase

| Tag | Event |
|-----|-------|
| 1 | Samen eingesetzt |
| 3-5 | Keimung erwartet |
| 7 | Erste echte Blätter |
| 10-14 | Bereit für Veggie-Phase |

### Veggie Phase

| Tag | Event |
|-----|-------|
| 1 | Vegetative Phase gestartet |
| 7 | Erste Düngung (leicht) |
| 14 | Umtopfen erwägen |
| 21 | LST/Training beginnen |
| 28 | Düngung erhöhen |

### Bloom Phase

| Tag | Event |
|-----|-------|
| -5 | Defoliation (Laub entfernen) |
| 1 | Blüte gestartet (12/12) |
| 7 | Stretch-Phase beginnt |
| 14 | Stretch-Ende, erste Blüten |
| 21 | Blüten werden größer |
| 28 | Trichome entwickeln sich |
| 42 | Spülen beginnen (Flush) |
| 49 | Trichome prüfen |
| 56-70 | Ernte-Fenster (sortenabhängig) |

---

## 8. Implementierungs-Phasen

### Phase 1: MVP (Priorität: HOCH)

**Scope:**
- [x] DB-Schema erstellen
- [x] API-Endpoints für Grows und Daily Logs
- [x] Kalender-Ansicht (Monats-Grid)
- [x] Daily-Log-Modal (Düngung + Notizen)
- [x] Manuelle Phase setzen

**Geschätzter Aufwand:** 10-12 Stunden

### Phase 2: Events & Polish

**Scope:**
- [ ] Vordefinierte Events anzeigen
- [ ] Custom Events erstellen
- [ ] Beobachtungen Multi-Select
- [ ] Grow-History (vergangene Zyklen anzeigen)
- [ ] Mobile-Optimierung

**Geschätzter Aufwand:** 6-8 Stunden

### Phase 3: Zukunft (Nach Chatbot-Integration)

**Scope:**
- [ ] KI-Chatbot kann auf Logs zugreifen
- [ ] Automatische Empfehlungen basierend auf Logs
- [ ] Auswertungen/Statistiken (EC-Verlauf, etc.)
- [ ] Export (CSV/PDF)
- [ ] Vergleich zwischen Grows

---

## 9. Akzeptanzkriterien (MVP)

- [ ] Neuer Tab "Kalender" im Web-Interface
- [ ] User kann neuen Grow anlegen (Name + Startdatum)
- [ ] User kann Phase manuell setzen (Seedling/Veggie/Bloom)
- [ ] Kalender zeigt aktuellen Monat mit Farbcodierung nach Phase
- [ ] Klick auf Tag öffnet Log-Modal
- [ ] User kann pro Tag erfassen: Gedüngt (EC/pH), Bewässert, Notizen
- [ ] Logs werden in SQLite gespeichert
- [ ] Logs werden beim erneuten Öffnen korrekt geladen
- [ ] Icons zeigen auf einen Blick: 💧🧪⚠️

---

## 10. Offene Fragen / Entscheidungen

1. **Mehrere Grows gleichzeitig?**
   - Aktuell: Nein, nur ein aktiver Grow
   - Später: Eventuell für Multi-Zelt-Setups

2. **Sprache?**
   - UI erstmal Deutsch
   - Labels in DB zweisprachig (für spätere i18n)

3. **Dünger-Presets?**
   - Später: Vorauswahl für bekannte Dünger (BioBizz, etc.)
   - MVP: Nur Freitext

4. **Fotos pro Tag?**
   - Später: Integration mit Timelapse?
   - MVP: Nur Text-Notizen

---

## Anhang: Technische Notizen für Claude Code

### Blueprint-Registrierung

In `api.py`:
```python
from grow_pi.web.blueprints.calendar_bp import calendar_bp
app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
```

### JavaScript-Modul laden

In `utils.js` bei Tab-Switch:
```javascript
case 'calendar':
    if (window.CalendarModule) {
        window.CalendarModule.init();
    }
    break;
```

### CSS-Variablen für Phasen-Farben

```css
:root {
    --phase-seedling: #4ade80;
    --phase-veggie: #60a5fa;
    --phase-bloom: #c084fc;
}
```

---

**Dokument-Ende**
