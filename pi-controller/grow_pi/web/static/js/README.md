# GrowPi Frontend JavaScript Modules

## Overview

This directory contains modular JavaScript components for the GrowPi web interface, created as part of Phase 1 refactoring to improve code organization and maintainability.

## Files

### 1. `api.js` - API Client Layer

Centralized API communication with the Flask backend.

**Key Features:**
- Single source of truth for all API endpoints
- Consistent error handling across requests
- Type-safe methods with clear documentation
- Generic request wrappers (GET, POST, PUT)

**Available Methods:**

#### System Status
- `getStatus()` - Get current system status (temp, humidity, lamps)
- `getTemperature()` - Get temperature reading
- `getHumidity()` - Get humidity reading

#### Lamp Control
- `setLamp(channel, intensity)` - Set lamp intensity (0-100)

#### Mode Management
- `getMode()` - Get current mode ('auto' | 'manual')
- `setMode(mode)` - Set control mode

#### Curve Management
- `getCurves()` - Get all lamp curves
- `updateCurve(channel, data)` - Update specific curve
- `getCurvePreview()` - Get 24h preview
- `getCurveIntensities()` - Get current curve intensities

#### Historical Data
- `getSensorLogs(type, hours, limit)` - Temperature/humidity history
- `getLampLogs(channel, hours, limit)` - Lamp intensity history
- `getPlugLogs(hours, limit)` - Smart plug power consumption
- `getEventLogs(hours, limit)` - System event logs

**Usage Example:**
```javascript
// Fetch current status
const status = await GrowPiAPI.getStatus();
console.log('Temperature:', status.temperature);

// Set lamp to 50%
await GrowPiAPI.setLamp(1, 50);

// Switch to auto mode
await GrowPiAPI.setMode('auto');

// Get last 7 days of temperature data
const tempLogs = await GrowPiAPI.getSensorLogs('temperature', 168, 1000);
```

---

### 2. `state.js` - Global State Management

Reactive state management with pub/sub pattern for application-wide state.

**Key Features:**
- Centralized state storage
- Pub/Sub pattern for reactive updates
- Immutable state access
- Type-safe getters/setters

**State Properties:**
- `currentMode` - Control mode ('auto' | 'manual')
- `curvesData` - All lamp curves by channel
- `activeChannel` - Currently focused curve editor channel (1-4)
- `lampStates` - Current lamp intensity values
- `temperature` - Current temperature reading
- `humidity` - Current humidity reading
- `online` - System online status
- `lastUpdate` - Last status update timestamp
- `historyRange` - History chart time range (hours)
- `previewData` - 24h curve preview data

**Available Methods:**

#### Subscription
- `subscribe(key, callback)` - Subscribe to state changes (returns unsubscribe function)

#### Mode
- `getMode()` / `setMode(mode)`

#### Curves
- `getCurvesData()` / `setCurvesData(curvesData)`
- `getCurve(channel)` / `updateCurve(channel, curveData)`
- `getActiveChannel()` / `setActiveChannel(channel)`

#### Lamps
- `getLampStates()` / `setLampStates(lampStates)`
- `getLampState(channel)`

#### Sensors
- `getTemperature()` / `setTemperature(temp)`
- `getHumidity()` / `setHumidity(hum)`

#### System
- `isOnline()` / `setOnline(online)`
- `getLastUpdate()` / `setLastUpdate(timestamp)`
- `getHistoryRange()` / `setHistoryRange(hours)`

#### Preview
- `getPreviewData()` / `setPreviewData(previewData)`

#### Utility
- `getState()` - Get full state snapshot
- `reset()` - Reset to default state

**Usage Example:**
```javascript
// Subscribe to mode changes
const unsubscribe = GrowPiState.subscribe('currentMode', (newMode) => {
    console.log('Mode changed to:', newMode);
    updateUI(newMode);
});

// Update state
GrowPiState.setMode('manual');
GrowPiState.setTemperature(22.5);

// Get state
const currentTemp = GrowPiState.getTemperature();
const lampState = GrowPiState.getLampState(1);

// Unsubscribe when done
unsubscribe();
```

---

## Integration with Existing Code

### Current Status (index.html)

The main `index.html` file currently contains ~2400 lines of inline JavaScript. This includes:
- Direct `fetch()` calls scattered throughout
- Global variables (`curvesData`, `currentMode`, etc.)
- Event handlers mixed with business logic
- Chart initialization and update logic

### Next Steps (Migration Plan)

**Phase 2 - Component Extraction:**
1. Extract tab management → `ui/tabs.js`
2. Extract curve editor → `components/curveEditor.js`
3. Extract chart logic → `components/charts.js`
4. Extract UI utilities → `ui/notifications.js`

**Phase 3 - Integration:**
1. Update `index.html` to include module scripts:
   ```html
   <script src="js/state.js"></script>
   <script src="js/api.js"></script>
   <script src="js/ui/tabs.js"></script>
   <script src="js/components/curveEditor.js"></script>
   ```

2. Replace inline fetch calls with `GrowPiAPI` methods
3. Replace global variables with `GrowPiState` access
4. Use pub/sub for UI updates instead of direct DOM manipulation

**Example Migration:**
```javascript
// BEFORE (inline in index.html)
async function fetchStatus() {
    const res = await fetch('/api/status');
    const data = await res.json();
    tempValue.innerHTML = `${data.temperature}°C`;
}

// AFTER (with modules)
async function fetchStatus() {
    const data = await GrowPiAPI.getStatus();
    GrowPiState.setTemperature(data.temperature);
    // UI updates happen via state subscription
}
```

---

## Architecture Benefits

### Before (Monolithic)
- 2400+ lines in single HTML file
- No separation of concerns
- Hard to test individual components
- Global namespace pollution
- Difficult to debug

### After (Modular)
- Clear separation: API | State | UI | Components
- Reusable modules
- Easy to unit test
- Encapsulated state management
- Better debugging with stack traces
- Scalable architecture

---

## Browser Compatibility

Both modules use IIFE (Immediately Invoked Function Expressions) pattern for browser compatibility without requiring a build step.

**Supported:**
- Chrome 60+
- Firefox 55+
- Safari 11+
- Edge 79+

**ES6 Features Used:**
- Arrow functions
- Async/await
- Destructuring
- Template literals
- Spread operator

For older browser support, transpilation with Babel would be required.

---

## Development Guidelines

### Adding New API Endpoints

1. Add method to `api.js`:
```javascript
async getNewEndpoint(param) {
    return await get(`/api/new-endpoint?param=${param}`);
}
```

2. Update this README with method documentation

### Adding New State Properties

1. Add property to `state` object in `state.js`
2. Add getter/setter methods following naming convention
3. Update README documentation

### Testing

```javascript
// Test API (in browser console)
const status = await GrowPiAPI.getStatus();
console.log(status);

// Test State
GrowPiState.setMode('auto');
GrowPiState.subscribe('currentMode', console.log);
GrowPiState.setMode('manual'); // Should log 'manual'
```

---

## Future Improvements

- [ ] Add TypeScript definitions (.d.ts files)
- [ ] Implement request caching for frequently accessed data
- [ ] Add request retry logic with exponential backoff
- [ ] Implement WebSocket support for real-time updates
- [ ] Add state persistence (localStorage)
- [ ] Create unit tests (Jest/Mocha)
- [ ] Add API request queue for offline support
- [ ] Implement optimistic UI updates

---

**Last Updated:** 2025-12-06
**Author:** Agent 8 (Frontend Refactoring)
**Branch:** `refactoring/phase-1-modularization`
