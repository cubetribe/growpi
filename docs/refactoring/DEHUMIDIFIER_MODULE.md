# Dehumidifier Module - Extraction Documentation

**Status:** ✅ Completed
**Date:** 2025-12-06
**Agent:** Agent #3 - Frontend Module Extractor (Dehumidifier)
**Source:** `index.html` (v6.4 commit 30f5ee7)
**Target:** New module `js/modules/environment.js`

---

## Executive Summary

Successfully extracted the Dehumidifier Control UI (v6.4 feature) from the monolithic `index.html` into a new dedicated module. The dehumidifier functionality is now properly modularized with clean separation of concerns.

**Key Decision:** Created NEW `environment.js` module instead of extending `control.js` because:
- Dehumidifier is environment control, not lamp control
- Uses separate API namespace (`/api/room/*`)
- Allows future expansion (fans, heating, cooling)
- Maintains logical separation between lighting and climate control

---

## Code Extraction Details

### HTML Structure Extracted

**Lines in original index.html (v6.4):** 966-1003

```html
<section class="section">
    <h2 class="section-title">Entfeuchter</h2>

    <!-- Status Display -->
    <div class="dehumidifier-status">
        <div>
            <span>Status:</span>
            <span id="dehumidifierStatus">--</span>
        </div>
        <div class="mode-switch">
            <button id="dehumidifierOff">AUS</button>
            <button id="dehumidifierOn">AN</button>
        </div>
    </div>

    <!-- Auto-Control Toggle -->
    <div class="dehumidifier-auto">
        <div class="curve-toggle" id="dehumidifierAutoToggle"></div>
        <span>Automatik (Hysterese)</span>
    </div>

    <!-- Configuration Form -->
    <div class="config-form">
        <div style="grid-template-columns: 1fr 1fr 1fr;">
            <div>
                <label>Sollwert (%)</label>
                <input type="number" id="targetHumidity" min="30" max="90" value="60">
            </div>
            <div>
                <label>AN wenn > (%)</label>
                <input type="number" id="thresholdHigh" min="30" max="95" value="65">
            </div>
            <div>
                <label>AUS wenn < (%)</label>
                <input type="number" id="thresholdLow" min="20" max="85" value="55">
            </div>
        </div>
        <button id="btnSaveRoomConfig">Einstellungen speichern</button>
    </div>
</section>
```

**Note:** This HTML remains in `index.html` for now - will be moved to template in future refactoring phase.

### JavaScript Functions Extracted

**Lines in original index.html (v6.4):** 2623-2741

**Functions migrated to `environment.js`:**

1. **DOM References** (lines 2626-2635)
   ```javascript
   roomTempValue, roomHumidityValue, dehumidifierStatus,
   dehumidifierOn, dehumidifierOff, dehumidifierAutoToggle,
   targetHumidity, thresholdHigh, thresholdLow, btnSaveRoomConfig
   ```

2. **`fetchRoomStatus()`** (lines 2637-2683)
   - Fetches `/api/room` endpoint
   - Updates temperature/humidity displays
   - Updates dehumidifier status (on/off)
   - Updates auto-control toggle state
   - Populates config input fields
   - Disables manual buttons when auto-mode is active

3. **`controlDehumidifier(action)`** (lines 2685-2703)
   - Sends POST to `/api/room/dehumidifier`
   - Accepts 'on' or 'off' action
   - Shows success/error messages
   - Refreshes status after control

4. **`saveRoomConfig()`** (lines 2705-2731)
   - Collects config from form inputs
   - Sends POST to `/api/room/config`
   - Payload: `{ enabled, target, threshold_high, threshold_low }`
   - Delays status refresh by 500ms to allow auto-control to kick in

5. **Event Listeners** (lines 2733-2741)
   ```javascript
   dehumidifierOn.click → controlDehumidifier('on')
   dehumidifierOff.click → controlDehumidifier('off')
   dehumidifierAutoToggle.click → toggle 'enabled' class
   btnSaveRoomConfig.click → saveRoomConfig()
   ```

### CSS Styles

**Status:** ⚠️ No dedicated dehumidifier CSS found

**Reuses existing styles:**
- `.section` - Section container
- `.section-title` - Header styling
- `.mode-switch` / `.mode-option` - Button styling
- `.curve-toggle` - Toggle switch (borrowed from curves module)
- `.config-form` - Form styling
- Inline styles for layout (will be extracted in future CSS refactoring)

**Action Item:** If custom dehumidifier styles are added in future, place them in `css/main.css` under:
```css
/* === Environment Control === */
.dehumidifier-status { ... }
.dehumidifier-auto { ... }
```

---

## New Module Structure

### File: `js/modules/environment.js`

**Lines of Code:** 167 LOC

**Public API:**
```javascript
export function initEnvironmentTab()
export function cleanupEnvironmentTab()
export async function fetchRoomStatus()
export async function controlDehumidifier(action)
export async function saveRoomConfig()
```

**Module Pattern:**
- ES6 Module with named exports
- Uses `GrowPiAPI` for all backend communication
- Auto-refresh interval: 10 seconds
- Cleanup function for proper teardown
- Uses global `showSuccess()`/`showError()` for notifications

**Dependencies:**
- `../api.js` (GrowPiAPI)
- Global window functions: `showSuccess()`, `showError()`

---

## API Integration

### New API Methods Added to `api.js`

**File:** `js/api.js`
**Lines Added:** 215-250 (36 LOC)

**Methods:**

1. **`getRoomStatus()`**
   ```javascript
   GET /api/room
   Returns: {
     success: boolean,
     temperature: number,
     humidity: number,
     dehumidifier: {
       is_on: boolean,
       config: {
         enabled: boolean,
         target: number,
         threshold_high: number,
         threshold_low: number
       }
     }
   }
   ```

2. **`controlDehumidifier(action)`**
   ```javascript
   POST /api/room/dehumidifier
   Body: { action: 'on' | 'off' }
   Returns: { success: boolean, error?: string }
   ```

3. **`saveRoomConfig(config)`**
   ```javascript
   POST /api/room/config
   Body: {
     enabled: boolean,
     target: number,
     threshold_high: number,
     threshold_low: number
   }
   Returns: { success: boolean, error?: string }
   ```

**Validation:**
- `controlDehumidifier()` validates action is 'on' or 'off'
- Throws error if invalid action

---

## Backend Requirements

**Python Flask Endpoints (assumed from frontend code):**

### `GET /api/room`
- Returns current room climate data
- Includes DHT22 sensor readings (temp/humidity)
- Includes dehumidifier state and config

### `POST /api/room/dehumidifier`
- Manually controls dehumidifier relay
- Accepts `{ action: 'on' | 'off' }`
- Returns `{ success: true }` or `{ success: false, error: 'message' }`

### `POST /api/room/config`
- Saves auto-control configuration to database
- Accepts hysteresis parameters
- Triggers immediate re-evaluation if auto-control is enabled

**Note:** These endpoints likely exist in `pi-controller/grow_pi/routes/` from v6.4 commit.

---

## Feature Overview

### Manual Control
- Two-button interface (AN/AUS)
- Immediate relay control
- Visual status feedback (green = ON, gray = OFF)
- Active button highlighting

### Auto-Control (Hysteresis)
- Toggle switch to enable/disable
- **Target Humidity:** Desired setpoint (30-90%)
- **High Threshold:** Turn ON when humidity exceeds this (30-95%)
- **Low Threshold:** Turn OFF when humidity falls below this (20-85%)

**Example Configuration:**
```
Target: 60%
High: 65%  → Dehumidifier turns ON when humidity > 65%
Low: 55%   → Dehumidifier turns OFF when humidity < 55%
```

**Behavior:**
- When auto-mode is enabled, manual buttons are disabled (opacity 0.5, no pointer events)
- System automatically controls relay based on current humidity vs thresholds
- Backend runs hysteresis check every 10 seconds (based on commit message 24370a8)

### Status Display
- Real-time ON/OFF indicator
- Color-coded: `#11ff55` (green) for ON, `#888` (gray) for OFF
- Updates every 10 seconds via auto-refresh

---

## Integration Points

### How to Use in `index.html` (future refactoring)

**Import the module:**
```html
<script type="module">
  import { initEnvironmentTab, cleanupEnvironmentTab } from './js/modules/environment.js';

  // Initialize when Room tab is selected
  function showTab(tabName) {
    if (tabName === 'room') {
      initEnvironmentTab();
    }
  }

  // Cleanup when switching away
  window.addEventListener('beforeunload', cleanupEnvironmentTab);
</script>
```

**Current State:**
- Module is extracted but NOT yet integrated into main HTML
- HTML still contains inline script for dehumidifier
- Requires main app refactoring to use module system

---

## Comparison with Other Modules

### Similarities to `control.js`
- Auto-refresh pattern (10-second interval)
- Cleanup function to prevent memory leaks
- Debounced API calls (not used in environment.js yet)
- Mode switching (manual/auto)

### Differences
- Uses different API namespace (`/api/room/*` vs `/api/status`, `/api/lamp/*`)
- Simpler state management (no curve interpolation)
- Binary control (on/off) vs multi-level (0-100% intensity)
- Form-based config vs slider-based control

### Why Separate Module?
1. **Logical Domain:** Climate control ≠ Light control
2. **API Isolation:** Separate backend routes
3. **Future Expansion:** Easy to add fans, heaters, coolers
4. **Code Clarity:** Avoid control.js becoming a "god module"

---

## Code Quality Metrics

**Before (Monolithic):**
- `index.html`: 2894 LOC
- Dehumidifier code: ~120 LOC inline JS + 38 LOC HTML

**After (Modular):**
- `js/modules/environment.js`: 167 LOC
- `js/api.js`: +36 LOC (API methods)
- `index.html`: Still 2894 LOC (HTML not yet refactored)

**Total Extracted:** 203 LOC (167 + 36)

**Readability Improvements:**
- ✅ Clear module boundaries
- ✅ JSDoc documentation on all public functions
- ✅ Consistent error handling
- ✅ Separation of concerns (API vs UI logic)

---

## Testing Checklist

**Manual Testing Required:**

- [ ] Room tab displays current temperature/humidity
- [ ] Dehumidifier status shows correctly (AN/AUS)
- [ ] Manual ON button activates dehumidifier
- [ ] Manual OFF button deactivates dehumidifier
- [ ] Auto-control toggle switches visual state
- [ ] Manual buttons disable when auto-mode is ON
- [ ] Config form accepts valid humidity values (30-90%)
- [ ] Save button persists config to backend
- [ ] Auto-control triggers relay based on thresholds
- [ ] Status refreshes every 10 seconds
- [ ] Error messages show on API failures
- [ ] Success messages show on successful operations

**Integration Testing:**

- [ ] Module loads without errors in browser console
- [ ] API methods are accessible from module
- [ ] Tab switching cleans up interval timers
- [ ] No memory leaks after multiple tab switches

---

## Future Enhancements

**Potential Additions:**

1. **Fan Control**
   - Integrate exhaust/intake fans
   - Speed control (0-100%)
   - Temperature-based automation

2. **Heating/Cooling**
   - Heater relay control
   - Temperature setpoints
   - PID-based regulation

3. **Advanced Charts**
   - Humidity history graph (like sensors tab)
   - Dehumidifier runtime logs
   - Cost calculation per device

4. **Smart Alerts**
   - Humidity too high/low warnings
   - Dehumidifier failure detection
   - Email/push notifications

5. **Schedule Override**
   - Time-based auto-control schedules
   - Night mode (different thresholds)
   - Vacation mode

---

## Migration Notes

**From v6.4 Commit:**
- Original code extracted from commit `30f5ee7`
- Commit message: "feat: v6.3 Kosten-Tab + v6.4 Entfeuchter-UI (monolithisch)"
- Commit date: Latest on main branch

**Refactoring Steps Taken:**

1. ✅ Identified all dehumidifier-related code in `index.html`
2. ✅ Analyzed dependencies and API endpoints
3. ✅ Decided to create new `environment.js` module
4. ✅ Extracted JavaScript functions with proper error handling
5. ✅ Added API methods to centralized `api.js`
6. ✅ Documented module structure and usage
7. ⚠️ HTML remains in `index.html` (deferred to template refactoring)
8. ⚠️ CSS remains inline/global (deferred to CSS extraction phase)

**Next Agent Tasks:**

- **Agent #4:** Extract Room tab HTML to template
- **Agent #5:** Extract inline CSS to `css/main.css`
- **Agent #6:** Integrate environment.js into main app module loader

---

## Files Modified

### Created
- **`pi-controller/grow_pi/web/static/js/modules/environment.js`**
  - 167 LOC
  - ES6 Module format
  - Handles dehumidifier control and room climate display

### Modified
- **`pi-controller/grow_pi/web/static/js/api.js`**
  - Added 36 LOC (lines 215-250)
  - Added 3 new API methods for room environment

### Unchanged (Future Work)
- **`pi-controller/grow_pi/web/static/index.html`**
  - HTML structure remains (will be templated later)
  - Inline JS remains (will be removed when module loader is integrated)

- **`pi-controller/grow_pi/web/static/css/main.css`**
  - No dehumidifier-specific styles yet
  - Uses global/inline styles

---

## Backend Code Location

**Python Routes (assumed from v6.4):**

Likely in one of these files:
- `pi-controller/grow_pi/routes/room.py` (new file for v6.4)
- `pi-controller/grow_pi/routes/api.py` (existing file extended)

**Database Schema (SQLite):**

Likely has table:
```sql
CREATE TABLE dehumidifier_config (
    id INTEGER PRIMARY KEY,
    enabled BOOLEAN DEFAULT 0,
    target REAL DEFAULT 60.0,
    threshold_high REAL DEFAULT 65.0,
    threshold_low REAL DEFAULT 55.0,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Hardware Integration:**

Likely uses:
- GPIO pin for relay control (e.g., GPIO 17)
- DHT22 sensor for humidity reading (already configured on GPIO 4)
- 10-second check interval in background thread

---

## Decision Rationale

### Why NOT extend `control.js`?

**Considered Option A:** Add dehumidifier to existing `control.js`

**Rejected because:**
- Different domain (climate vs lighting)
- Different API structure (`/api/room/*` vs `/api/lamp/*`)
- Control.js already focused on lamp sliders and mode switching
- Would mix concerns (lights + environment)

**Chosen Option B:** Create new `environment.js` module

**Benefits:**
- Clear separation of concerns
- Scalable for future climate features
- Own API namespace
- Easier to test independently
- Follows single-responsibility principle

---

## Lessons Learned

**What Went Well:**
- Clear module pattern from existing `control.js` / `curves.js`
- API abstraction made integration straightforward
- Inline code was well-structured (easy to extract)

**Challenges:**
- Finding dehumidifier code in 2894-line HTML file
- Distinguishing between room tab and greenhouse tab (both have humidity)
- Deciding module name: `environment.js` vs `climate.js` vs `room.js`

**Recommendations for Next Agent:**
- Use `git show 30f5ee7:path/to/file` to view v6.4 commit files
- Search for keywords: "dehumidifier", "room", "/api/room"
- Test API endpoints with `curl` before frontend integration

---

## LOC Summary

**Total Extracted Code:**

| File | Lines Added | Purpose |
|------|------------|---------|
| `js/modules/environment.js` | 167 | Main module logic |
| `js/api.js` | 36 | API methods |
| **TOTAL** | **203** | Dehumidifier feature |

**Removed from index.html:** 0 (code still present - will be removed in integration phase)

**Net Change:** +203 LOC (new modular code)

---

## Status: ✅ COMPLETE

**Deliverables:**

1. ✅ New module created: `js/modules/environment.js` (167 LOC)
2. ✅ API methods added: `api.js` (+36 LOC)
3. ✅ Comprehensive documentation: `DEHUMIDIFIER_MODULE.md`
4. ✅ Decision documented: New module vs extending control.js

**Agent #3 Task Complete.**

---

**Last Updated:** 2025-12-06
**Author:** Agent #3 - Frontend Module Extractor (Dehumidifier)
**Review Status:** Ready for Agent #4 (Template Extraction)
