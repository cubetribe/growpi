-- Migration: Add device_time_schedules table for time-based device control
-- Version: 6.8.0
-- Date: 2025-12-06
-- Feature: #2 - Zeitbasierte Geraete-Schaltung

-- ============================================================================
-- NEW TABLE: Switchable Devices (for future multi-device support)
-- ============================================================================
CREATE TABLE IF NOT EXISTS switchable_devices (
    id INTEGER PRIMARY KEY,
    device_type TEXT NOT NULL,          -- 'dehumidifier', 'heater', 'fan'
    name TEXT NOT NULL,                 -- Display name
    tuya_device_id TEXT,               -- Tuya Cloud device ID
    gpio_pin INTEGER,                   -- GPIO pin (if applicable)
    automation_mode TEXT DEFAULT 'auto', -- 'auto' or 'manual'
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Insert default dehumidifier device (if not exists)
INSERT OR IGNORE INTO switchable_devices (id, device_type, name, automation_mode)
VALUES (1, 'dehumidifier', 'Entfeuchter', 'auto');

-- ============================================================================
-- NEW TABLE: Device Automation Configuration
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_automation_config (
    id INTEGER PRIMARY KEY,
    device_id INTEGER NOT NULL,
    enabled BOOLEAN DEFAULT 1,           -- Enable automation
    target_value REAL,                   -- Target value (e.g., 60% humidity)
    threshold_high REAL,                 -- High threshold (turn on)
    threshold_low REAL,                  -- Low threshold (turn off)
    min_run_time INTEGER DEFAULT 300,    -- Minimum run time in seconds
    min_off_time INTEGER DEFAULT 60,     -- Minimum off time in seconds
    time_schedule_enabled BOOLEAN DEFAULT 0,  -- Enable time-based scheduling
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES switchable_devices(id) ON DELETE CASCADE
);

-- Insert default config for dehumidifier
INSERT OR IGNORE INTO device_automation_config (id, device_id, target_value, threshold_high, threshold_low)
VALUES (1, 1, 60.0, 5.0, 5.0);

-- ============================================================================
-- NEW TABLE: Device Time Schedules
-- ============================================================================
-- Stores time windows for time-based device control
-- Priority: Time Schedule > Humidity Automation > Manual
CREATE TABLE IF NOT EXISTS device_time_schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device_id INTEGER NOT NULL,
    start_time TEXT NOT NULL,            -- "HH:MM" format (24h)
    end_time TEXT NOT NULL,              -- "HH:MM" format (24h)
    target_state TEXT NOT NULL DEFAULT 'on',  -- 'on' or 'off'
    enabled BOOLEAN DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES switchable_devices(id) ON DELETE CASCADE
);

-- Index for fast time-based lookups
CREATE INDEX IF NOT EXISTS idx_time_schedules_device_enabled
ON device_time_schedules(device_id, enabled);

-- Index for time range queries
CREATE INDEX IF NOT EXISTS idx_time_schedules_times
ON device_time_schedules(start_time, end_time);

-- ============================================================================
-- NEW TABLE: Device State Log (for tracking automation decisions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS device_state_log (
    id TEXT PRIMARY KEY,
    device_id INTEGER NOT NULL,
    state TEXT NOT NULL,                 -- 'on' or 'off'
    trigger_type TEXT NOT NULL,          -- 'time_schedule', 'humidity_auto', 'manual'
    trigger_details TEXT,                -- JSON with additional info
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (device_id) REFERENCES switchable_devices(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_device_state_log_device_time
ON device_state_log(device_id, created_at DESC);

-- ============================================================================
-- Sample Data: Time Schedules for Dehumidifier
-- ============================================================================
-- Example: Turn on 10 minutes before lights off (19:50), run for 40 minutes (until 20:30)
INSERT OR IGNORE INTO device_time_schedules (device_id, start_time, end_time, target_state, enabled)
VALUES (1, '19:50', '20:30', 'on', 0);  -- Disabled by default

-- Example: Morning humidity reduction (06:00 - 06:30)
INSERT OR IGNORE INTO device_time_schedules (device_id, start_time, end_time, target_state, enabled)
VALUES (1, '06:00', '06:30', 'on', 0);  -- Disabled by default
