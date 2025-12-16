-- Migration: Grow Calendar Feature (Grow-Zyklen Tracking)
-- Version: v6.20.0
-- Date: 2025-12-12
-- Feature: Grow-Kalender mit Phasen-Tracking und täglichen Logs

-- ============================================================================
-- TABLE: grows - Grow-Zyklen
-- ============================================================================
CREATE TABLE IF NOT EXISTS grows (
    id TEXT PRIMARY KEY,                     -- UUID
    name TEXT NOT NULL,                      -- z.B. "Northern Lights #1"
    strain TEXT,                             -- Sorte (optional)
    start_date TEXT NOT NULL,                -- ISO 8601 Date
    current_phase TEXT NOT NULL DEFAULT 'seedling',  -- seedling, vegetative, flowering, drying, curing
    phase_started_at TEXT NOT NULL,          -- ISO 8601 Datetime
    notes TEXT,                              -- Freitext-Notizen
    is_active BOOLEAN DEFAULT 1,             -- Aktiver Grow (nur 1 gleichzeitig)
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_grows_active ON grows(is_active);
CREATE INDEX IF NOT EXISTS idx_grows_start_date ON grows(start_date DESC);

-- ============================================================================
-- TABLE: phase_events - Phasen-Übergänge
-- ============================================================================
CREATE TABLE IF NOT EXISTS phase_events (
    id TEXT PRIMARY KEY,                     -- UUID
    grow_id TEXT NOT NULL,
    phase TEXT NOT NULL,                     -- seedling, vegetative, flowering, drying, curing
    started_at TEXT NOT NULL,                -- ISO 8601 Datetime
    ended_at TEXT,                           -- NULL = noch aktiv
    duration_days INTEGER,                   -- Berechnet bei Phase-Ende
    notes TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (grow_id) REFERENCES grows(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_phase_events_grow ON phase_events(grow_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_phase_events_phase ON phase_events(phase);

-- ============================================================================
-- TABLE: daily_logs - Tägliche Pflegeeinträge
-- ============================================================================
CREATE TABLE IF NOT EXISTS daily_logs (
    id TEXT PRIMARY KEY,                     -- UUID
    grow_id TEXT NOT NULL,
    log_date TEXT NOT NULL,                  -- YYYY-MM-DD
    watered BOOLEAN DEFAULT 0,
    fertilized BOOLEAN DEFAULT 0,
    water_amount_ml INTEGER,                 -- Optional: Wassermenge
    fertilizer_type TEXT,                    -- z.B. "BioBizz Grow"
    fertilizer_amount_ml INTEGER,
    notes TEXT,                              -- Tagesnotizen
    plant_height_cm REAL,                    -- Optional: Pflanzenhöhe
    photos TEXT,                             -- JSON Array mit Foto-URLs
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (grow_id) REFERENCES grows(id) ON DELETE CASCADE,
    UNIQUE(grow_id, log_date)                -- Nur 1 Log pro Tag pro Grow
);

CREATE INDEX IF NOT EXISTS idx_daily_logs_grow_date ON daily_logs(grow_id, log_date DESC);
CREATE INDEX IF NOT EXISTS idx_daily_logs_date ON daily_logs(log_date DESC);

-- ============================================================================
-- DEMO DATA: Seed Test-Daten für Development
-- ============================================================================

-- Demo Grow (aktiv)
INSERT OR IGNORE INTO grows (id, name, strain, start_date, current_phase, phase_started_at, is_active, notes)
VALUES (
    'demo-grow-001',
    'Demo Grow #1',
    'Haze Test Strain',
    date('now', '-45 days'),
    'vegetative',
    datetime('now', '-20 days'),
    1,
    'Demo-Grow für Testing der Calendar-Feature'
);

-- Phase Events für Demo Grow
INSERT OR IGNORE INTO phase_events (id, grow_id, phase, started_at, ended_at, duration_days, notes)
VALUES
    ('demo-phase-001', 'demo-grow-001', 'seedling', datetime('now', '-45 days'), datetime('now', '-20 days'), 25, 'Keimphase abgeschlossen'),
    ('demo-phase-002', 'demo-grow-001', 'vegetative', datetime('now', '-20 days'), NULL, NULL, 'Aktuell in Vegi-Phase');

-- Daily Logs für Demo Grow (letzte 7 Tage)
INSERT OR IGNORE INTO daily_logs (id, grow_id, log_date, watered, water_amount_ml, notes, plant_height_cm)
VALUES
    ('demo-log-001', 'demo-grow-001', date('now', '-6 days'), 1, 500, 'Erste Woche Vegi', 15.5),
    ('demo-log-002', 'demo-grow-001', date('now', '-5 days'), 0, NULL, 'Kein Wasser', 16.0),
    ('demo-log-003', 'demo-grow-001', date('now', '-4 days'), 1, 500, 'Normal gegossen', 17.2),
    ('demo-log-004', 'demo-grow-001', date('now', '-3 days'), 1, 500, 'Mit Bio-Grow gedüngt', 18.5),
    ('demo-log-005', 'demo-grow-001', date('now', '-2 days'), 0, NULL, 'Pause', 19.0),
    ('demo-log-006', 'demo-grow-001', date('now', '-1 days'), 1, 600, 'Etwas mehr Wasser', 20.3),
    ('demo-log-007', 'demo-grow-001', date('now'), 1, 500, 'Normales Gießen', 21.0);

-- Abgeschlossener Grow für History
INSERT OR IGNORE INTO grows (id, name, strain, start_date, current_phase, phase_started_at, is_active, notes)
VALUES (
    'demo-grow-002',
    'Demo Grow #2 (Abgeschlossen)',
    'Test Strain Alpha',
    date('now', '-120 days'),
    'curing',
    datetime('now', '-10 days'),
    0,
    'Abgeschlossener Demo-Grow'
);

INSERT OR IGNORE INTO phase_events (id, grow_id, phase, started_at, ended_at, duration_days)
VALUES
    ('demo-phase-003', 'demo-grow-002', 'seedling', datetime('now', '-120 days'), datetime('now', '-100 days'), 20),
    ('demo-phase-004', 'demo-grow-002', 'vegetative', datetime('now', '-100 days'), datetime('now', '-50 days'), 50),
    ('demo-phase-005', 'demo-grow-002', 'flowering', datetime('now', '-50 days'), datetime('now', '-20 days'), 30),
    ('demo-phase-006', 'demo-grow-002', 'drying', datetime('now', '-20 days'), datetime('now', '-10 days'), 10),
    ('demo-phase-007', 'demo-grow-002', 'curing', datetime('now', '-10 days'), NULL, NULL);
