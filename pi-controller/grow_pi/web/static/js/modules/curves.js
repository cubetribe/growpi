/**
 * curves.js - Lamp Curve Editor Module
 *
 * This module handles the complete lamp curve editing functionality:
 * - Fetching and rendering curve data for all 4 channels
 * - 24h preview chart with linear interpolation
 * - Interactive Bezier curve editor for visual editing
 * - Point-based curve editing (add, remove, move, modify)
 * - JSON import/export functionality
 * - Enable/disable toggle per channel
 * - Real-time local preview updates
 *
 * This is the most complex module due to:
 * - Multiple channels with independent curves
 * - Curve interpolation algorithm (midnight wrap-around)
 * - Interactive Bezier curve editor integration
 * - JSON editor with validation
 * - Preview generation for 24h (96 bars at 15-min resolution)
 */

import { GrowPiAPI } from '../api.js';
import { BezierCurveEditor, createCurveEditor } from './curve-editor.js';

// ============================================================================
// MODULE STATE
// ============================================================================

let curvesData = {}; // { channel: { name, channel, enabled, curve: [{ time, intensity }], current_intensity } }
let previewData = []; // [{ time: "HH:MM", intensities: { channel: intensity } }]
let activeChannel = 1; // Currently selected channel for preview
let presetsData = []; // [{ id, name, description, curves_json, is_system, created_at }]

// Bezier curve editors for each channel
let curveEditors = {}; // { channel: BezierCurveEditor }

// Channel colors matching the UI
const channelColors = {
    1: "#ff4444", // Far Red
    2: "#ffbb44", // Warm White
    3: "#88ddff", // Cool White
    4: "#cc66ff", // UV
};

// Channel names for display
const channelNames = {
    1: "Far Red",
    2: "Warm White",
    3: "Cool White",
    4: "UV",
};

// Preview channel visibility state (loaded from localStorage)
let previewChannelVisibility = {
    1: true,
    2: true,
    3: true,
    4: true,
};

// Storage key for preview channel visibility
const PREVIEW_STORAGE_KEY = 'growpi-preview-channels';

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
    // Load preview channel visibility from localStorage
    loadPreviewChannelVisibility();

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
            // Create checkboxes first, then render
            createPreviewCheckboxes();
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
 * Creates UI for each of the 4 lamp channels with collapsible accordion
 * Now includes interactive Bezier curve editor for each channel
 */
export function renderCurves(data) {
    if (!curvesContainer) return;

    // Destroy existing editors before clearing
    Object.values(curveEditors).forEach(editor => {
        if (editor && typeof editor.destroy === 'function') {
            editor.destroy();
        }
    });
    curveEditors = {};

    curvesContainer.innerHTML = "";

    Object.values(curvesData)
        .sort((a, b) => a.channel - b.channel)
        .forEach((curve) => {
            const sectionId = `curve-channel-${curve.channel}`;
            const isCollapsed = getCurveChannelState(sectionId);

            const div = document.createElement("div");
            div.className = `curve-channel collapsible-section${isCollapsed ? ' collapsed' : ''}`;
            div.dataset.sectionId = sectionId;
            div.innerHTML = `
                <div class="collapsible-header curve-header">
                    <div class="curve-name">
                        <span class="curve-dot" style="background: ${
                            channelColors[curve.channel]
                        }"></span>
                        ${curve.name}
                        <span class="current-intensity" style="color: ${
                            channelColors[curve.channel]
                        }">${curve.current_intensity}%</span>
                    </div>
                    <div class="curve-header-actions">
                        <div class="curve-toggle ${
                            curve.enabled ? "enabled" : ""
                        }" data-channel="${curve.channel}"></div>
                        <span class="collapse-icon">&#9660;</span>
                    </div>
                </div>
                <div class="collapsible-content">
                    <!-- Interactive Bezier Curve Editor -->
                    <div class="curve-editor-mount" data-channel="${curve.channel}"></div>

                    <!-- Points Table (synchronized with editor) -->
                    <div class="curve-points-table-wrapper" style="margin-top: 12px;">
                        <div class="curve-points-table-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                            <span style="font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 0.5px;">Punkte-Tabelle</span>
                            <button class="btn-add" data-channel="${curve.channel}" style="width: auto; margin: 0; padding: 6px 12px; font-size: 12px;">+ Punkt</button>
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
                    </div>
                </div>
            `;
            curvesContainer.appendChild(div);

            // Initialize Bezier curve editor for this channel
            const editorMount = div.querySelector(`.curve-editor-mount[data-channel="${curve.channel}"]`);
            if (editorMount) {
                const editor = createCurveEditor(editorMount, curve.channel, curve.curve || []);
                if (editor) {
                    // Handle changes during drag (update preview)
                    editor.onChange((points) => {
                        curvesData[curve.channel].curve = points;
                        updateLocalPreview(curve.channel);
                    });

                    // Handle save on release (sync table)
                    editor.onSave((points) => {
                        curvesData[curve.channel].curve = points;
                        // Re-render just the points table for this channel
                        renderPointsTable(curve.channel);
                        updateLocalPreview(curve.channel);
                    });

                    curveEditors[curve.channel] = editor;
                }
            }
        });

    // Setup event listeners for newly created elements
    setupCurveEventListeners();

    // Setup accordion event listeners for curve channels
    setupCurveAccordionListeners();
}

/**
 * Render just the points table for a specific channel
 * Used when editor updates points to avoid full re-render
 * @param {number} channel - Channel number (1-4)
 */
function renderPointsTable(channel) {
    const pointsContainer = document.querySelector(`.curve-points[data-channel="${channel}"]`);
    if (!pointsContainer) return;

    const curve = curvesData[channel];
    if (!curve) return;

    pointsContainer.innerHTML = curve.curve
        .map(
            (p, i) => `
            <div class="curve-point">
                <input type="text" value="${p.time}" data-idx="${i}" data-field="time" placeholder="HH:MM" maxlength="5" pattern="[0-9]{2}:[0-9]{2}">
                <input type="number" min="0" max="100" value="${p.intensity}" data-idx="${i}" data-field="intensity" placeholder="%">
                <div class="point-actions">
                    <button class="btn-move btn-up" data-idx="${i}" ${i === 0 ? "disabled" : ""}>↑</button>
                    <button class="btn-move btn-down" data-idx="${i}" ${i === curve.curve.length - 1 ? "disabled" : ""}>↓</button>
                    <button class="btn-remove" data-idx="${i}">×</button>
                </div>
            </div>
        `
        )
        .join("");

    // Re-attach event listeners for this points container
    setupPointsEventListeners(pointsContainer, channel);
}

/**
 * Setup event listeners for a specific points container
 * @param {HTMLElement} container - Points container element
 * @param {number} channel - Channel number
 */
function setupPointsEventListeners(container, channel) {
    // Input changes (time and intensity)
    container.querySelectorAll("input").forEach((input) => {
        input.addEventListener("change", (e) => {
            const idx = parseInt(e.target.dataset.idx);
            const field = e.target.dataset.field;
            let value = e.target.value;

            if (field === "intensity") {
                value = parseInt(value);
            }

            if (!curvesData[channel]?.curve?.[idx]) {
                console.warn(`Channel ${channel} or point ${idx} not found`);
                return;
            }
            curvesData[channel].curve[idx][field] = value;

            // Update the visual editor
            if (curveEditors[channel]) {
                curveEditors[channel].setPoints(curvesData[channel].curve);
            }

            updateLocalPreview(channel);
        });

        // Focus sets active channel for preview
        input.addEventListener("focus", () => {
            activeChannel = channel;
            updateLocalPreview(channel);
        });
    });

    // Remove point buttons
    container.querySelectorAll(".btn-remove").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const idx = parseInt(e.target.dataset.idx);
            removePoint(channel, idx);
        });
    });

    // Move up buttons
    container.querySelectorAll(".btn-up").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const idx = parseInt(e.target.dataset.idx);
            movePoint(channel, idx, "up");
        });
    });

    // Move down buttons
    container.querySelectorAll(".btn-down").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            const idx = parseInt(e.target.dataset.idx);
            movePoint(channel, idx, "down");
        });
    });
}

/**
 * Setup all event listeners for curve editing controls
 * Now includes synchronization with Bezier curve editors
 */
function setupCurveEventListeners() {
    // Toggle enable/disable
    document.querySelectorAll(".curve-toggle").forEach((toggle) => {
        toggle.addEventListener("click", () => {
            const ch = parseInt(toggle.dataset.channel);
            if (!curvesData[ch]) {
                console.warn(`Channel ${ch} not found in curvesData`);
                return;
            }
            curvesData[ch].enabled = !curvesData[ch].enabled;
            toggle.classList.toggle("enabled");
        });
    });

    // Input changes (time and intensity) - with editor sync
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

            if (!curvesData[ch]?.curve?.[idx]) {
                console.warn(`Channel ${ch} or point ${idx} not found`);
                return;
            }
            curvesData[ch].curve[idx][field] = value;

            // Sync with visual editor
            if (curveEditors[ch]) {
                curveEditors[ch].setPoints(curvesData[ch].curve);
            }

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
 * Render the 24h preview chart as Multi-Line SVG
 * Shows intensity lines for all visible channels across 24 hours
 */
export function renderPreview() {
    if (!previewChart) return;

    // Calculate all channels preview data if not available
    const allChannelData = calculateAllChannelsPreview();

    // SVG dimensions
    const width = previewChart.offsetWidth || 400;
    const height = 120;
    const padding = { top: 10, right: 10, bottom: 5, left: 35 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;

    // Create SVG
    let svg = `<svg class="preview-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="xMidYMid meet">`;

    // Add gradient definitions for each channel
    svg += '<defs>';
    Object.entries(channelColors).forEach(([ch, color]) => {
        svg += `
            <linearGradient id="lineGradient${ch}" x1="0%" y1="0%" x2="0%" y2="100%">
                <stop offset="0%" style="stop-color:${color};stop-opacity:1" />
                <stop offset="100%" style="stop-color:${color};stop-opacity:0.3" />
            </linearGradient>
        `;
    });
    svg += '</defs>';

    // Draw Y-axis labels (0%, 50%, 100%)
    svg += `<text x="${padding.left - 5}" y="${padding.top + 5}" class="preview-axis-label" text-anchor="end">100%</text>`;
    svg += `<text x="${padding.left - 5}" y="${padding.top + chartHeight / 2 + 3}" class="preview-axis-label" text-anchor="end">50%</text>`;
    svg += `<text x="${padding.left - 5}" y="${padding.top + chartHeight}" class="preview-axis-label" text-anchor="end">0%</text>`;

    // Draw horizontal grid lines
    svg += `<line x1="${padding.left}" y1="${padding.top}" x2="${padding.left + chartWidth}" y2="${padding.top}" class="preview-grid-line"/>`;
    svg += `<line x1="${padding.left}" y1="${padding.top + chartHeight / 2}" x2="${padding.left + chartWidth}" y2="${padding.top + chartHeight / 2}" class="preview-grid-line"/>`;
    svg += `<line x1="${padding.left}" y1="${padding.top + chartHeight}" x2="${padding.left + chartWidth}" y2="${padding.top + chartHeight}" class="preview-grid-line"/>`;

    // Draw vertical grid lines for time markers (00:00, 06:00, 12:00, 18:00, 24:00)
    for (let i = 0; i <= 4; i++) {
        const x = padding.left + (chartWidth * i) / 4;
        svg += `<line x1="${x}" y1="${padding.top}" x2="${x}" y2="${padding.top + chartHeight}" class="preview-grid-line"/>`;
    }

    // Draw lines for each visible channel
    [1, 2, 3, 4].forEach((channel) => {
        if (!previewChannelVisibility[channel]) return;

        const color = channelColors[channel];
        const points = allChannelData.map((p, i) => {
            const x = padding.left + (i / (allChannelData.length - 1)) * chartWidth;
            const intensity = p.intensities[channel] || 0;
            const y = padding.top + chartHeight - (intensity / 100) * chartHeight;
            return `${x},${y}`;
        }).join(' ');

        // Draw filled area under the line (optional, adds depth)
        const firstPoint = `${padding.left},${padding.top + chartHeight}`;
        const lastPoint = `${padding.left + chartWidth},${padding.top + chartHeight}`;
        svg += `<polygon points="${firstPoint} ${points} ${lastPoint}" fill="url(#lineGradient${channel})" opacity="0.15"/>`;

        // Draw the line
        svg += `<polyline points="${points}" class="preview-line" style="stroke: ${color};" data-channel="${channel}"/>`;
    });

    svg += '</svg>';

    previewChart.innerHTML = svg;
}

/**
 * Calculate preview data for all channels
 * Used by the multi-line preview chart
 * @returns {Array} Array of { time, intensities: { channel: intensity } }
 */
function calculateAllChannelsPreview() {
    const result = [];

    for (let i = 0; i < 96; i++) {
        const hour = Math.floor(i / 4);
        const min = (i % 4) * 15;
        const time = `${hour.toString().padStart(2, "0")}:${min.toString().padStart(2, "0")}`;
        const intensities = {};

        [1, 2, 3, 4].forEach((channel) => {
            const curve = curvesData[channel]?.curve || [];
            if (curve.length === 0) {
                intensities[channel] = 0;
            } else {
                intensities[channel] = interpolateLocalMinutes(curve, hour * 60 + min);
            }
        });

        result.push({ time, intensities });
    }

    return result;
}

/**
 * Load preview channel visibility from localStorage
 */
function loadPreviewChannelVisibility() {
    try {
        const stored = localStorage.getItem(PREVIEW_STORAGE_KEY);
        if (stored) {
            const parsed = JSON.parse(stored);
            previewChannelVisibility = { ...previewChannelVisibility, ...parsed };
        }
    } catch (e) {
        console.warn('Failed to load preview channel visibility:', e);
    }
}

/**
 * Save preview channel visibility to localStorage
 */
function savePreviewChannelVisibility() {
    try {
        localStorage.setItem(PREVIEW_STORAGE_KEY, JSON.stringify(previewChannelVisibility));
    } catch (e) {
        console.warn('Failed to save preview channel visibility:', e);
    }
}

/**
 * Toggle visibility of a channel in the preview chart
 * @param {number} channel - Channel number (1-4)
 */
function togglePreviewChannel(channel) {
    previewChannelVisibility[channel] = !previewChannelVisibility[channel];
    savePreviewChannelVisibility();
    renderPreview();
}

/**
 * Create the channel visibility checkboxes above the preview chart
 * Called once during initialization
 */
function createPreviewCheckboxes() {
    const previewSection = document.querySelector('.preview-section');
    if (!previewSection) return;

    // Check if checkboxes already exist
    if (document.getElementById('previewChannelCheckboxes')) return;

    const checkboxContainer = document.createElement('div');
    checkboxContainer.id = 'previewChannelCheckboxes';
    checkboxContainer.className = 'preview-channel-checkboxes';

    [1, 2, 3, 4].forEach((channel) => {
        const label = document.createElement('label');
        label.className = 'preview-channel-checkbox';
        label.innerHTML = `
            <input type="checkbox" data-channel="${channel}" ${previewChannelVisibility[channel] ? 'checked' : ''}>
            <span class="preview-channel-dot" style="background: ${channelColors[channel]}"></span>
            <span class="preview-channel-name">${channelNames[channel]}</span>
        `;
        checkboxContainer.appendChild(label);
    });

    // Insert before the preview-title
    const previewTitle = previewSection.querySelector('.preview-title');
    if (previewTitle) {
        previewSection.insertBefore(checkboxContainer, previewTitle);
    } else {
        previewSection.insertBefore(checkboxContainer, previewSection.firstChild);
    }

    // Setup event listeners
    checkboxContainer.querySelectorAll('input[type="checkbox"]').forEach((checkbox) => {
        checkbox.addEventListener('change', (e) => {
            const channel = parseInt(e.target.dataset.channel);
            togglePreviewChannel(channel);
        });
    });
}

/**
 * Update preview locally based on current curve edits
 * Generates multi-line preview chart for all channels
 * @param {number} channel - Channel number that was edited (1-4)
 */
export function updateLocalPreview(channel) {
    activeChannel = channel;

    // Ensure checkboxes are created
    createPreviewCheckboxes();

    // Simply re-render the preview - calculateAllChannelsPreview will recalculate all channels
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
            // Update local curves data from response OR re-fetch
            if (response.curves && response.curves.length > 0) {
                curvesData = {};
                response.curves.forEach((c) => {
                    curvesData[c.channel] = c;
                });
                renderCurves();
                updateLocalPreview(activeChannel);
            } else {
                // Fallback: Re-fetch curves from server if not in response
                await fetchCurves();
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

// ============================================================================
// CURVE CHANNEL ACCORDION FUNCTIONALITY
// ============================================================================

// Storage key prefix for curve channel accordion state
const CURVE_STORAGE_PREFIX = 'growpi-curve-';

/**
 * Get the collapsed state for a curve channel from localStorage
 * @param {string} sectionId - The section identifier (e.g., "curve-channel-1")
 * @returns {boolean} - True if collapsed, false if expanded
 */
function getCurveChannelState(sectionId) {
    const stored = localStorage.getItem(CURVE_STORAGE_PREFIX + sectionId);
    // Default: ALL channels are COLLAPSED (closed) - user must click to expand
    return stored !== 'expanded';
}

/**
 * Save the collapsed state for a curve channel to localStorage
 * @param {string} sectionId - The section identifier
 * @param {boolean} isCollapsed - Whether the section is collapsed
 */
function saveCurveChannelState(sectionId, isCollapsed) {
    if (isCollapsed) {
        localStorage.removeItem(CURVE_STORAGE_PREFIX + sectionId);
    } else {
        localStorage.setItem(CURVE_STORAGE_PREFIX + sectionId, 'expanded');
    }
}

/**
 * Toggle a curve channel's collapsed state
 * @param {HTMLElement} section - The section element
 */
function toggleCurveChannel(section) {
    const sectionId = section.dataset.sectionId;
    const isCurrentlyCollapsed = section.classList.contains('collapsed');

    if (isCurrentlyCollapsed) {
        // Expand
        section.classList.remove('collapsed');
        saveCurveChannelState(sectionId, false);
    } else {
        // Collapse
        section.classList.add('collapsed');
        saveCurveChannelState(sectionId, true);
    }

    // Update ARIA attribute
    const header = section.querySelector('.collapsible-header');
    if (header) {
        header.setAttribute('aria-expanded', !section.classList.contains('collapsed'));
    }
}

/**
 * Setup accordion event listeners for curve channels
 * Called after renderCurves() to attach click handlers
 */
function setupCurveAccordionListeners() {
    const curveSections = document.querySelectorAll('.curve-channel.collapsible-section');

    curveSections.forEach(section => {
        const header = section.querySelector('.collapsible-header');
        if (!header) return;

        // Set initial ARIA state
        header.setAttribute('role', 'button');
        header.setAttribute('tabindex', '0');
        header.setAttribute('aria-expanded', !section.classList.contains('collapsed'));

        // Click handler - but only on header, not on toggle switch
        header.addEventListener('click', (e) => {
            // Don't toggle if clicking on the enable/disable toggle
            if (e.target.closest('.curve-toggle')) {
                return;
            }
            e.preventDefault();
            toggleCurveChannel(section);
        });

        // Keyboard accessibility
        header.addEventListener('keydown', (e) => {
            if ((e.key === 'Enter' || e.key === ' ') && !e.target.closest('.curve-toggle')) {
                e.preventDefault();
                toggleCurveChannel(section);
            }
        });
    });

    console.log(`Curve accordion: Initialized ${curveSections.length} collapsible channels`);
}
