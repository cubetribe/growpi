# Frontend Modules Documentation

**Version**: v6.5 (Phase 2 Integration)
**Last Updated**: 2025-12-06

---

## Overview

The GrowPi web interface is built using a modular JavaScript architecture with:

- **Separated Concerns**: HTML, CSS, and JavaScript are split into different files
- **Module Pattern**: Each feature (lamps, curves, logs, costs, etc.) has its own module
- **Pub/Sub State Management**: Central state updates propagate to all modules
- **No Framework Dependencies**: Pure JavaScript with no React, Vue, or Angular

---

## Module Structure

```
pi-controller/grow_pi/web/static/
├── index.html (250 LOC)      - HTML markup only
├── css/
│   └── main.css (900+ LOC)   - All styles
└── js/
    ├── api.js (218 LOC)      - REST API client
    ├── state.js (336 LOC)    - State management
    └── modules/
        ├── control.js        - Tab 1: Lamp control
        ├── curves.js         - Tab 2: Curve editor
        ├── history.js        - Tab 3: Logs & charts
        ├── environment.js     - Tab 4: Dehumidifier (NEW)
        └── costs.js          - Tab 5: Costs (NEW)
```

---

## Loading Order

The HTML `<head>` loads scripts in this specific order:

```html
<!-- 1. API Client (must be first) -->
<script src="js/api.js"></script>

<!-- 2. State Management (depends on api.js) -->
<script src="js/state.js"></script>

<!-- 3. Feature Modules (depend on api.js + state.js) -->
<script src="js/modules/control.js"></script>
<script src="js/modules/curves.js"></script>
<script src="js/modules/history.js"></script>
<script src="js/modules/environment.js"></script>
<script src="js/modules/costs.js"></script>

<!-- 4. Init script (starts everything) -->
<script>
    // Initialize all modules
    window.Control.init();
    window.Curves.init();
    window.History.init();
    window.Environment.init();
    window.Costs.init();
</script>
```

---

## Architecture Pattern

### 1. API Client (`api.js`)

Provides a centralized REST client for all HTTP requests:

```javascript
window.API = {
    // Status endpoints
    getStatus: async () => { ... },
    getLamps: async () => { ... },

    // Lighting endpoints
    setLamp: async (channel, intensity) => { ... },
    getCurves: async () => { ... },
    updateCurve: async (channel, curve) => { ... },

    // Environment endpoints
    getDehumidifierStatus: async () => { ... },
    setDehumidifier: async (action) => { ... },

    // Costs endpoints
    getCosts: async (period) => { ... },
    getCostsConfig: async () => { ... },
    setCostsConfig: async (kwh_price) => { ... }
};
```

### 2. State Management (`state.js`)

Central pub/sub system for state updates:

```javascript
window.State = {
    // Get current state
    get: (key) => { ... },

    // Set state and notify subscribers
    set: (key, value) => { ... },

    // Subscribe to changes
    on: (key, callback) => { ... },

    // Example:
    // State.on('lamps', (lamps) => {
    //     updateUI(lamps);
    // });
};
```

### 3. Module Pattern

Each module exports `init()` and `refresh()` functions:

```javascript
window.ModuleName = {
    init: function() {
        // Initialize DOM, attach event listeners
        // Subscribe to state changes
        State.on('someKey', this.handleUpdate.bind(this));
    },

    refresh: function() {
        // Fetch fresh data from API
        // Update state
    }
};
```

---

## Modules Reference

### Module: Control (`control.js`)

**Purpose**: Lamp intensity sliders and mode switching

**Dependencies**: `api.js`, `state.js`

**Functions**:
```javascript
window.Control = {
    init: function() {
        // Attach slider handlers
        // Attach mode toggle
    },

    refresh: function() {
        // Fetch lamp status
        // Update slider positions
    }
};
```

**UI Elements**:
- Sliders for channels 1-4
- Mode toggle (auto/manual)
- Current intensity display

---

### Module: Curves (`curves.js`)

**Purpose**: Lighting curve editor with 24h preview

**Dependencies**: `api.js`, `state.js`

**Functions**:
```javascript
window.Curves = {
    init: function() {
        // Initialize curve editor UI
        // Attach point add/remove handlers
    },

    refresh: function() {
        // Fetch curves from API
        // Draw 24h preview chart
    }
};
```

**UI Elements**:
- Tab selection (channels 1-4)
- Time/Intensity input table
- Add/Remove point buttons
- 24h preview chart
- Save button

---

### Module: History (`history.js`)

**Purpose**: Sensor data charts and logs

**Dependencies**: `api.js`, `state.js`

**Functions**:
```javascript
window.History = {
    init: function() {
        // Initialize chart containers
        // Attach time range selector
    },

    refresh: function() {
        // Fetch sensor logs
        // Fetch lamp state logs
        // Render charts with Chart.js
    }
};
```

**UI Elements**:
- Time range selector (1h, 24h, 7d)
- Temperature chart
- Humidity chart
- Lamp state timeline
- Log table

---

### Module: Environment (`environment.js`) - NEW v6.5

**Purpose**: Dehumidifier control and configuration

**Dependencies**: `api.js`, `state.js`

**Functions**:
```javascript
window.Environment = {
    init: function() {
        // Initialize dehumidifier UI
        // Attach toggle handlers
        // Attach config form
    },

    refresh: function() {
        // Fetch dehumidifier status
        // Update enable/disable toggle
        // Display current humidity
    }
};
```

**UI Elements**:
- Current temperature/humidity display
- Dehumidifier toggle (on/off)
- Enable automation checkbox
- Target humidity slider
- Hysteresis thresholds (upper/lower)
- Min run/off time inputs
- Status badge (running/idle/off)

---

### Module: Costs (`costs.js`) - NEW v6.5

**Purpose**: Power consumption and cost tracking

**Dependencies**: `api.js`, `state.js`

**Functions**:
```javascript
window.Costs = {
    init: function() {
        // Initialize period selector
        // Attach device filter handlers
    },

    refresh: function() {
        // Fetch costs for selected period
        // Update device cards
        // Calculate totals
    }
};
```

**UI Elements**:
- Period selector (Today/Week/Month)
- Device cost cards (name, kWh, cost, current power)
- Total cost summary
- kWh price config input
- Currency selector

---

## State Keys Reference

### Lamp State

```javascript
State.get('lamps')
// Returns:
{
    channel1: { name: 'Far Red', intensity: 50, mode: 'auto' },
    channel2: { name: 'Warm White', intensity: 75, mode: 'auto' },
    ...
}

State.get('lampCurves')
// Returns curves for all channels
```

### Sensor State

```javascript
State.get('temperature')      // °C
State.get('humidity')         // %
State.get('sensorLogs')       // Array of readings

State.get('lampStateLogs')    // Array of lamp changes
```

### Environment State

```javascript
State.get('dehumidifier')
// Returns:
{
    enabled: true,
    current_humidity: 62.3,
    target: 60,
    state: 'running',
    config: { ... }
}
```

### Cost State

```javascript
State.get('costs')
// Returns:
{
    period: 'today',
    devices: [
        { name: 'Main Light', kwh: 1.237, cost: 0.371 },
        ...
    ],
    total_kwh: 1.898,
    total_cost: 0.569
}

State.get('costsConfig')
// Returns: { kwh_price: 0.30, currency: 'EUR' }
```

---

## Communication Flow

```
User Interaction (click, input)
    ↓
Module Event Handler
    ↓
API.someMethod()
    ↓
Flask Backend
    ↓
API Response
    ↓
State.set(key, value)
    ↓
State subscribers notified
    ↓
Other modules refresh their UI
```

### Example: Change Lamp Intensity

```javascript
// 1. User moves slider in control.js
<input type="range" id="lamp-1" onchange="Control.handleLampChange(1, event)">

// 2. Event handler
Control.handleLampChange = async (channel, event) => {
    const intensity = event.target.value;

    // 3. Call API
    await API.setLamp(channel, intensity);

    // 4. Update state
    State.set('lamps', { ...State.get('lamps'), [channel]: intensity });
};

// 5. Subscriber in history.js
State.on('lamps', (lamps) => {
    History.renderLampTimeline(lamps);  // Update chart
});
```

---

## Adding a New Module

### 1. Create new file: `modules/newfeature.js`

```javascript
window.NewFeature = {
    init: function() {
        // Setup DOM event listeners
        document.getElementById('mybutton').addEventListener('click',
            this.handleClick.bind(this));

        // Subscribe to state changes
        State.on('someKey', this.onStateChange.bind(this));
    },

    refresh: function() {
        // Fetch data
        API.getNewFeatureData().then(data => {
            State.set('newFeature', data);
        });
    },

    handleClick: function(event) {
        // Handle user interaction
    },

    onStateChange: function(newValue) {
        // Update UI when state changes
    }
};
```

### 2. Add to HTML

```html
<script src="js/modules/newfeature.js"></script>
```

### 3. Initialize in startup script

```html
<script>
    window.NewFeature.init();
</script>
```

---

## Best Practices

### DO:
- ✅ Use `State` for shared data
- ✅ Use `API` for all HTTP requests
- ✅ Keep modules independent (no direct imports)
- ✅ Subscribe to state changes, not polling
- ✅ Use `bind(this)` for callbacks
- ✅ Handle errors with try/catch
- ✅ Show loading states during API calls

### DON'T:
- ❌ Modify DOM directly (use State)
- ❌ Make API calls without error handling
- ❌ Store state in module local variables
- ❌ Create circular dependencies between modules
- ❌ Use global variables (use State instead)
- ❌ Hardcode URLs (use API client)

---

## Debugging

### Check State

```javascript
// In browser console:
State.get('lamps')
State.get('temperature')
State.get('dehumidifier')
```

### Monitor API Calls

```javascript
// Check Network tab in DevTools for:
// GET /api/status
// POST /api/lamp/1
// GET /api/dehumidifier/status
// GET /api/costs?period=today
```

### Test Module Initialization

```javascript
// Verify all modules loaded:
console.log(window.Control);      // Should be an object
console.log(window.Curves);
console.log(window.History);
console.log(window.Environment);
console.log(window.Costs);

// Manually initialize:
window.Control.init();
window.Control.refresh();
```

---

## Performance Considerations

### API Call Frequency

- `refresh()` called every 10 seconds
- Each call fetches only needed data
- Database queries optimized with indexes

### Chart Rendering

- Chart.js handles rendering efficiently
- Downsamples data for performance (1000+ points)
- Lazy loads chart library

### Memory Usage

- State limited to current data (no history)
- Event listeners cleaned up on module exit
- No memory leaks from closures

---

## Browser Compatibility

- Chrome/Edge: ✅ Full support
- Firefox: ✅ Full support
- Safari: ✅ Full support
- IE11: ❌ Not supported (uses async/await)

---

## Migration from Monolith

The old `index.html` had 2894 lines of code:
- 760 lines inline `<style>`
- 1426 lines inline `<script>`

The new modular version:
- `index.html`: 250 lines
- `css/main.css`: 900+ lines
- `js/api.js`: 218 lines
- `js/state.js`: 336 lines
- `js/modules/*.js`: 2500+ lines total

**Benefits**:
- Browser caches separate files
- Easier to debug individual features
- Can load modules conditionally
- Better code organization

---

## Support

Questions about modules?

1. Check this README first
2. Review the module source code
3. Look at `DEPLOYMENT_GUIDE.md` for troubleshooting
4. Contact: d.westermann@ol-mg.de

---

**Version**: 2025-12-06 v6.5
**Status**: Production Ready
