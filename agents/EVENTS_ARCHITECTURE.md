# EVENTS_ARCHITECTURE.md - Grow-Phasen Events Integration

## Zusammenfassung

Vollständiger Architektur-Plan für die Integration vordefinierter Grow-Events basierend auf `/docs/grow_phasen.md`.

---

## 1. Datenbank-Schema

### Neue Tabelle: `phase_milestones`

```sql
CREATE TABLE IF NOT EXISTS phase_milestones (
    id TEXT PRIMARY KEY,
    phase TEXT NOT NULL,                     -- seedling, vegetative, flowering, drying, curing

    -- Zeitfenster-System
    day_offset_min INTEGER NOT NULL,         -- z.B. 28
    day_offset_max INTEGER,                  -- z.B. 35 (NULL = exakt)

    -- Content
    title TEXT NOT NULL,
    title_en TEXT,
    description TEXT,
    icon TEXT,                               -- Emoji
    category TEXT,                           -- training, environment, nutrients, observation, harvest

    -- Umgebungsparameter (JSON)
    env_params TEXT,                         -- {"temp":{"min":20,"max":28}, "rh":{"min":50,"max":60}}

    -- System vs. User
    is_system BOOLEAN DEFAULT 0,
    is_enabled BOOLEAN DEFAULT 1,

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_milestones_phase ON phase_milestones(phase);
CREATE INDEX idx_milestones_category ON phase_milestones(category);
```

---

## 2. System-Events (50+)

### Seedling Phase (Tag 1-21)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-seed-001 | 1-3 | Keimung | 🌱 | observation |
| ms-seed-002 | 3-5 | Keimblätter öffnen | 🌿 | observation |
| ms-seed-003 | 5-7 | Erste echte Blätter | 🍃 | observation |
| ms-seed-004 | 7-10 | Dome entfernen | 💨 | environment |
| ms-seed-005 | 10-14 | Umtopf-Fenster | 🪴 | training |
| ms-seed-006 | 14-21 | Übergang zu Veg | ➡️ | observation |

### Vegetative Phase (Tag 1-60+)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-veg-001 | 1-7 | LST beginnen | 🔗 | training |
| ms-veg-002 | 7-14 | Erstes Topping | ✂️ | training |
| ms-veg-003 | 14-21 | SCROG Installation | 🕸️ | training |
| ms-veg-004 | 14-28 | Super Cropping Fenster | 💪 | training |
| ms-veg-005 | 21-28 | Zweites Topping | ✂️ | training |
| ms-veg-006 | 1-7 | Nährstoffe einführen (25-50%) | 🧪 | nutrients |
| ms-veg-007 | 21-35 | Finales Umtopfen | 🪴 | training |

### Pre-Flower (Tag -7 bis -1)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-pre-001 | -7 bis -3 | Heavy Defoliation | 🍂 | training |
| ms-pre-002 | -7 bis -3 | Lollipopping | 🍭 | training |
| ms-pre-003 | -3 | Finaler Training-Check | ✅ | observation |
| ms-pre-004 | -1 | Pre-Flip Vorbereitung | 💡 | environment |

### Flowering Phase (Tag 1-56+)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-flow-001 | 1 | Flip zu 12/12 | 💡 | environment |
| ms-flow-002 | 1 | Optional: Erste Schwazze | 🍂 | training |
| ms-flow-003 | 1-7 | Vegi-Nährstoffe beibehalten | 🧪 | nutrients |
| ms-flow-004 | 8-14 | Peak Stretch | 📏 | observation |
| ms-flow-005 | 8-14 | Geschlecht identifizieren | ♂️♀️ | observation |
| ms-flow-006 | 15-19 | Bloom-Nährstoffe 100% | 🧪 | nutrients |
| ms-flow-007 | 20-21 | Zweite Schwazze | 🍂 | training |
| ms-flow-008 | 21 | SCROG Tucking stoppen | 🕸️ | training |
| ms-flow-009 | 22-28 | Bud Formation | 🌺 | observation |
| ms-flow-010 | 29-35 | Bud Fattening (Peak P-K) | 💪 | nutrients |
| ms-flow-011 | 36-42 | Stützpfähle prüfen | 🔧 | observation |
| ms-flow-012 | 43-49 | Trichome-Monitoring starten | 🔬 | observation |
| ms-flow-013 | 43-49 | Flush beginnen (Soil) | 💧 | nutrients |
| ms-flow-014 | 50-56 | Ernte-Fenster | ✂️ | harvest |

### Drying Phase (Tag 1-14)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-dry-001 | 1 | Schneiden & Aufhängen | ✂️ | harvest |
| ms-dry-002 | 7-14 | Stem Snap Test | 🔍 | observation |

### Curing Phase (Tag 1-60+)
| ID | Tag | Titel | Icon | Kategorie |
|----|-----|-------|------|-----------|
| ms-cure-001 | 1-3 | Kritisch: 2-3x täglich lüften | 👁️ | environment |
| ms-cure-002 | 4-7 | 1-2x täglich lüften | 💨 | environment |
| ms-cure-003 | 8-14 | 1x täglich lüften | 💨 | environment |
| ms-cure-004 | 15-21 | Jeden 2. Tag lüften | 💨 | environment |
| ms-cure-005 | 28+ | Boveda hinzufügen (optional) | 💧 | environment |
| ms-cure-006 | 42-56 | Optimale Qualität erreicht | ⭐ | observation |

---

## 3. API-Endpoints

```
GET    /api/calendar/milestones                    # Alle Milestones
GET    /api/calendar/milestones?phase=flowering    # Filter nach Phase
GET    /api/calendar/milestones/for-date           # Events für Grow + Datum
POST   /api/calendar/milestones                    # Custom Event erstellen
PUT    /api/calendar/milestones/:id                # Event bearbeiten
PATCH  /api/calendar/milestones/:id/toggle         # Enable/Disable
DELETE /api/calendar/milestones/:id                # Custom löschen
```

---

## 4. Frontend-Integration

### Kalender-Ansicht
- Event-Badges an relevanten Tagen
- Kategorie-Farbcodierung:
  - Training: Blau
  - Environment: Grün
  - Nutrients: Orange
  - Observation: Lila
  - Harvest: Rot

### Daily-Log-Modal
- Event-Sektion oberhalb des Log-Formulars
- Zeigt alle Events für den Tag

---

## 5. Implementierungs-Reihenfolge

1. Migration-Script mit Seed-Events
2. Backend API-Endpoints
3. Frontend Kalender-Integration
4. Frontend Event-Details in Modal
5. Testing

---

**Erstellt:** 2025-12-13
**Status:** APPROVED FOR IMPLEMENTATION
