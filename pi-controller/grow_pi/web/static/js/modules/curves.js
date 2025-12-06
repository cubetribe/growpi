/**
 * curves.js - Lamp Curve Editor Module
 *
 * This module handles the complete lamp curve editing functionality:
 * - Fetching and rendering curve data for all 4 channels
 * - 24h preview chart with linear interpolation
 * - Point-based curve editing (add, remove, move, modify)
 * - JSON import/export functionality
 * - Enable/disable toggle per channel
 * - Real-time local preview updates
 *
 * This is the most complex module (~450 lines) due to:
 * - Multiple channels with independent curves
 * - Curve interpolation algorithm (midnight wrap-around)
 * - JSON editor with validation
 * - Preview generation for 24h (96 bars at 15-min resolution)
 */

// ============================================================================
// MODULE STATE
// ============================================================================

let curvesData = {}; // { channel: { name, channel, enabled, curve: [{ time, intensity }], current_intensity } }
let previewData = []; // [{ time: "HH:MM", intensities: { channel: intensity } }]
let activeChannel = 1; // Currently selected channel for preview

// Channel colors matching the UI
const channelColors = {
    1: "#ff4444", // Far Red
    2: "#ffbb44", // Warm White
    3: "#88ddff", // Cool White
    4: "#cc66ff", // UV
};

// ============================================================================
// DOM REFERENCES
// ============================================================================

let curvesContainer;
let previewChart;
let btnSaveCurves;
let jsonSection;
let jsonHeader;
let jsonPreview;
let jsonTextarea;
let jsonStatus;
let btnExportJson;
let btnCopyJson;
let btnDownloadJson;
let btnImportJson;

// ============================================================================
// INITIALIZATION
// ============================================================================

/**
 * Initialize the curves tab
 * Sets up DOM references and event listeners
 */
export function initCurvesTab() {
    // Get DOM elements
    curvesContainer = document.getElementById("curvesContainer");
    previewChart = document.getElementById("previewChart");
    btnSaveCurves = document.getElementById("btnSaveCurves");
    jsonSection = document.getElementById("jsonSection");
    jsonHeader = document.getElementById("jsonHeader");
    jsonPreview = document.getElementById("jsonPreview");
    jsonTextarea = document.getElementById("jsonTextarea");
    jsonStatus = document.getElementById("jsonStatus");
    btnExportJson = document.getElementById("btnExportJson");
    btnCopyJson = document.getElementById("btnCopyJson");
    btnDownloadJson = document.getElementById("btnDownloadJson");
    btnImportJson = document.getElementById("btnImportJson");

    // Setup event listeners
    if (btnSaveCurves) {
        btnSaveCurves.addEventListener("click", saveCurves);
    }

    // JSON Editor Expand/Collapse
    if (jsonHeader) {
        jsonHeader.addEventListener("click", () => {
            jsonSection.classList.toggle("expanded");
            if (
                jsonSection.classList.contains("expanded") &&
                !jsonTextarea.value
            ) {
                btnExportJson.click();
            }
        });
    }

    // JSON Validation on input
    if (jsonTextarea) {
        jsonTextarea.addEventListener("input", validateJson);
    }

    // JSON Editor Buttons
    if (btnExportJson) {
        btnExportJson.addEventListener("click", exportJson);
    }

    if (btnCopyJson) {
        btnCopyJson.addEventListener("click", copyJson);
    }

    if (btnDownloadJson) {
        btnDownloadJson.addEventListener("click", downloadJson);
    }

    if (btnImportJson) {
        btnImportJson.addEventListener("click", importJson);
    }

    console.log("Curves module initialized");
}

// ============================================================================
// DATA FETCHING
// ============================================================================

/**
 * Fetch curve data from server
 * Loads both curve definitions and preview data
 */
export async function fetchCurves() {
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
        window.showError?.("Kurven konnten nicht geladen werden");
    }
}

// ============================================================================
// RENDERING
// ============================================================================

/**
 * Render all curve channels with their control points
 * Creates UI for each of the 4 lamp channels
 */
export function renderCurves(data) {
    if (!curvesContainer) return;

    curvesContainer.innerHTML = "";

    Object.values(curvesData)
        .sort((a, b) => a.channel - b.channel)
        .forEach((curve) => {
            const div = document.createElement("div");
            div.className = "curve-channel";
            div.innerHTML = `
                <div class="curve-header">
                    <div class="curve-name">
                        <span class="curve-dot" style="background: ${
                            channelColors[curve.channel]
                        }"></span>
                        ${curve.name}
                        <span class="current-intensity" style="color: ${
                            channelColors[curve.channel]
                        }">${curve.current_intensity}%</span>
                    </div>
                    <div class="curve-toggle ${
                        curve.enabled ? "enabled" : ""
                    }" data-channel="${curve.channel}"></div>
                </div>
                <div class="curve-points" data-channel="${curve.channel}">
                    ${curve.curve
                        .map(
                            (p, i) => `
                        <div class="curve-point">
                            <input type="text" value="${
                                p.time
                            }" data-idx="${i}" data-field="time" placeholder="HH:MM" maxlength="5" pattern="[0-9]{2}:[0-9]{2}">
                            <input type="number" min="0" max="100" value="${
                                p.intensity
                            }" data-idx="${i}" data-field="intensity" placeholder="%">
                            <div class="point-actions">
                                <button class="btn-move btn-up" data-idx="${i}" ${
                                i === 0 ? "disabled" : ""
                            }>↑</button>
                                <button class="btn-move btn-down" data-idx="${i}" ${
                                i === curve.curve.length - 1 ? "disabled" : ""
                            }>↓</button>
                                <button class="btn-remove" data-idx="${i}">×</button>
                            </div>
                        </div>
                    `
                        )
                        .join("")}
                </div>
                <button class="btn-add" data-channel="${
                    curve.channel
                }">+ Punkt hinzufügen</button>
            `;
            curvesContainer.appendChild(div);
        });

    // Setup event listeners for newly created elements
    setupCurveEventListeners();
}

/**
 * Setup all event listeners for curve editing controls
 */
function setupCurveEventListeners() {
    // Toggle enable/disable
    document.querySelectorAll(".curve-toggle").forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const ch = parseInt(toggle.dataset.channel);
            curvesData[ch].enabled = !curvesData[ch].enabled;
            toggle.classList.toggle("enabled");
        });
    });

    // Input changes (time and intensity)
    document.querySelectorAll(".curve-points input").forEach((input) => {
        input.addEventListener("change", (e) => {
            const container = e.target.closest(".curve-points");
            const ch = parseInt(container.dataset.channel);
            const idx = parseInt(e.target.dataset.idx);
            const field = e.target.dataset.field;
            let value = e.target.value;

            if (field === "intensity") {
                value = parseInt(value);
            }

            curvesData[ch].curve[idx][field] = value;
            updateLocalPreview(ch);
        });

        // Focus sets active channel for preview
        input.addEventListener("focus", (e) => {
            const container = e.target.closest(".curve-points");
            activeChannel = parseInt(container.dataset.channel);
            updateLocalPreview(activeChannel);
        });
    });

    // Remove point buttons
    document.querySelectorAll(".btn-remove").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const container = e.target.closest(".curve-points");
            const ch = parseInt(container.dataset.channel);
            const idx = parseInt(e.target.dataset.idx);
            removePoint(ch, idx);
        });
    });

    // Add point buttons
    document.querySelectorAll(".btn-add").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const ch = parseInt(e.target.dataset.channel);
            addPoint(ch);
        });
    });

    // Move up buttons
    document.querySelectorAll(".btn-up").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const container = e.target.closest(".curve-points");
            const ch = parseInt(container.dataset.channel);
            const idx = parseInt(e.target.dataset.idx);
            movePoint(ch, idx, "up");
        });
    });

    // Move down buttons
    document.querySelectorAll(".btn-down").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const container = e.target.closest(".curve-points");
            const ch = parseInt(container.dataset.channel);
            const idx = parseInt(e.target.dataset.idx);
            movePoint(ch, idx, "down");
        });
    });
}

/**
 * Render the 24h preview chart
 * Shows intensity bars for the active channel across 24 hours
 */
export function renderPreview() {
    if (!previewChart) return;

    previewChart.innerHTML = "";
    previewData.forEach((p) => {
        const intensity = p.intensities[activeChannel] || 0;
        const bar = document.createElement("div");
        bar.className = "preview-bar";
        bar.style.height = `${Math.max(intensity, 2)}%`;
        bar.style.background = `linear-gradient(to top, ${
            channelColors[activeChannel]
        }, ${channelColors[activeChannel]}44)`;
        bar.title = `${p.time}: ${intensity}%`;
        previewChart.appendChild(bar);
    });
}

/**
 * Update preview locally based on current curve edits
 * Generates 96 preview bars (15-minute resolution)
 * @param {number} channel - Channel number (1-4)
 */
export function updateLocalPreview(channel) {
    activeChannel = channel;
    const curve = curvesData[channel]?.curve || [];

    if (curve.length === 0) {
        // No curve data - fill with zeros
        previewData = Array(96)
            .fill(null)
            .map((_, i) => {
                const hour = Math.floor(i / 4);
                const min = (i % 4) * 15;
                return {
                    time: `${hour.toString().padStart(2, "0")}:${min
                        .toString()
                        .padStart(2, "0")}`,
                    intensities: { [channel]: 0 },
                };
            });
    } else {
        // Calculate interpolated values for 96 intervals (15 min each)
        previewData = Array(96)
            .fill(null)
            .map((_, i) => {
                const hour = Math.floor(i / 4);
                const min = (i % 4) * 15;
                const intensity = interpolateLocalMinutes(
                    curve,
                    hour * 60 + min
                );
                return {
                    time: `${hour.toString().padStart(2, "0")}:${min
                        .toString()
                        .padStart(2, "0")}`,
                    intensities: { [channel]: intensity },
                };
            });
    }

    renderPreview();
}

// ============================================================================
// CURVE INTERPOLATION
// ============================================================================

/**
 * Interpolate intensity for a given minute of the day
 * Uses linear interpolation between curve points
 * Handles midnight wrap-around (23:59 -> 00:00)
 *
 * @param {Array} curve - Curve points [{ time: "HH:MM", intensity: number }]
 * @param {number} currentMinutes - Minutes since midnight (0-1439)
 * @returns {number} Interpolated intensity (0-100)
 */
export function interpolateLocalMinutes(curve, currentMinutes) {
    if (!curve.length) return 0;

    // Sort curve points by time
    const sorted = [...curve].sort((a, b) => {
        const [ah, am] = a.time.split(":").map(Number);
        const [bh, bm] = b.time.split(":").map(Number);
        return ah * 60 + am - (bh * 60 + bm);
    });

    // Find surrounding points (prev and next)
    let prev = sorted[sorted.length - 1]; // Default: last point wraps to next
    let next = sorted[0];

    for (let i = 0; i < sorted.length; i++) {
        const [h, m] = sorted[i].time.split(":").map(Number);
        const mins = h * 60 + m;

        if (mins > currentMinutes) {
            next = sorted[i];
            prev = sorted[i - 1] || sorted[sorted.length - 1];
            break;
        }
    }

    // Convert times to minutes
    const [ph, pm] = prev.time.split(":").map(Number);
    const [nh, nm] = next.time.split(":").map(Number);
    let prevMins = ph * 60 + pm;
    let nextMins = nh * 60 + nm;
    let currMins = currentMinutes;

    // Handle midnight wrap-around
    if (nextMins <= prevMins) nextMins += 24 * 60;
    if (currMins < prevMins) currMins += 24 * 60;

    // If prev == next (single point), no interpolation
    if (nextMins === prevMins) {
        return prev.intensity;
    }

    // Linear interpolation
    const ratio = (currMins - prevMins) / (nextMins - prevMins);
    return Math.round(
        prev.intensity + ratio * (next.intensity - prev.intensity)
    );
}

// ============================================================================
// CURVE MODIFICATION ACTIONS
// ============================================================================

/**
 * Add a new point to a channel's curve
 * @param {number} channel - Channel number (1-4)
 */
function addPoint(channel) {
    curvesData[channel].curve.push({
        time: "12:00",
        intensity: 0,
    });
    renderCurves();
    updateLocalPreview(channel);
}

/**
 * Remove a point from a channel's curve
 * @param {number} channel - Channel number (1-4)
 * @param {number} index - Point index in curve array
 */
function removePoint(channel, index) {
    curvesData[channel].curve.splice(index, 1);
    renderCurves();
    updateLocalPreview(channel);
}

/**
 * Move a point up or down in the curve list
 * @param {number} channel - Channel number (1-4)
 * @param {number} index - Point index in curve array
 * @param {string} direction - "up" or "down"
 */
function movePoint(channel, index, direction) {
    const curve = curvesData[channel].curve;

    if (direction === "up" && index > 0) {
        // Swap with previous
        const temp = curve[index];
        curve[index] = curve[index - 1];
        curve[index - 1] = temp;
        renderCurves();
    } else if (direction === "down" && index < curve.length - 1) {
        // Swap with next
        const temp = curve[index];
        curve[index] = curve[index + 1];
        curve[index + 1] = temp;
        renderCurves();
    }
}

// ============================================================================
// SAVE FUNCTIONALITY
// ============================================================================

/**
 * Save all curves to the server
 * Sends PUT requests for each channel
 */
export async function saveCurves() {
    btnSaveCurves.disabled = true;
    btnSaveCurves.textContent = "Speichern...";

    try {
        for (const [ch, data] of Object.entries(curvesData)) {
            const response = await fetch(`/api/curves/${ch}`, {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    curve: data.curve,
                    enabled: data.enabled,
                }),
            });

            if (!response.ok) {
                throw new Error(`Kanal ${ch} fehlgeschlagen`);
            }
        }

        window.showSuccess?.("Alle Kurven gespeichert!");
        fetchCurves();
    } catch (error) {
        console.error("Save error:", error);
        window.showError?.(`Speichern fehlgeschlagen: ${error.message}`);
    } finally {
        btnSaveCurves.disabled = false;
        btnSaveCurves.textContent = "Kurven Speichern";
    }
}

// ============================================================================
// JSON EDITOR FUNCTIONALITY
// ============================================================================

/**
 * Validate JSON in the textarea
 * Updates status indicator and enables/disables import button
 * @returns {Object|null} Parsed JSON object or null if invalid
 */
function validateJson() {
    const text = jsonTextarea.value.trim();

    if (!text) {
        jsonTextarea.classList.remove("invalid");
        jsonStatus.className = "json-status";
        jsonStatus.textContent = "";
        btnImportJson.disabled = true;
        return null;
    }

    try {
        const parsed = JSON.parse(text);
        jsonTextarea.classList.remove("invalid");
        jsonStatus.className = "json-status valid";

        // Count channels
        const channels = Object.keys(parsed).length;
        jsonStatus.textContent = `✓ Gültiges JSON (${channels} Kanäle)`;
        btnImportJson.disabled = false;
        return parsed;
    } catch (e) {
        jsonTextarea.classList.add("invalid");
        jsonStatus.className = "json-status invalid";
        jsonStatus.textContent = `✗ ${e.message}`;
        btnImportJson.disabled = true;
        return null;
    }
}

/**
 * Export current curves to JSON editor
 */
function exportJson() {
    const exportData = {};
    Object.values(curvesData).forEach((c) => {
        exportData[c.name] = {
            channel: c.channel,
            enabled: c.enabled,
            curve: c.curve,
        };
    });

    jsonTextarea.value = JSON.stringify(exportData, null, 2);
    jsonPreview.textContent = `${Object.keys(exportData).length} Kanäle exportiert`;
    validateJson();
    window.showSuccess?.("Kurven exportiert!");
}

/**
 * Copy JSON to clipboard
 */
async function copyJson() {
    if (!jsonTextarea.value) {
        btnExportJson.click();
    }

    try {
        await navigator.clipboard.writeText(jsonTextarea.value);
        window.showSuccess?.("In Zwischenablage kopiert!");
    } catch (e) {
        // Fallback for older browsers
        jsonTextarea.select();
        document.execCommand("copy");
        window.showSuccess?.("Kopiert!");
    }
}

/**
 * Download JSON as file
 */
function downloadJson() {
    if (!jsonTextarea.value) {
        btnExportJson.click();
    }

    const blob = new Blob([jsonTextarea.value], {
        type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `growpi-curves-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    window.showSuccess?.("Download gestartet!");
}

/**
 * Import JSON into curves
 * Validates and merges imported data with existing curves
 */
function importJson() {
    const parsed = validateJson();
    if (!parsed) {
        window.showError?.("Ungültiges JSON");
        return;
    }

    try {
        Object.entries(parsed).forEach(([key, data]) => {
            let channel = data.channel;

            // If no channel specified, try to find by name
            if (!channel) {
                const found = Object.values(curvesData).find(
                    (c) => c.name === key
                );
                if (found) {
                    channel = found.channel;
                }
            }

            // Update curve if channel exists
            if (channel && curvesData[channel]) {
                if (data.curve) {
                    curvesData[channel].curve = data.curve;
                }
                if (data.enabled !== undefined) {
                    curvesData[channel].enabled = data.enabled;
                }
            }
        });

        renderCurves();
        window.showSuccess?.(
            'Kurven importiert! Klicke "Speichern" um zu übernehmen.'
        );
    } catch (e) {
        window.showError?.("Import fehlgeschlagen: " + e.message);
    }
}
