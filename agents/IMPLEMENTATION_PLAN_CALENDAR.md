# IMPLEMENTATION_PLAN.md - Grow-Kalender Feature

## Executive Summary

**Feature:** Grow-Kalender mit Daily Logs für Hobbygärtner
**Target Stack:** Pi-Controller (Python Flask Backend + Vanilla JavaScript Frontend)
**Aufwand:** 25-30 Stunden (realistisch)
**Komplexität:** Mittel-Hoch

**Stack-Entscheidung: Pi-Controller ✅**
- ✅ Aktives Frontend (index.html mit 565 Zeilen)
- ✅ Blueprint-Pattern etabliert (8 Blueprints)
- ✅ SQLite-Datenbank mit Migrations-System
- ✅ Vanilla JS Module-System (ES6 imports)

---

## Dateien zu erstellen/ändern

### Backend (Builder-Agent 1)
1. `pi-controller/grow_pi/database/migrations/20251212_grow_calendar.sql` - NEU
2. `pi-controller/grow_pi/web/blueprints/calendar_bp.py` - NEU
3. `pi-controller/grow_pi/web/app.py` - Blueprint registrieren

### Frontend (Builder-Agent 2)
4. `pi-controller/grow_pi/web/static/js/modules/calendar.js` - NEU
5. `pi-controller/grow_pi/web/static/css/calendar.css` - NEU
6. `pi-controller/grow_pi/web/static/js/api.js` - Erweitern
7. `pi-controller/grow_pi/web/static/index.html` - Tab + Modal + Hamburger
8. `pi-controller/grow_pi/web/static/css/main.css` - Mobile Nav
9. `pi-controller/grow_pi/web/static/js/utils.js` - setupMobileNav()

---

## Datenbank-Schema (SQLite)

```sql
-- TABLE: grows
CREATE TABLE IF NOT EXISTS grows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    strain TEXT,
    start_date DATE NOT NULL,
    current_phase TEXT NOT NULL DEFAULT 'seedling',
    phase_started_at DATE NOT NULL,
    notes TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- TABLE: phase_events
CREATE TABLE IF NOT EXISTS phase_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grow_id INTEGER NOT NULL,
    phase TEXT NOT NULL,
    started_at DATE NOT NULL,
    ended_at DATE,
    duration_days INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (grow_id) REFERENCES grows(id) ON DELETE CASCADE
);

-- TABLE: daily_logs
CREATE TABLE IF NOT EXISTS daily_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    grow_id INTEGER NOT NULL,
    log_date DATE NOT NULL,
    watered BOOLEAN DEFAULT 0,
    fertilized BOOLEAN DEFAULT 0,
    water_amount_ml INTEGER,
    fertilizer_type TEXT,
    fertilizer_amount_ml INTEGER,
    notes TEXT,
    plant_height_cm REAL,
    photos TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (grow_id) REFERENCES grows(id) ON DELETE CASCADE,
    UNIQUE(grow_id, log_date)
);
```

---

## API Endpoints

| Method | Endpoint | Beschreibung |
|--------|----------|--------------|
| GET | `/api/calendar/grows` | Liste aller Grows |
| POST | `/api/calendar/grows` | Neuen Grow erstellen |
| GET | `/api/calendar/grows/<id>` | Grow-Details |
| PUT | `/api/calendar/grows/<id>` | Grow aktualisieren |
| DELETE | `/api/calendar/grows/<id>` | Grow archivieren |
| POST | `/api/calendar/grows/<id>/phase` | Phase wechseln |
| GET | `/api/calendar/grows/<id>/timeline` | Phasen-Historie |
| GET | `/api/calendar/grows/<id>/logs` | Logs eines Grows |
| POST | `/api/calendar/logs` | Log erstellen/update |
| GET | `/api/calendar/logs/<id>` | Einzelner Log |
| PUT | `/api/calendar/logs/<id>` | Log aktualisieren |
| DELETE | `/api/calendar/logs/<id>` | Log löschen |
| GET | `/api/calendar/month/<YYYY-MM>` | Kalenderansicht |

---

## Implementierungs-Reihenfolge

### Phase 1: Backend (Builder-Agent 1) - 8h
1. Migration erstellen (1h)
2. Calendar Blueprint (6h)
3. Blueprint registrieren (15min)

### Phase 2: Frontend (Builder-Agent 2) - 12h
4. Calendar Module (8h)
5. Calendar Styles (2h)
6. API Client erweitern (1h)

### Phase 3: Integration (Builder-Agent 2) - 5h
7. Tab Integration (2h)
8. Mobile Navigation / Hamburger (3h)

### Phase 4: Validation (Validator-Agent) - 3h
9. Backend-Tests
10. Frontend-Tests
11. Integration-Tests

---

## Validierungs-Checkliste

### Backend
- [ ] Migration ausgeführt (3 Tabellen)
- [ ] Alle 13 Endpoints erreichbar
- [ ] CRUD-Operationen funktional
- [ ] Error-Handling (400/404/500)

### Frontend
- [ ] Tab "Kalender" sichtbar
- [ ] Grows-Liste zeigt Daten
- [ ] Kalender-Grid rendert
- [ ] Daily-Log-Modal funktioniert
- [ ] Responsive Design
- [ ] Hamburger-Menu funktional

### Integration
- [ ] API-Calls erfolgreich
- [ ] Daten persistent
- [ ] Keine Console-Errors

---

**Erstellt:** 2025-12-12
**Status:** READY FOR IMPLEMENTATION
