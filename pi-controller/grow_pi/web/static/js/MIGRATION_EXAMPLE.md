# Migration Example: Refactoring index.html

This document shows step-by-step how to migrate the existing monolithic `index.html` to use the new modular JavaScript architecture.

## Step 1: Include Module Scripts

Add these script tags BEFORE the main inline script in `index.html`:

```html
<!-- Add before closing </body> tag -->
<script src="js/state.js"></script>
<script src="js/api.js"></script>
<script>
    // Your refactored code here...
</script>
```

## Step 2: Replace Global Variables with State

### BEFORE (Lines 1041-1049):
```javascript
const statusBadge = document.getElementById("statusBadge");
const lastUpdate = document.getElementById("lastUpdate");
// ... more DOM refs
let debounceTimers = {};
let curvesData = {};
let previewData = [];
let activeChannel = 1;
let currentMode = 'auto';
```

### AFTER:
```javascript
// DOM references stay the same
const statusBadge = document.getElementById("statusBadge");
const lastUpdate = document.getElementById("lastUpdate");
// ... more DOM refs

// Replace global state variables with GrowPiState
// (No more global curvesData, previewData, activeChannel, currentMode!)

// Setup state subscriptions for reactive UI updates
GrowPiState.subscribe('currentMode', (mode) => {
    updateModeUI(mode);
});

GrowPiState.subscribe('temperature', (temp) => {
    if (temp !== null) {
        tempValue.innerHTML = `${temp.toFixed(1)}<span class="temp-unit">°C</span>`;
    }
});

GrowPiState.subscribe('humidity', (hum) => {
    if (hum !== null) {
        humidityValue.innerHTML = `${hum.toFixed(0)}<span class="temp-unit">%</span>`;
    }
});

GrowPiState.subscribe('online', (online) => {
    statusBadge.className = `status-badge ${online ? 'status-online' : 'status-offline'}`;
    statusBadge.textContent = online ? 'Online' : 'Offline';
});
```

## Step 3: Replace Direct fetch() with API Methods

### BEFORE (Lines 1118-1202 - fetchStatus):
```javascript
async function fetchStatus() {
    try {
        const [statusRes, intensitiesRes] = await Promise.all([
            fetch("/api/status"),
            fetch("/api/curves/intensities"),
        ]);

        if (!statusRes.ok) {
            throw new Error(`HTTP ${statusRes.status}`);
        }

        const data = await statusRes.json();
        let curveIntensities = {};

        if (intensitiesRes.ok) {
            const intensitiesData = await intensitiesRes.json();
            if (intensitiesData.success && intensitiesData.intensities) {
                curveIntensities = intensitiesData.intensities;
            }
        }

        if (data.temperature !== null && data.temperature !== undefined) {
            tempValue.innerHTML = `${data.temperature.toFixed(1)}<span class="temp-unit">°C</span>`;
        }

        if (data.humidity !== null && data.humidity !== undefined) {
            humidityValue.innerHTML = `${data.humidity.toFixed(0)}<span class="temp-unit">%</span>`;
        }

        if (data.lamps) {
            data.lamps.forEach((lamp) => {
                const slider = document.getElementById(`lamp${lamp.channel}`);
                const valueEl = document.getElementById(`lamp${lamp.channel}Value`);
                if (slider && valueEl) {
                    const displayValue = (currentMode === 'auto' && curveIntensities[lamp.channel] !== undefined)
                        ? curveIntensities[lamp.channel]
                        : lamp.intensity;
                    slider.value = displayValue;
                    valueEl.textContent = `${displayValue}%`;
                }
            });
        }

        updateStatus(true);
        lastUpdate.textContent = `Aktualisiert: ${formatTime()}`;
    } catch (error) {
        console.error("Fetch error:", error);
        updateStatus(false);
    }
}
```

### AFTER:
```javascript
async function fetchStatus() {
    try {
        // Use API client instead of direct fetch
        const [statusData, intensitiesData] = await Promise.all([
            GrowPiAPI.getStatus(),
            GrowPiAPI.getCurveIntensities()
        ]);

        // Update state (triggers reactive UI updates via subscriptions)
        if (statusData.temperature !== null) {
            GrowPiState.setTemperature(statusData.temperature);
        }

        if (statusData.humidity !== null) {
            GrowPiState.setHumidity(statusData.humidity);
        }

        if (statusData.lamps) {
            GrowPiState.setLampStates(statusData.lamps);

            // Update sliders
            statusData.lamps.forEach((lamp) => {
                const slider = document.getElementById(`lamp${lamp.channel}`);
                const valueEl = document.getElementById(`lamp${lamp.channel}Value`);
                if (slider && valueEl) {
                    const currentMode = GrowPiState.getMode();
                    const displayValue = (currentMode === 'auto' &&
                                         intensitiesData.success &&
                                         intensitiesData.intensities[lamp.channel] !== undefined)
                        ? intensitiesData.intensities[lamp.channel]
                        : lamp.intensity;

                    slider.value = displayValue;
                    valueEl.textContent = `${displayValue}%`;
                }
            });
        }

        GrowPiState.setOnline(true);
        GrowPiState.setLastUpdate(new Date());
        lastUpdate.textContent = `Aktualisiert: ${formatTime()}`;

    } catch (error) {
        console.error("Fetch error:", error);
        GrowPiState.setOnline(false);
    }
}
```

## Step 4: Simplify setLamp Function

### BEFORE (Lines 1204-1218):
```javascript
async function setLamp(channel, intensity) {
    try {
        await fetch(`/api/lamp/${channel}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                intensity: parseInt(intensity),
            }),
        });
    } catch (error) {
        showError(`Fehler bei Lampe ${channel}`);
    }
}
```

### AFTER:
```javascript
async function setLamp(channel, intensity) {
    try {
        await GrowPiAPI.setLamp(channel, intensity);
    } catch (error) {
        showError(`Fehler bei Lampe ${channel}`);
    }
}
```

## Step 5: Refactor fetchCurves

### BEFORE (Lines 1245-1274):
```javascript
async function fetchCurves() {
    try {
        const [curvesRes, previewRes] = await Promise.all([
            fetch("/api/curves"),
            fetch("/api/curves/preview"),
        ]);

        const curvesJson = await curvesRes.json();
        const previewJson = await previewRes.json();

        if (curvesJson.success) {
            curvesData = {};
            curvesJson.curves.forEach((c) => {
                curvesData[c.channel] = c;
            });
            renderCurves();
        }

        if (previewJson.success) {
            previewData = previewJson.preview;
            renderPreview();
        }
    } catch (error) {
        console.error("Fetch curves error:", error);
        showError("Kurven konnten nicht geladen werden");
    }
}
```

### AFTER:
```javascript
async function fetchCurves() {
    try {
        const [curvesData, previewData] = await Promise.all([
            GrowPiAPI.getCurves(),
            GrowPiAPI.getCurvePreview()
        ]);

        if (curvesData.success) {
            const curvesObj = {};
            curvesData.curves.forEach((c) => {
                curvesObj[c.channel] = c;
            });
            GrowPiState.setCurvesData(curvesObj);
            renderCurves();
        }

        if (previewData.success) {
            GrowPiState.setPreviewData(previewData.preview);
            renderPreview();
        }
    } catch (error) {
        console.error("Fetch curves error:", error);
        showError("Kurven konnten nicht geladen werden");
    }
}
```

## Step 6: Update renderCurves to Use State

### BEFORE:
```javascript
function renderCurves() {
    curvesContainer.innerHTML = "";

    Object.values(curvesData).sort((a, b) => a.channel - b.channel).forEach((curve) => {
        // ... rendering logic
    });
}
```

### AFTER:
```javascript
function renderCurves() {
    curvesContainer.innerHTML = "";

    const curvesData = GrowPiState.getCurvesData();
    Object.values(curvesData).sort((a, b) => a.channel - b.channel).forEach((curve) => {
        // ... rendering logic (same)
    });
}
```

## Step 7: Refactor Mode Management

### BEFORE (Lines 1655-1695):
```javascript
let currentMode = 'auto';

async function setMode(mode) {
    currentMode = mode;

    // Update UI
    modeAuto.classList.toggle("active", mode === "auto");
    modeManual.classList.toggle("active", mode === "manual");
    lampSection.classList.toggle("disabled", mode === "auto");

    // Save to server
    try {
        const response = await fetch("/api/mode", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ mode: mode }),
        });
        const data = await response.json();
        await fetchStatus();

        if (data.success) {
            console.log(`Mode changed to ${mode}`, data.applied_intensities || {});
        }
    } catch (e) {
        console.error("Mode save error:", e);
    }
}

async function fetchMode() {
    try {
        const res = await fetch("/api/mode");
        const data = await res.json();
        if (data.mode) {
            currentMode = data.mode;
            modeAuto.classList.toggle("active", data.mode === "auto");
            modeManual.classList.toggle("active", data.mode === "manual");
            lampSection.classList.toggle("disabled", data.mode === "auto");
        }
    } catch (e) {
        console.error("Mode fetch error:", e);
    }
}
```

### AFTER:
```javascript
// Setup mode subscription (at initialization)
GrowPiState.subscribe('currentMode', (mode) => {
    modeAuto.classList.toggle("active", mode === "auto");
    modeManual.classList.toggle("active", mode === "manual");
    lampSection.classList.toggle("disabled", mode === "auto");
});

async function setMode(mode) {
    try {
        const response = await GrowPiAPI.setMode(mode);

        if (response.success) {
            GrowPiState.setMode(mode);  // Triggers UI update via subscription
            console.log(`Mode changed to ${mode}`, response.applied_intensities || {});
            await fetchStatus();
        }
    } catch (e) {
        console.error("Mode save error:", e);
    }
}

async function fetchMode() {
    try {
        const data = await GrowPiAPI.getMode();
        if (data.mode) {
            GrowPiState.setMode(data.mode);  // Triggers UI update
        }
    } catch (e) {
        console.error("Mode fetch error:", e);
    }
}
```

## Step 8: Refactor History Chart Loading

### BEFORE (Lines 2120-2169):
```javascript
async function loadHistoryData(hours) {
    loadSystemLogs(hours);

    try {
        const [tempRes, humRes, plugRes] = await Promise.all([
            fetch(`/api/logs/sensors?type=temperature&hours=${hours}&limit=1000`),
            fetch(`/api/logs/sensors?type=humidity&hours=${hours}&limit=1000`),
            fetch(`/api/logs/plugs?hours=${hours}&limit=1000`)
        ]);

        const temps = await tempRes.json();
        const hums = await humRes.json();
        const plugs = await plugRes.json();

        if (temps.success && hums.success) {
            updateSensorChart(temps.readings, hums.readings);
        }

        const [ch1Res, ch2Res, ch3Res, ch4Res] = await Promise.all([
            fetch(`/api/logs/lamps?channel=1&hours=${hours}&limit=1000`),
            fetch(`/api/logs/lamps?channel=2&hours=${hours}&limit=1000`),
            fetch(`/api/logs/lamps?channel=3&hours=${hours}&limit=1000`),
            fetch(`/api/logs/lamps?channel=4&hours=${hours}&limit=1000`),
        ]);

        const ch1Logs = await ch1Res.json();
        const ch2Logs = await ch2Res.json();
        const ch3Logs = await ch3Res.json();
        const ch4Logs = await ch4Res.json();

        updateLampChart(ch1Logs, ch2Logs, ch3Logs, ch4Logs);

        // ... plug chart logic
    } catch (e) {
        console.error("Error loading charts:", e);
        showError("Fehler beim Laden der Diagramme");
    }
}
```

### AFTER:
```javascript
async function loadHistoryData(hours) {
    // Update state
    GrowPiState.setHistoryRange(hours);

    // Load logs independently
    loadSystemLogs(hours);

    try {
        // Use API client
        const [temps, hums, plugs] = await Promise.all([
            GrowPiAPI.getSensorLogs('temperature', hours, 1000),
            GrowPiAPI.getSensorLogs('humidity', hours, 1000),
            GrowPiAPI.getPlugLogs(hours, 1000)
        ]);

        if (temps.success && hums.success) {
            updateSensorChart(temps.readings, hums.readings);
        }

        // Parallel lamp log fetching
        const lampLogs = await Promise.all([
            GrowPiAPI.getLampLogs(1, hours, 1000),
            GrowPiAPI.getLampLogs(2, hours, 1000),
            GrowPiAPI.getLampLogs(3, hours, 1000),
            GrowPiAPI.getLampLogs(4, hours, 1000)
        ]);

        updateLampChart(...lampLogs);

        if (plugs && Array.isArray(plugs)) {
            updatePlugChart(plugs);
        } else if (plugs?.success && Array.isArray(plugs.data)) {
            updatePlugChart(plugs.data);
        }
    } catch (e) {
        console.error("Error loading charts:", e);
        showError("Fehler beim Laden der Diagramme");
    }
}
```

## Step 9: Simplify saveCurves

### BEFORE (Lines 1595-1639):
```javascript
async function saveCurves() {
    btnSaveCurves.disabled = true;
    btnSaveCurves.textContent = "Speichern...";

    try {
        for (const [ch, data] of Object.entries(curvesData)) {
            const response = await fetch(`/api/curves/${ch}`, {
                method: "PUT",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    curve: data.curve,
                    enabled: data.enabled,
                }),
            });

            if (!response.ok) {
                throw new Error(`Kanal ${ch} fehlgeschlagen`);
            }
        }

        showSuccess("Alle Kurven gespeichert!");
        fetchCurves();
    } catch (error) {
        console.error("Save error:", error);
        showError(`Speichern fehlgeschlagen: ${error.message}`);
    } finally {
        btnSaveCurves.disabled = false;
        btnSaveCurves.textContent = "Kurven Speichern";
    }
}
```

### AFTER:
```javascript
async function saveCurves() {
    btnSaveCurves.disabled = true;
    btnSaveCurves.textContent = "Speichern...";

    try {
        const curvesData = GrowPiState.getCurvesData();

        // Save all curves in parallel
        const savePromises = Object.entries(curvesData).map(([ch, data]) =>
            GrowPiAPI.updateCurve(ch, {
                curve: data.curve,
                enabled: data.enabled
            })
        );

        await Promise.all(savePromises);

        showSuccess("Alle Kurven gespeichert!");
        fetchCurves();
    } catch (error) {
        console.error("Save error:", error);
        showError(`Speichern fehlgeschlagen: ${error.message}`);
    } finally {
        btnSaveCurves.disabled = false;
        btnSaveCurves.textContent = "Kurven Speichern";
    }
}
```

## Summary of Benefits

### Code Reduction
- **Before:** ~2400 lines in index.html
- **After:** ~1800 lines + 2 modular files (api.js + state.js)

### Improvements
1. ✅ **No more global variables** - All state in `GrowPiState`
2. ✅ **No more scattered fetch calls** - All API calls via `GrowPiAPI`
3. ✅ **Reactive UI updates** - Pub/sub pattern automatically updates UI
4. ✅ **Better error handling** - Centralized in API client
5. ✅ **Easier testing** - Can test API and state independently
6. ✅ **Better debugging** - Clear stack traces, isolated modules

### Next Steps
- Extract more components (charts, curve editor, tabs)
- Add unit tests for `api.js` and `state.js`
- Consider TypeScript for type safety
- Implement WebSocket for real-time updates
