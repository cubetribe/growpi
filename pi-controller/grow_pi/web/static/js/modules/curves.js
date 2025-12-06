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

import { GrowPiAPI } from '../api.js';

// ============================================================================
// MODULE STATE
// ============================================================================

let curvesData = {}; // { channel: { name, channel, enabled, curve: [{ time, intensity }], current_intensity } }
let previewData = []; // [{ time: "HH:MM", intensities: { channel: intensity } }]
let activeChannel = 1; // Currently selected channel for preview
let presetsData = []; // [{ id, name, description, curves_json, is_system, created_at }]

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

// Preset DOM references
let presetControls;
let presetSelect;
let btnApplyPreset;
let btnSavePreset;
let btnManagePresets;
let savePresetModal;
let managePresetsModal;

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

    // Initialize preset controls
    initPresetControls();

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
        // Use GrowPiAPI instead of direct fetch()
        const [curvesJson, previewJson] = await Promise.all([
            GrowPiAPI.getCurves(),
            GrowPiAPI.getCurvePreview(),
        ]);

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
        // Use GrowPiAPI instead of direct fetch()
        for (const [ch, data] of Object.entries(curvesData)) {
            const response = await GrowPiAPI.updateCurve(ch, {
                curve: data.curve,
                enabled: data.enabled,
            });

            if (!response.success) {
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

// ============================================================================
// PRESET FUNCTIONALITY
// ============================================================================

/**
 * Initialize preset controls - creates UI elements and sets up event handlers
 */
function initPresetControls() {
    // Find or create preset controls container
    const curvesTab = document.getElementById("tab-curves");
    if (!curvesTab) return;

    // Create preset controls HTML
    const presetControlsHTML = `
        <div class="preset-controls" id="presetControls">
            <div class="preset-header">
                <span class="preset-label">Presets:</span>
                <select id="presetSelect" class="preset-select">
                    <option value="">-- Preset wählen --</option>
                </select>
                <button class="btn-preset" id="btnApplyPreset" disabled>Anwenden</button>
                <button class="btn-preset btn-preset-primary" id="btnSavePreset">Speichern als...</button>
                <button class="btn-preset" id="btnManagePresets">Verwalten</button>
            </div>
        </div>
    `;

    // Create save preset modal
    const saveModalHTML = `
        <div class="modal-overlay" id="savePresetModal" style="display: none;">
            <div class="modal-content">
                <div class="modal-header">
                    <h3>Preset speichern</h3>
                    <button class="modal-close" id="closeSaveModal">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="form-group">
                        <label for="presetName">Name:</label>
                        <input type="text" id="presetName" class="form-input" placeholder="z.B. Meine Konfiguration" maxlength="50">
                    </div>
                    <div class="form-group">
                        <label for="presetDescription">Beschreibung (optional):</label>
                        <textarea id="presetDescription" class="form-textarea" placeholder="Beschreibung des Presets..." rows="3"></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-modal btn-cancel" id="cancelSavePreset">Abbrechen</button>
                    <button class="btn-modal btn-primary" id="confirmSavePreset">Speichern</button>
                </div>
            </div>
        </div>
    `;

    // Create manage presets modal
    const manageModalHTML = `
        <div class="modal-overlay" id="managePresetsModal" style="display: none;">
            <div class="modal-content modal-wide">
                <div class="modal-header">
                    <h3>Presets verwalten</h3>
                    <button class="modal-close" id="closeManageModal">&times;</button>
                </div>
                <div class="modal-body">
                    <div id="presetsListContainer" class="presets-list">
                        <p class="loading-text">Lade Presets...</p>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn-modal" id="closeManagePresets">Schließen</button>
                </div>
            </div>
        </div>
    `;

    // Insert preset controls before preview section
    const previewSection = curvesTab.querySelector(".preview-section");
    if (previewSection) {
        previewSection.insertAdjacentHTML("beforebegin", presetControlsHTML);
    }

    // Add modals to body
    document.body.insertAdjacentHTML("beforeend", saveModalHTML);
    document.body.insertAdjacentHTML("beforeend", manageModalHTML);

    // Get DOM references
    presetControls = document.getElementById("presetControls");
    presetSelect = document.getElementById("presetSelect");
    btnApplyPreset = document.getElementById("btnApplyPreset");
    btnSavePreset = document.getElementById("btnSavePreset");
    btnManagePresets = document.getElementById("btnManagePresets");
    savePresetModal = document.getElementById("savePresetModal");
    managePresetsModal = document.getElementById("managePresetsModal");

    // Setup event listeners
    if (presetSelect) {
        presetSelect.addEventListener("change", () => {
            btnApplyPreset.disabled = !presetSelect.value;
        });
    }

    if (btnApplyPreset) {
        btnApplyPreset.addEventListener("click", applySelectedPreset);
    }

    if (btnSavePreset) {
        btnSavePreset.addEventListener("click", () => showSavePresetModal());
    }

    if (btnManagePresets) {
        btnManagePresets.addEventListener("click", () => showManagePresetsModal());
    }

    // Save modal events
    document.getElementById("closeSaveModal")?.addEventListener("click", closeSavePresetModal);
    document.getElementById("cancelSavePreset")?.addEventListener("click", closeSavePresetModal);
    document.getElementById("confirmSavePreset")?.addEventListener("click", saveNewPreset);

    // Manage modal events
    document.getElementById("closeManageModal")?.addEventListener("click", closeManagePresetsModal);
    document.getElementById("closeManagePresets")?.addEventListener("click", closeManagePresetsModal);

    // Close modals on overlay click
    savePresetModal?.addEventListener("click", (e) => {
        if (e.target === savePresetModal) closeSavePresetModal();
    });
    managePresetsModal?.addEventListener("click", (e) => {
        if (e.target === managePresetsModal) closeManagePresetsModal();
    });

    // Load presets on init
    fetchPresets();
}

/**
 * Fetch presets from server
 */
async function fetchPresets() {
    try {
        const response = await GrowPiAPI.getCurvePresets();
        if (response.success) {
            presetsData = response.presets || [];
            renderPresetSelect();
        }
    } catch (error) {
        console.error("Fetch presets error:", error);
    }
}

/**
 * Render preset dropdown options
 */
function renderPresetSelect() {
    if (!presetSelect) return;

    // Clear existing options except default
    presetSelect.innerHTML = '<option value="">-- Preset wählen --</option>';

    // Add system presets first
    const systemPresets = presetsData.filter(p => p.is_system);
    const userPresets = presetsData.filter(p => !p.is_system);

    if (systemPresets.length > 0) {
        const systemGroup = document.createElement("optgroup");
        systemGroup.label = "System Presets";
        systemPresets.forEach(p => {
            const option = document.createElement("option");
            option.value = p.id;
            option.textContent = p.name;
            option.title = p.description || "";
            systemGroup.appendChild(option);
        });
        presetSelect.appendChild(systemGroup);
    }

    if (userPresets.length > 0) {
        const userGroup = document.createElement("optgroup");
        userGroup.label = "Eigene Presets";
        userPresets.forEach(p => {
            const option = document.createElement("option");
            option.value = p.id;
            option.textContent = p.name;
            option.title = p.description || "";
            userGroup.appendChild(option);
        });
        presetSelect.appendChild(userGroup);
    }

    btnApplyPreset.disabled = true;
}

/**
 * Apply selected preset to curves
 */
async function applySelectedPreset() {
    const presetId = parseInt(presetSelect.value);
    if (!presetId) return;

    btnApplyPreset.disabled = true;
    btnApplyPreset.textContent = "Anwenden...";

    try {
        const response = await GrowPiAPI.applyCurvePreset(presetId);
        if (response.success) {
            // Update local curves data
            if (response.curves) {
                curvesData = {};
                response.curves.forEach((c) => {
                    curvesData[c.channel] = c;
                });
                renderCurves();
            }
            window.showSuccess?.(`Preset "${response.preset?.name}" angewendet!`);
        } else {
            throw new Error(response.error || "Fehler beim Anwenden");
        }
    } catch (error) {
        console.error("Apply preset error:", error);
        window.showError?.(`Preset konnte nicht angewendet werden: ${error.message}`);
    } finally {
        btnApplyPreset.disabled = false;
        btnApplyPreset.textContent = "Anwenden";
        presetSelect.value = "";
    }
}

/**
 * Show save preset modal
 */
function showSavePresetModal() {
    if (!savePresetModal) return;
    document.getElementById("presetName").value = "";
    document.getElementById("presetDescription").value = "";
    savePresetModal.style.display = "flex";
    document.getElementById("presetName").focus();
}

/**
 * Close save preset modal
 */
function closeSavePresetModal() {
    if (savePresetModal) {
        savePresetModal.style.display = "none";
    }
}

/**
 * Save a new preset with current curves
 */
async function saveNewPreset() {
    const nameInput = document.getElementById("presetName");
    const descInput = document.getElementById("presetDescription");
    const name = nameInput.value.trim();
    const description = descInput.value.trim();

    if (!name) {
        window.showError?.("Bitte geben Sie einen Namen ein");
        nameInput.focus();
        return;
    }

    const confirmBtn = document.getElementById("confirmSavePreset");
    confirmBtn.disabled = true;
    confirmBtn.textContent = "Speichern...";

    try {
        const response = await GrowPiAPI.createCurvePreset(name, description);
        if (response.success) {
            window.showSuccess?.(`Preset "${name}" erstellt!`);
            closeSavePresetModal();
            await fetchPresets();
        } else {
            throw new Error(response.error || "Fehler beim Erstellen");
        }
    } catch (error) {
        console.error("Create preset error:", error);
        window.showError?.(`Preset konnte nicht erstellt werden: ${error.message}`);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = "Speichern";
    }
}

/**
 * Show manage presets modal
 */
async function showManagePresetsModal() {
    if (!managePresetsModal) return;
    managePresetsModal.style.display = "flex";
    await renderPresetsList();
}

/**
 * Close manage presets modal
 */
function closeManagePresetsModal() {
    if (managePresetsModal) {
        managePresetsModal.style.display = "none";
    }
}

/**
 * Render presets list in manage modal
 */
async function renderPresetsList() {
    const container = document.getElementById("presetsListContainer");
    if (!container) return;

    // Refresh presets data
    await fetchPresets();

    if (presetsData.length === 0) {
        container.innerHTML = '<p class="empty-text">Keine Presets vorhanden</p>';
        return;
    }

    let html = '<table class="presets-table"><thead><tr><th>Name</th><th>Beschreibung</th><th>Typ</th><th>Aktionen</th></tr></thead><tbody>';

    presetsData.forEach(preset => {
        const isSystem = preset.is_system;
        html += `
            <tr data-preset-id="${preset.id}">
                <td>
                    <span class="preset-name-display">${escapeHtml(preset.name)}</span>
                    <input type="text" class="preset-name-edit form-input" value="${escapeHtml(preset.name)}" style="display: none;" maxlength="50">
                </td>
                <td>
                    <span class="preset-desc-display">${escapeHtml(preset.description || "-")}</span>
                    <textarea class="preset-desc-edit form-textarea" style="display: none;" rows="2">${escapeHtml(preset.description || "")}</textarea>
                </td>
                <td><span class="preset-type ${isSystem ? "system" : "user"}">${isSystem ? "System" : "Eigene"}</span></td>
                <td class="preset-actions">
                    ${!isSystem ? `
                        <button class="btn-preset-action btn-edit" data-id="${preset.id}" title="Bearbeiten">Bearbeiten</button>
                        <button class="btn-preset-action btn-save-edit" data-id="${preset.id}" style="display: none;" title="Speichern">OK</button>
                        <button class="btn-preset-action btn-cancel-edit" data-id="${preset.id}" style="display: none;" title="Abbrechen">X</button>
                        <button class="btn-preset-action btn-delete" data-id="${preset.id}" title="Löschen">Löschen</button>
                    ` : '<span class="system-hint">Geschützt</span>'}
                </td>
            </tr>
        `;
    });

    html += '</tbody></table>';
    container.innerHTML = html;

    // Setup event listeners for table actions
    setupPresetTableListeners();
}

/**
 * Setup event listeners for preset table actions
 */
function setupPresetTableListeners() {
    const container = document.getElementById("presetsListContainer");
    if (!container) return;

    // Edit buttons
    container.querySelectorAll(".btn-edit").forEach(btn => {
        btn.addEventListener("click", () => {
            const row = btn.closest("tr");
            enterEditMode(row);
        });
    });

    // Save edit buttons
    container.querySelectorAll(".btn-save-edit").forEach(btn => {
        btn.addEventListener("click", async () => {
            const row = btn.closest("tr");
            await savePresetEdit(row);
        });
    });

    // Cancel edit buttons
    container.querySelectorAll(".btn-cancel-edit").forEach(btn => {
        btn.addEventListener("click", () => {
            const row = btn.closest("tr");
            exitEditMode(row);
        });
    });

    // Delete buttons
    container.querySelectorAll(".btn-delete").forEach(btn => {
        btn.addEventListener("click", async () => {
            const presetId = parseInt(btn.dataset.id);
            await deletePreset(presetId);
        });
    });
}

/**
 * Enter edit mode for a preset row
 */
function enterEditMode(row) {
    row.querySelector(".preset-name-display").style.display = "none";
    row.querySelector(".preset-name-edit").style.display = "block";
    row.querySelector(".preset-desc-display").style.display = "none";
    row.querySelector(".preset-desc-edit").style.display = "block";
    row.querySelector(".btn-edit").style.display = "none";
    row.querySelector(".btn-save-edit").style.display = "inline-block";
    row.querySelector(".btn-cancel-edit").style.display = "inline-block";
    row.querySelector(".btn-delete").style.display = "none";
}

/**
 * Exit edit mode for a preset row
 */
function exitEditMode(row) {
    const preset = presetsData.find(p => p.id === parseInt(row.dataset.presetId));
    if (preset) {
        row.querySelector(".preset-name-edit").value = preset.name;
        row.querySelector(".preset-desc-edit").value = preset.description || "";
    }
    row.querySelector(".preset-name-display").style.display = "inline";
    row.querySelector(".preset-name-edit").style.display = "none";
    row.querySelector(".preset-desc-display").style.display = "inline";
    row.querySelector(".preset-desc-edit").style.display = "none";
    row.querySelector(".btn-edit").style.display = "inline-block";
    row.querySelector(".btn-save-edit").style.display = "none";
    row.querySelector(".btn-cancel-edit").style.display = "none";
    row.querySelector(".btn-delete").style.display = "inline-block";
}

/**
 * Save preset edit
 */
async function savePresetEdit(row) {
    const presetId = parseInt(row.dataset.presetId);
    const newName = row.querySelector(".preset-name-edit").value.trim();
    const newDesc = row.querySelector(".preset-desc-edit").value.trim();

    if (!newName) {
        window.showError?.("Name darf nicht leer sein");
        return;
    }

    try {
        const response = await GrowPiAPI.updateCurvePreset(presetId, {
            name: newName,
            description: newDesc
        });

        if (response.success) {
            window.showSuccess?.("Preset aktualisiert!");
            await renderPresetsList();
        } else {
            throw new Error(response.error || "Fehler beim Aktualisieren");
        }
    } catch (error) {
        console.error("Update preset error:", error);
        window.showError?.(`Aktualisierung fehlgeschlagen: ${error.message}`);
    }
}

/**
 * Delete a preset
 */
async function deletePreset(presetId) {
    const preset = presetsData.find(p => p.id === presetId);
    if (!preset) return;

    if (!confirm(`Preset "${preset.name}" wirklich löschen?`)) {
        return;
    }

    try {
        const response = await GrowPiAPI.deleteCurvePreset(presetId);
        if (response.success) {
            window.showSuccess?.(`Preset "${preset.name}" gelöscht!`);
            await renderPresetsList();
        } else {
            throw new Error(response.error || "Fehler beim Löschen");
        }
    } catch (error) {
        console.error("Delete preset error:", error);
        window.showError?.(`Löschen fehlgeschlagen: ${error.message}`);
    }
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}
