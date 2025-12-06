/**
 * Control Module - Tab 1: Steuerung
 * Handles lamp controls, status display, and mode switching
 */

import { GrowPiAPI } from '../api.js';

// ==========================================
// DOM Elements
// ==========================================
const statusBadge = document.getElementById('statusBadge');
const lastUpdate = document.getElementById('lastUpdate');
const tempValue = document.getElementById('tempValue');
const humidityValue = document.getElementById('humidityValue');
const lampSection = document.getElementById('lampSection');
const modeAuto = document.getElementById('modeAuto');
const modeManual = document.getElementById('modeManual');

// ==========================================
// State
// ==========================================
let debounceTimers = {};
let currentMode = 'auto'; // Default to auto (Zeitsteuerung)
let statusInterval = null;

// ==========================================
// Public API
// ==========================================
export function initControlTab() {
    console.log('[Control] Initializing control tab...');

    // Setup slider event listeners
    setupSliders();

    // Setup mode switch buttons
    setupModeSwitch();

    // Initial fetch
    initializeControl();

    // Auto-refresh every 10 seconds
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    statusInterval = setInterval(fetchStatus, 10000);
}

export function cleanupControlTab() {
    console.log('[Control] Cleaning up control tab...');
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

// ==========================================
// Initialization
// ==========================================
async function initializeControl() {
    // IMPORTANT: Fetch mode FIRST, then status (so currentMode is set before status display)
    await fetchMode();
    await fetchStatus();
}

// ==========================================
// Status Fetching
// ==========================================
export async function fetchStatus() {
    try {
        // Fetch status and curve intensities in parallel
        const [statusData, intensitiesData] = await Promise.all([
            GrowPiAPI.getStatus(),
            GrowPiAPI.getCurveIntensities()
        ]);

        // Update temperature
        if (statusData.temperature !== null && statusData.temperature !== undefined) {
            tempValue.innerHTML = `${statusData.temperature.toFixed(1)}<span class="temp-unit">°C</span>`;
        }

        // Update humidity
        if (statusData.humidity !== null && statusData.humidity !== undefined) {
            humidityValue.innerHTML = `${statusData.humidity.toFixed(0)}<span class="temp-unit">%</span>`;
        }

        // Update lamp displays
        if (statusData.lamps) {
            statusData.lamps.forEach((lamp) => {
                updateLampDisplay(lamp, intensitiesData?.intensities || {});
            });
        }

        updateStatusDisplay({ online: true });
        lastUpdate.textContent = `Aktualisiert: ${formatTime()}`;
    } catch (error) {
        console.error('[Control] Fetch status error:', error);
        updateStatusDisplay({ online: false });
    }
}

function updateLampDisplay(lamp, curveIntensities) {
    const slider = document.getElementById(`lamp${lamp.channel}`);
    const valueEl = document.getElementById(`lamp${lamp.channel}Value`);

    if (slider && valueEl) {
        // In auto mode, show curve intensities; in manual mode, show actual lamp values
        const displayValue = (currentMode === 'auto' && curveIntensities[lamp.channel] !== undefined)
            ? curveIntensities[lamp.channel]
            : lamp.intensity;

        slider.value = displayValue;
        valueEl.textContent = `${displayValue}%`;
    }
}

export function updateStatusDisplay(data) {
    const online = data?.online ?? false;
    statusBadge.className = `status-badge ${online ? 'status-online' : 'status-offline'}`;
    statusBadge.textContent = online ? 'Online' : 'Offline';
}

// ==========================================
// Lamp Control
// ==========================================
export async function setLamp(channel, intensity) {
    try {
        await GrowPiAPI.setLamp(channel, parseInt(intensity));
    } catch (error) {
        console.error(`[Control] Error setting lamp ${channel}:`, error);
        window.showError?.(`Fehler bei Lampe ${channel}`);
    }
}

function handleSliderChange(event) {
    const channel = event.target.dataset.channel;
    const value = event.target.value;
    const valueEl = document.getElementById(`lamp${channel}Value`);

    // Update display immediately
    if (valueEl) {
        valueEl.textContent = `${value}%`;
    }

    // Debounce API call
    debounce(
        () => setLamp(channel, value),
        300,
        `lamp${channel}`
    );
}

// ==========================================
// Mode Management
// ==========================================
async function fetchMode() {
    try {
        const data = await GrowPiAPI.getMode();
        if (data.mode) {
            currentMode = data.mode;
            updateModeSwitch(data.mode);
        }
    } catch (error) {
        console.error('[Control] Mode fetch error:', error);
    }
}

async function setMode(mode) {
    currentMode = mode;

    // Update UI immediately
    updateModeSwitch(mode);

    // Save to server
    try {
        const data = await GrowPiAPI.setMode(mode);

        // After mode change, immediately refresh status to show current lamp values
        await fetchStatus();

        if (data.success) {
            console.log(`[Control] Mode changed to ${mode}`, data.applied_intensities || {});
        }
    } catch (error) {
        console.error('[Control] Mode save error:', error);
    }
}

export function updateModeSwitch(mode = currentMode) {
    // Update button states
    modeAuto.classList.toggle('active', mode === 'auto');
    modeManual.classList.toggle('active', mode === 'manual');

    // Disable lamp section in auto mode
    lampSection.classList.toggle('disabled', mode === 'auto');
}

// ==========================================
// Event Listeners Setup
// ==========================================
function setupSliders() {
    for (let i = 1; i <= 4; i++) {
        const slider = document.getElementById(`lamp${i}`);
        if (slider) {
            slider.addEventListener('input', handleSliderChange);
        }
    }
}

function setupModeSwitch() {
    modeAuto?.addEventListener('click', () => setMode('auto'));
    modeManual?.addEventListener('click', () => setMode('manual'));
}

// ==========================================
// Utility Functions
// ==========================================
function debounce(fn, delay, key) {
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(fn, delay);
}

function formatTime() {
    return new Date().toLocaleTimeString('de-DE', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}
