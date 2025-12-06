/**
 * Environment Module - Room Climate Control
 * Handles dehumidifier control, room temperature/humidity monitoring
 * and automated environment management
 *
 * Part of GrowPi v6.4 - Extracted from monolithic index.html (2894 LOC)
 * @module environment
 */

import { GrowPiAPI } from '../api.js';

// ==========================================
// DOM Elements
// ==========================================
const roomTempValue = document.getElementById('roomTempValue');
const roomHumidityValue = document.getElementById('roomHumidityValue');
const dehumidifierStatus = document.getElementById('dehumidifierStatus');
const dehumidifierOn = document.getElementById('dehumidifierOn');
const dehumidifierOff = document.getElementById('dehumidifierOff');
const dehumidifierAutoToggle = document.getElementById('dehumidifierAutoToggle');
const targetHumidity = document.getElementById('targetHumidity');
const thresholdHigh = document.getElementById('thresholdHigh');
const thresholdLow = document.getElementById('thresholdLow');
const btnSaveRoomConfig = document.getElementById('btnSaveRoomConfig');

// ==========================================
// State
// ==========================================
let statusInterval = null;

// ==========================================
// Public API
// ==========================================
export function initEnvironmentTab() {
    console.log('[Environment] Initializing environment tab...');

    // Setup event listeners
    setupEventListeners();

    // Initial fetch
    fetchRoomStatus();

    // Auto-refresh every 10 seconds
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    statusInterval = setInterval(fetchRoomStatus, 10000);
}

export function cleanupEnvironmentTab() {
    console.log('[Environment] Cleaning up environment tab...');
    if (statusInterval) {
        clearInterval(statusInterval);
        statusInterval = null;
    }
}

// ==========================================
// Room Status Fetching
// ==========================================
export async function fetchRoomStatus() {
    try {
        const data = await GrowPiAPI.getRoomStatus();

        if (data.success) {
            // Update temperature
            if (data.temperature !== null && data.temperature !== undefined) {
                roomTempValue.innerHTML = `${data.temperature.toFixed(1)}<span class="temp-unit">°C</span>`;
            }

            // Update humidity
            if (data.humidity !== null && data.humidity !== undefined) {
                roomHumidityValue.innerHTML = `${data.humidity.toFixed(0)}<span class="temp-unit">%</span>`;
            }

            // Update dehumidifier status
            if (data.dehumidifier && data.dehumidifier.config) {
                updateDehumidifierDisplay(data.dehumidifier);
            }
        }
    } catch (error) {
        console.error('[Environment] Room fetch error:', error);
    }
}

function updateDehumidifierDisplay(dehumidifier) {
    const isOn = dehumidifier.is_on;

    // Update status display
    dehumidifierStatus.textContent = isOn ? 'AN' : 'AUS';
    dehumidifierStatus.style.color = isOn ? '#11ff55' : '#888';

    // Update button states
    dehumidifierOn.classList.toggle('active', isOn);
    dehumidifierOff.classList.toggle('active', !isOn);

    // Update auto toggle
    const autoEnabled = dehumidifier.config.enabled;
    dehumidifierAutoToggle.classList.toggle('enabled', autoEnabled);

    // Disable manual buttons when auto mode is enabled
    const buttonsDisabled = autoEnabled;
    dehumidifierOn.disabled = buttonsDisabled;
    dehumidifierOff.disabled = buttonsDisabled;
    dehumidifierOn.style.opacity = buttonsDisabled ? '0.5' : '1';
    dehumidifierOff.style.opacity = buttonsDisabled ? '0.5' : '1';
    dehumidifierOn.style.pointerEvents = buttonsDisabled ? 'none' : 'auto';
    dehumidifierOff.style.pointerEvents = buttonsDisabled ? 'none' : 'auto';

    // Update config input values
    targetHumidity.value = dehumidifier.config.target;
    thresholdHigh.value = dehumidifier.config.threshold_high;
    thresholdLow.value = dehumidifier.config.threshold_low;
}

// ==========================================
// Dehumidifier Control
// ==========================================
export async function controlDehumidifier(action) {
    try {
        const data = await GrowPiAPI.controlDehumidifier(action);

        if (data.success) {
            window.showSuccess?.(`Entfeuchter ${action === 'on' ? 'AN' : 'AUS'}`);
            await fetchRoomStatus();
        } else {
            window.showError?.(data.error || 'Fehler');
        }
    } catch (error) {
        console.error('[Environment] Dehumidifier control error:', error);
        window.showError?.('Verbindungsfehler');
    }
}

export async function saveRoomConfig() {
    try {
        const config = {
            enabled: dehumidifierAutoToggle.classList.contains('enabled'),
            target: parseFloat(targetHumidity.value),
            threshold_high: parseFloat(thresholdHigh.value),
            threshold_low: parseFloat(thresholdLow.value)
        };

        const data = await GrowPiAPI.saveRoomConfig(config);

        if (data.success) {
            window.showSuccess?.('Einstellungen gespeichert!');
            // Refresh status to show new state (especially after auto-control kick-in)
            setTimeout(fetchRoomStatus, 500);
        } else {
            window.showError?.(data.error || 'Fehler beim Speichern');
        }
    } catch (error) {
        console.error('[Environment] Config save error:', error);
        window.showError?.('Verbindungsfehler');
    }
}

// ==========================================
// Event Listeners Setup
// ==========================================
function setupEventListeners() {
    // Dehumidifier manual control
    dehumidifierOn?.addEventListener('click', () => controlDehumidifier('on'));
    dehumidifierOff?.addEventListener('click', () => controlDehumidifier('off'));

    // Auto toggle
    dehumidifierAutoToggle?.addEventListener('click', () => {
        dehumidifierAutoToggle.classList.toggle('enabled');
    });

    // Save configuration
    btnSaveRoomConfig?.addEventListener('click', saveRoomConfig);
}
