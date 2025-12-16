-- Migration: Phase Milestones (Grow-Phasen Events)
-- Version: v6.21.0
-- Date: 2025-12-13
-- Feature: Vordefinierte Events basierend auf grow_phasen.md

-- ============================================================================
-- TABLE: phase_milestones - System- und Custom-Events
-- ============================================================================
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
    is_system BOOLEAN DEFAULT 1,
    is_enabled BOOLEAN DEFAULT 1,

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_milestones_phase ON phase_milestones(phase);
CREATE INDEX IF NOT EXISTS idx_milestones_category ON phase_milestones(category);
CREATE INDEX IF NOT EXISTS idx_milestones_enabled ON phase_milestones(is_enabled);

-- ============================================================================
-- SYSTEM EVENTS: Seedling Phase (Tag 1-21)
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-seed-001', 'seedling', 1, 3, 'Keimung', 'Germination', 'Samen sollten aufbrechen und erste Wurzeln zeigen', '🌱', 'observation', '{"temp":{"min":20,"max":25},"rh":{"min":70,"max":80}}', 1),
    ('ms-seed-002', 'seedling', 3, 5, 'Keimblätter öffnen', 'Cotyledons Open', 'Erste runde Blätter entfalten sich', '🌿', 'observation', '{"temp":{"min":20,"max":25},"rh":{"min":70,"max":80}}', 1),
    ('ms-seed-003', 'seedling', 5, 7, 'Erste echte Blätter', 'First True Leaves', 'Die ersten gezackten Cannabisblätter erscheinen', '🍃', 'observation', '{"temp":{"min":20,"max":25},"rh":{"min":65,"max":75}}', 1),
    ('ms-seed-004', 'seedling', 7, 10, 'Dome entfernen', 'Remove Dome', 'Luftfeuchtigkeit langsam reduzieren durch schrittweises Lüften', '💨', 'environment', '{"temp":{"min":20,"max":25},"rh":{"min":60,"max":70}}', 1),
    ('ms-seed-005', 'seedling', 10, 14, 'Umtopf-Fenster', 'Transplant Window', 'Optional: Umtopfen in größeren Behälter (Solo Cup → 1L)', '🪴', 'training', '{"temp":{"min":20,"max":25},"rh":{"min":60,"max":70}}', 1),
    ('ms-seed-006', 'seedling', 14, 21, 'Übergang zu Veg', 'Transition to Veg', 'Pflanze zeigt stabiles Wachstum, bereit für vegetative Phase', '➡️', 'observation', '{"temp":{"min":20,"max":26},"rh":{"min":55,"max":65}}', 1);

-- ============================================================================
-- SYSTEM EVENTS: Vegetative Phase (Tag 1-60+)
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-veg-001', 'vegetative', 1, 7, 'LST beginnen', 'Start LST', 'Low Stress Training: Haupttrieb biegen für bessere Lichtverteilung', '🔗', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-002', 'vegetative', 7, 14, 'Erstes Topping', 'First Topping', 'Optional: Haupttrieb kappen ab 4-6 Nodien für buschiges Wachstum', '✂️', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-003', 'vegetative', 14, 21, 'SCROG Installation', 'Install SCROG Net', 'Screen of Green Netz 20-30cm über Pflanzen spannen', '🕸️', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-004', 'vegetative', 14, 28, 'Super Cropping Fenster', 'Super Cropping Window', 'Fortgeschritten: Stängel quetschen für stärkere Seitentriebe', '💪', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-005', 'vegetative', 21, 28, 'Zweites Topping', 'Second Topping', 'Optional: Weitere Haupttriebe kappen für Mainline/Manifold', '✂️', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-006', 'vegetative', 1, 7, 'Nährstoffe einführen', 'Introduce Nutrients', 'Starte mit 25-50% der empfohlenen Düngerdosis (Grow-Phase)', '🧪', 'nutrients', NULL, 1),
    ('ms-veg-007', 'vegetative', 21, 35, 'Finales Umtopfen', 'Final Transplant', 'Letzter Topfwechsel in endgültigen Container (10-20L)', '🪴', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-veg-008', 'vegetative', 28, 60, 'SCROG Weaving', 'SCROG Weaving', 'Täglich neue Triebe unter das Netz tucken für gleichmäßigen Canopy', '🕸️', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1);

-- ============================================================================
-- SYSTEM EVENTS: Pre-Flower (Relative zu Flowering Tag 1 = -7 bis -1)
-- Diese Events werden im Frontend speziell behandelt
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-pre-001', 'vegetative', -7, -3, 'Heavy Defoliation', 'Heavy Defoliation', 'Große Fächerblätter entfernen für bessere Luftzirkulation (VOR Flip)', '🍂', 'training', '{"temp":{"min":20,"max":28},"rh":{"min":50,"max":60}}', 1),
    ('ms-pre-002', 'vegetative', -7, -3, 'Lollipopping', 'Lollipopping', 'Untere Äste und kleine Triebe entfernen', '🍭', 'training', NULL, 1),
    ('ms-pre-003', 'vegetative', -3, -1, 'Finaler Training-Check', 'Final Training Check', 'Letzte LST/SCROG Anpassungen vor dem Flip', '✅', 'observation', NULL, 1),
    ('ms-pre-004', 'vegetative', -1, -1, 'Pre-Flip Vorbereitung', 'Pre-Flip Preparation', 'Wasser-pH prüfen, Nährstoffe vorbereiten, Licht-Timer checken', '💡', 'environment', NULL, 1);

-- ============================================================================
-- SYSTEM EVENTS: Flowering Phase (Tag 1-63)
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-flow-001', 'flowering', 1, 1, 'Flip zu 12/12', 'Flip to 12/12', 'Lichtzykles auf 12h Licht / 12h Dunkelheit umstellen', '💡', 'environment', '{"temp":{"min":20,"max":26},"rh":{"min":45,"max":55}}', 1),
    ('ms-flow-002', 'flowering', 1, 1, 'Erste Schwazze (Optional)', 'First Schwazze (Optional)', 'Aggressives Entlauben am Tag des Flips (fortgeschrittene Technik)', '🍂', 'training', NULL, 1),
    ('ms-flow-003', 'flowering', 1, 7, 'Vegi-Nährstoffe beibehalten', 'Keep Veg Nutrients', 'Während Stretch-Phase weiterhin Grow-Dünger verwenden', '🧪', 'nutrients', NULL, 1),
    ('ms-flow-004', 'flowering', 8, 14, 'Peak Stretch', 'Peak Stretch', 'Pflanze streckt sich stark (bis zu 200% der Veg-Höhe)', '📏', 'observation', '{"temp":{"min":20,"max":26},"rh":{"min":45,"max":55}}', 1),
    ('ms-flow-005', 'flowering', 8, 14, 'Geschlecht identifizieren', 'Identify Gender', 'Männliche Pflanzen zeigen Pollensäcke (sofort entfernen!)', '♂️♀️', 'observation', NULL, 1),
    ('ms-flow-006', 'flowering', 15, 19, 'Bloom-Nährstoffe 100%', 'Full Bloom Nutrients', 'Umstellen auf Blüte-Dünger (hoher P-K Anteil)', '🧪', 'nutrients', NULL, 1),
    ('ms-flow-007', 'flowering', 20, 21, 'Zweite Schwazze', 'Second Schwazze', 'Großes Entlauben Tag 20-21 für maximale Bud-Entwicklung', '🍂', 'training', NULL, 1),
    ('ms-flow-008', 'flowering', 21, 21, 'SCROG Tucking stoppen', 'Stop SCROG Tucking', 'Kein weiteres Biegen - Pflanze in vertikale Blütephase lassen', '🕸️', 'training', NULL, 1),
    ('ms-flow-009', 'flowering', 22, 28, 'Bud Formation', 'Bud Formation', 'Blütenkelche werden sichtbar, erste Pistils erscheinen', '🌺', 'observation', '{"temp":{"min":20,"max":26},"rh":{"min":40,"max":50}}', 1),
    ('ms-flow-010', 'flowering', 29, 35, 'Bud Fattening', 'Bud Fattening', 'Blüten werden dicht und schwer - Peak P-K Booster Zeit', '💪', 'nutrients', '{"temp":{"min":18,"max":24},"rh":{"min":40,"max":50}}', 1),
    ('ms-flow-011', 'flowering', 36, 42, 'Stützpfähle prüfen', 'Check Support Stakes', 'Schwere Colas brauchen Unterstützung gegen Abbrechen', '🔧', 'observation', NULL, 1),
    ('ms-flow-012', 'flowering', 43, 49, 'Trichome-Monitoring starten', 'Start Trichome Monitoring', 'Täglich mit Lupe checken: klar → milchig → bernstein', '🔬', 'observation', '{"temp":{"min":18,"max":24},"rh":{"min":35,"max":45}}', 1),
    ('ms-flow-013', 'flowering', 50, 56, 'Flush beginnen (Soil)', 'Start Flush (Soil)', 'Nur noch pH-neutrales Wasser für sauberen Geschmack', '💧', 'nutrients', NULL, 1),
    ('ms-flow-014', 'flowering', 56, 63, 'Ernte-Fenster', 'Harvest Window', 'Optimal bei 10-20% bernsteinfarbenen Trichomen', '✂️', 'harvest', NULL, 1);

-- ============================================================================
-- SYSTEM EVENTS: Drying Phase (Tag 1-14)
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-dry-001', 'drying', 1, 1, 'Schneiden & Aufhängen', 'Cut & Hang', 'Pflanze ernten und kopfüber in dunklem Raum aufhängen', '✂️', 'harvest', '{"temp":{"min":18,"max":21},"rh":{"min":55,"max":62}}', 1),
    ('ms-dry-002', 'drying', 7, 14, 'Stem Snap Test', 'Stem Snap Test', 'Kleine Äste sollten knacken (nicht biegen) = bereit für Curing', '🔍', 'observation', '{"temp":{"min":18,"max":21},"rh":{"min":55,"max":62}}', 1);

-- ============================================================================
-- SYSTEM EVENTS: Curing Phase (Tag 1-60+)
-- ============================================================================
INSERT INTO phase_milestones (id, phase, day_offset_min, day_offset_max, title, title_en, description, icon, category, env_params, is_system)
VALUES
    ('ms-cure-001', 'curing', 1, 3, 'Kritisch: 2-3x täglich lüften', 'Critical: Burp 2-3x Daily', 'Gläser öffnen für 15-30min zur Feuchtigkeitsabgabe', '👁️', 'environment', '{"temp":{"min":18,"max":21},"rh":{"min":58,"max":62}}', 1),
    ('ms-cure-002', 'curing', 4, 7, '1-2x täglich lüften', 'Burp 1-2x Daily', 'Weiterhin täglich Gläser öffnen, RH sollte stabil bei 62% sein', '💨', 'environment', '{"temp":{"min":18,"max":21},"rh":{"min":58,"max":62}}', 1),
    ('ms-cure-003', 'curing', 8, 14, '1x täglich lüften', 'Burp Daily', 'Einmal täglich kurz lüften', '💨', 'environment', '{"temp":{"min":18,"max":21},"rh":{"min":58,"max":62}}', 1),
    ('ms-cure-004', 'curing', 15, 21, 'Jeden 2. Tag lüften', 'Burp Every Other Day', 'Lüft-Intervalle verlängern', '💨', 'environment', '{"temp":{"min":18,"max":21},"rh":{"min":58,"max":62}}', 1),
    ('ms-cure-005', 'curing', 28, NULL, 'Boveda hinzufügen (optional)', 'Add Boveda (Optional)', '62% Humidity Packs für langfristige Lagerung', '💧', 'environment', NULL, 1),
    ('ms-cure-006', 'curing', 42, 56, 'Optimale Qualität erreicht', 'Peak Quality Reached', 'Geschmack und Potenz sind voll entwickelt', '⭐', 'observation', NULL, 1);

-- ============================================================================
-- INDEXES für Performance
-- ============================================================================
CREATE INDEX IF NOT EXISTS idx_milestones_phase_day ON phase_milestones(phase, day_offset_min, day_offset_max);
