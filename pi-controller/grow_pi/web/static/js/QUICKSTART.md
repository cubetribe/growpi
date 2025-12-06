# GrowPi Modules - Quick Start Guide

Get started with the new modular JavaScript architecture in 5 minutes!

---

## 🚀 Installation

### 1. Include the Modules

Add these script tags to your HTML file (before your main script):

```html
<script src="js/state.js"></script>
<script src="js/api.js"></script>
```

That's it! No build tools, no npm, no bundlers needed.

---

## 📝 Basic Usage

### API Client

```javascript
// Get system status
const status = await GrowPiAPI.getStatus();
console.log('Temperature:', status.temperature);
console.log('Humidity:', status.humidity);

// Set lamp intensity
await GrowPiAPI.setLamp(1, 50);  // Channel 1 to 50%

// Switch to auto mode
await GrowPiAPI.setMode('auto');

// Get curves
const curves = await GrowPiAPI.getCurves();
curves.curves.forEach(curve => {
    console.log(`Channel ${curve.channel}: ${curve.name}`);
});
```

### State Management

```javascript
// Set state
GrowPiState.setMode('manual');
GrowPiState.setTemperature(22.5);
GrowPiState.setHumidity(65);

// Get state
const mode = GrowPiState.getMode();
const temp = GrowPiState.getTemperature();

// Subscribe to changes (reactive updates!)
GrowPiState.subscribe('currentMode', (newMode) => {
    console.log('Mode changed to:', newMode);
    updateUI(newMode);
});

// Update state (triggers subscriber)
GrowPiState.setMode('auto'); // Subscriber will be called!
```

---

## 🎯 Common Patterns

### Pattern 1: Fetch and Update UI

```javascript
async function fetchAndDisplayStatus() {
    try {
        const data = await GrowPiAPI.getStatus();

        // Update state
        GrowPiState.setTemperature(data.temperature);
        GrowPiState.setHumidity(data.humidity);
        GrowPiState.setOnline(true);

        // UI updates happen via subscriptions!
    } catch (error) {
        console.error('Error:', error);
        GrowPiState.setOnline(false);
    }
}
```

### Pattern 2: Reactive UI Updates

```javascript
// Setup subscriptions once
GrowPiState.subscribe('temperature', (temp) => {
    document.getElementById('temp').textContent = `${temp}°C`;
});

GrowPiState.subscribe('online', (online) => {
    statusBadge.className = online ? 'online' : 'offline';
});

// Now just update state, UI updates automatically!
GrowPiState.setTemperature(23.5);  // UI updates automatically
GrowPiState.setOnline(true);       // Status badge updates
```

### Pattern 3: Batch API Calls

```javascript
// Fetch multiple endpoints in parallel
const [status, curves, mode] = await Promise.all([
    GrowPiAPI.getStatus(),
    GrowPiAPI.getCurves(),
    GrowPiAPI.getMode()
]);

// Process results
console.log('All data loaded:', { status, curves, mode });
```

### Pattern 4: Error Handling

```javascript
async function safeFetchStatus() {
    try {
        const status = await GrowPiAPI.getStatus();
        return status;
    } catch (error) {
        console.error('API Error:', error.message);
        showError('Failed to fetch status');
        return null;
    }
}
```

---

## 🧪 Testing

### Option 1: Browser Console

```javascript
// Open browser console (F12) and try:
await GrowPiAPI.getStatus();
GrowPiState.setMode('manual');
GrowPiState.subscribe('currentMode', console.log);
```

### Option 2: Test Page

Open the interactive test page in your browser:

```
pi-controller/grow_pi/web/static/js/test-modules.html
```

Click buttons to run tests and see results in real-time!

---

## 📚 Full API Reference

### GrowPiAPI Methods

| Method | Description | Example |
|--------|-------------|---------|
| `getStatus()` | Get current system status | `await GrowPiAPI.getStatus()` |
| `setLamp(ch, int)` | Set lamp intensity | `await GrowPiAPI.setLamp(1, 50)` |
| `getMode()` | Get control mode | `await GrowPiAPI.getMode()` |
| `setMode(mode)` | Set mode ('auto'/'manual') | `await GrowPiAPI.setMode('auto')` |
| `getCurves()` | Get all lamp curves | `await GrowPiAPI.getCurves()` |
| `updateCurve(ch, data)` | Update curve | `await GrowPiAPI.updateCurve(1, {...})` |
| `getSensorLogs(type, h, lim)` | Get sensor history | `await GrowPiAPI.getSensorLogs('temperature', 24, 1000)` |

### GrowPiState Methods

| Method | Description | Example |
|--------|-------------|---------|
| `subscribe(key, fn)` | Subscribe to changes | `GrowPiState.subscribe('currentMode', console.log)` |
| `getMode()` / `setMode(m)` | Mode getter/setter | `GrowPiState.setMode('auto')` |
| `getTemperature()` / `setTemperature(t)` | Temperature | `GrowPiState.setTemperature(22.5)` |
| `getCurvesData()` / `setCurvesData(d)` | Curves data | `GrowPiState.setCurvesData({...})` |
| `isOnline()` / `setOnline(b)` | Online status | `GrowPiState.setOnline(true)` |

See `README.md` for complete reference with all 15 API methods and 30 state methods!

---

## 🔄 Migration from Old Code

### Before (Direct fetch)
```javascript
const res = await fetch('/api/status');
const data = await res.json();
tempValue.textContent = data.temperature;
```

### After (With modules)
```javascript
const data = await GrowPiAPI.getStatus();
GrowPiState.setTemperature(data.temperature);
// UI updates automatically via subscription!
```

See `MIGRATION_EXAMPLE.md` for detailed step-by-step migration guide!

---

## 🐛 Troubleshooting

### "GrowPiAPI is not defined"

**Solution:** Make sure you included the script:
```html
<script src="js/api.js"></script>
```

### "Failed to fetch"

**Solution:** Backend is not running. Start Flask server:
```bash
cd pi-controller
python -m grow_pi.web.api
```

### State not updating UI

**Solution:** Make sure you setup subscriptions BEFORE updating state:
```javascript
// ✓ Correct order
GrowPiState.subscribe('currentMode', updateUI);
GrowPiState.setMode('auto');  // Triggers updateUI

// ✗ Wrong order
GrowPiState.setMode('auto');  // No subscriber yet!
GrowPiState.subscribe('currentMode', updateUI);  // Too late
```

---

## 💡 Pro Tips

### Tip 1: Unsubscribe when done
```javascript
const unsubscribe = GrowPiState.subscribe('currentMode', callback);

// Later...
unsubscribe();  // Clean up to prevent memory leaks
```

### Tip 2: Check state before API calls
```javascript
// Avoid unnecessary API calls
if (GrowPiState.getMode() !== 'auto') {
    await GrowPiAPI.setMode('auto');
}
```

### Tip 3: Use parallel API calls
```javascript
// ✓ Fast (parallel)
await Promise.all([
    GrowPiAPI.getStatus(),
    GrowPiAPI.getCurves()
]);

// ✗ Slow (sequential)
await GrowPiAPI.getStatus();
await GrowPiAPI.getCurves();
```

### Tip 4: Cache frequently accessed state
```javascript
// Instead of calling getter repeatedly
const mode = GrowPiState.getMode();
if (mode === 'auto') { /* ... */ }
if (mode === 'manual') { /* ... */ }
```

---

## 🎨 Real-World Example

Complete example showing everything together:

```javascript
// 1. Setup subscriptions (once, at initialization)
GrowPiState.subscribe('temperature', (temp) => {
    document.getElementById('temp').textContent = `${temp}°C`;
});

GrowPiState.subscribe('currentMode', (mode) => {
    const lampSection = document.getElementById('lampSection');
    lampSection.classList.toggle('disabled', mode === 'auto');
});

GrowPiState.subscribe('online', (online) => {
    const badge = document.getElementById('statusBadge');
    badge.className = online ? 'status-online' : 'status-offline';
    badge.textContent = online ? 'Online' : 'Offline';
});

// 2. Fetch data from API
async function updateDashboard() {
    try {
        const [status, mode] = await Promise.all([
            GrowPiAPI.getStatus(),
            GrowPiAPI.getMode()
        ]);

        // 3. Update state (triggers all subscribed UI updates)
        GrowPiState.setTemperature(status.temperature);
        GrowPiState.setHumidity(status.humidity);
        GrowPiState.setMode(mode.mode);
        GrowPiState.setOnline(true);

        // UI automatically updates via subscriptions!

    } catch (error) {
        console.error('Update failed:', error);
        GrowPiState.setOnline(false);
    }
}

// 4. Run periodically
updateDashboard();
setInterval(updateDashboard, 10000);  // Every 10 seconds

// 5. Handle user interactions
document.getElementById('btnSetMode').onclick = async () => {
    try {
        await GrowPiAPI.setMode('manual');
        GrowPiState.setMode('manual');  // UI updates automatically!
        showSuccess('Mode changed to manual');
    } catch (error) {
        showError('Failed to change mode');
    }
};
```

---

## 📖 Next Steps

1. ✅ **Read this guide** - You're here!
2. 📝 **Read `README.md`** - Complete API reference
3. 🔄 **Read `MIGRATION_EXAMPLE.md`** - Step-by-step migration
4. 🧪 **Test with `test-modules.html`** - Interactive testing
5. 🚀 **Start migrating** - One function at a time!

---

## 🆘 Need Help?

- Full documentation: `README.md`
- Migration guide: `MIGRATION_EXAMPLE.md`
- Test page: `test-modules.html`
- Phase 1 summary: `/REFACTORING_PHASE1_SUMMARY.md`

---

**Happy coding!** 🎉
