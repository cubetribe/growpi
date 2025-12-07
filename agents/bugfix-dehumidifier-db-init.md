# Bugfix Report: Dehumidifier Database Initialization

**Date:** 2025-12-07
**Agent:** Claude Opus 4.5
**Bug:** #1 - Room/Entfeuchter-Steuerung funktioniert nicht
**Status:** FIXED (pending deployment)

---

## Problem Description

**Error Message:**
```
sqlite3.OperationalError: no such table: device_automation_config
```

**Symptoms:**
- Steckdose reagiert nicht auf Steuerung (An/Aus)
- Automatik springt nicht an trotz Wertänderungen
- Room-Tab zeigt Fehler

---

## Root Cause Analysis

### The Catch-22 Problem

The `DehumidifierController._load_config()` method had flawed logic:

```python
# BEFORE (broken):
def _load_config(self) -> None:
    if not os.path.exists(self._db_path):
        logger.warning("Database not found, using defaults")
        return  # ← RETURNS EARLY - NO MIGRATION!

    conn = sqlite3.connect(self._db_path)
    # ... check if tables exist ...
    # ... run migration if needed ...
```

**The Problem:**
1. If database file doesn't exist → `return` early
2. Migration never runs
3. Tables never created
4. API calls fail with "no such table"

### Why `device_time_schedules` Existed

The main database system (`db.py`) has its own initialization that:
1. Creates the `/opt/grow-pi/data/` directory
2. Creates `growpi.db` file
3. Creates its own tables

But `DehumidifierController` assumed the database already existed and only ran migration if it found the file. This worked inconsistently depending on initialization order.

---

## The Fix

### File Modified

`/pi-controller/grow_pi/utils/dehumidifier_controller.py`

### Code Change

```python
# AFTER (fixed):
def _load_config(self) -> None:
    try:
        # BUGFIX 2025-12-07: Create database directory and file if they don't exist
        # This ensures migration can always run on fresh installations
        db_dir = os.path.dirname(self._db_path)
        if not os.path.exists(db_dir):
            logger.info(f"Creating database directory: {db_dir}")
            os.makedirs(db_dir, exist_ok=True)

        # Connect to database (creates file if not exists)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.cursor()

        # Check if tables exist - ALWAYS run migration if missing
        # ... rest of the method unchanged ...
```

### Key Changes

1. **Create directory if missing:** `os.makedirs(db_dir, exist_ok=True)`
2. **Always connect to database:** `sqlite3.connect()` creates file if not exists
3. **Removed early `return`:** Migration check always runs

---

## Testing

### Expected Behavior After Fix

1. Service starts
2. `DehumidifierController.__init__()` runs
3. `_load_config()` is called
4. Directory created if missing
5. Database file created if missing
6. Tables created via migration
7. Config loaded successfully
8. API endpoints work

### Tables Created by Migration

- `switchable_devices` - Device registry
- `device_automation_config` - Automation settings (was missing!)
- `device_time_schedules` - Time windows
- `device_state_log` - Audit log

---

## Deployment

### File to Deploy

```
/pi-controller/grow_pi/utils/dehumidifier_controller.py
```

### Deployment Steps

1. Copy file to Pi
2. Restart service: `sudo systemctl restart grow-pi`
3. Check logs: `sudo journalctl -u grow-pi -f`
4. Test API: `curl http://localhost:5000/api/room`

---

## Risk Assessment

**Risk Level:** LOW

- Uses `IF NOT EXISTS` in SQL - safe to run multiple times
- Uses `os.makedirs(exist_ok=True)` - safe if directory exists
- Does not modify existing data
- Zero-Downtime compatible (no PWM changes)

---

**END OF REPORT**
