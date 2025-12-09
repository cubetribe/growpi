/**
 * Environment Module - Room Climate Control
 * Handles dehumidifier control, room temperature/humidity monitoring
 * and automated environment management with time-based scheduling
 *
 * Part of GrowPi v6.8 - Added time-based scheduling (Feature #2)
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

// Time Schedule DOM Elements (Feature #2)
const timeScheduleToggle = document.getElementById('timeScheduleToggle');
const scheduleList = document.getElementById('scheduleList');
const scheduleStartTime = document.getElementById('scheduleStartTime');
const scheduleEndTime = document.getElementById('scheduleEndTime');
const scheduleTargetState = document.getElementById('scheduleTargetState');
const btnAddSchedule = document.getElementById('btnAddSchedule');
const activeScheduleInfo = document.getElementById('activeScheduleInfo');

// ==========================================
// State
// ==========================================
let statusInterval = null;
let schedules = [];
let timeScheduleEnabled = false;

// Track if user is currently editing input fields to prevent polling overwrites
// FIX: Race-condition zwischen User-Input und Auto-Refresh (v6.16.0 Bugfix)
let isUserEditing = {
    targetHumidity: false,
    thresholdHigh: false,
    thresholdLow: false
};

// ==========================================
// Public API
// ==========================================
export function initEnvironmentTab() {
    console.log('[Environment] Initializing environment tab...');

    // Setup event listeners
    setupEventListeners();

    // Initial fetch
    fetchRoomStatus();
    fetchSchedules();

    // Auto-refresh every 10 seconds
    if (statusInterval) {
        clearInterval(statusInterval);
    }
    statusInterval = setInterval(() => {
        fetchRoomStatus();
        fetchSchedules();
    }, 10000);
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
            if (roomTempValue && data.temperature !== null && data.temperature !== undefined) {
                roomTempValue.innerHTML = `${data.temperature.toFixed(1)}<span class="temp-unit">C</span>`;
            }

            // Update humidity
            if (roomHumidityValue && data.humidity !== null && data.humidity !== undefined) {
                roomHumidityValue.innerHTML = `${data.humidity.toFixed(1)}<span class="temp-unit">%</span>`;
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
    if (dehumidifierStatus) {
        dehumidifierStatus.textContent = isOn ? 'AN' : 'AUS';
        dehumidifierStatus.style.color = isOn ? '#11ff55' : '#888';
    }

    // Update button states
    if (dehumidifierOn) dehumidifierOn.classList.toggle('active', isOn);
    if (dehumidifierOff) dehumidifierOff.classList.toggle('active', !isOn);

    // Update auto toggle
    const autoEnabled = dehumidifier.config.enabled;
    if (dehumidifierAutoToggle) {
        dehumidifierAutoToggle.classList.toggle('enabled', autoEnabled);
    }

    // Disable manual buttons when auto mode is enabled
    const buttonsDisabled = autoEnabled;
    if (dehumidifierOn) {
        dehumidifierOn.disabled = buttonsDisabled;
        dehumidifierOn.style.opacity = buttonsDisabled ? '0.5' : '1';
        dehumidifierOn.style.pointerEvents = buttonsDisabled ? 'none' : 'auto';
    }
    if (dehumidifierOff) {
        dehumidifierOff.disabled = buttonsDisabled;
        dehumidifierOff.style.opacity = buttonsDisabled ? '0.5' : '1';
        dehumidifierOff.style.pointerEvents = buttonsDisabled ? 'none' : 'auto';
    }

    // Update config input values - ONLY if user is NOT currently editing them
    // FIX: Prevent polling from overwriting user input (v6.16.0 Bugfix)
    if (targetHumidity && !isUserEditing.targetHumidity) {
        targetHumidity.value = dehumidifier.config.target;
    }
    if (thresholdHigh && !isUserEditing.thresholdHigh) {
        thresholdHigh.value = dehumidifier.config.threshold_high;
    }
    if (thresholdLow && !isUserEditing.thresholdLow) {
        thresholdLow.value = dehumidifier.config.threshold_low;
    }

    // Update time schedule toggle (Feature #2)
    timeScheduleEnabled = dehumidifier.config.time_schedule_enabled || false;
    if (timeScheduleToggle) {
        timeScheduleToggle.classList.toggle('enabled', timeScheduleEnabled);
    }

    // Update active schedule display
    if (activeScheduleInfo && dehumidifier.active_schedule) {
        const schedule = dehumidifier.active_schedule;
        activeScheduleInfo.innerHTML = `
            <span class="active-indicator">AKTIV</span>
            ${schedule.start_time} - ${schedule.end_time}
            (${schedule.target_state === 'on' ? 'AN' : 'AUS'})
        `;
        activeScheduleInfo.style.display = 'block';
    } else if (activeScheduleInfo) {
        activeScheduleInfo.style.display = 'none';
    }
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
            enabled: dehumidifierAutoToggle?.classList.contains('enabled') || false,
            target: parseFloat(targetHumidity?.value || 60),
            threshold_high: parseFloat(thresholdHigh?.value || 5),
            threshold_low: parseFloat(thresholdLow?.value || 5),
            time_schedule_enabled: timeScheduleToggle?.classList.contains('enabled') || false
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
// Time Schedule Management (Feature #2)
// ==========================================

async function fetchSchedules() {
    try {
        const data = await GrowPiAPI.getSchedules();

        if (data.success) {
            schedules = data.schedules || [];
            timeScheduleEnabled = data.time_schedule_enabled || false;
            renderScheduleList();

            // Update toggle state
            if (timeScheduleToggle) {
                timeScheduleToggle.classList.toggle('enabled', timeScheduleEnabled);
            }
        }
    } catch (error) {
        console.error('[Environment] Schedule fetch error:', error);
    }
}

function renderScheduleList() {
    if (!scheduleList) return;

    if (schedules.length === 0) {
        scheduleList.innerHTML = `
            <div class="schedule-empty">
                Keine Zeitfenster definiert
            </div>
        `;
        return;
    }

    scheduleList.innerHTML = schedules.map(schedule => `
        <div class="schedule-item ${schedule.enabled ? '' : 'disabled'}" data-id="${schedule.id}">
            <div class="schedule-time">
                <span class="time-start">${schedule.start_time}</span>
                <span class="time-separator">-</span>
                <span class="time-end">${schedule.end_time}</span>
            </div>
            <div class="schedule-state ${schedule.target_state}">
                ${schedule.target_state === 'on' ? 'AN' : 'AUS'}
            </div>
            <div class="schedule-actions">
                <button class="btn-toggle-schedule" data-id="${schedule.id}" data-enabled="${schedule.enabled}">
                    ${schedule.enabled ? 'Aus' : 'An'}
                </button>
                <button class="btn-delete-schedule" data-id="${schedule.id}">
                    X
                </button>
            </div>
        </div>
    `).join('');

    // Add event listeners for schedule actions
    scheduleList.querySelectorAll('.btn-toggle-schedule').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const id = parseInt(e.target.dataset.id);
            const currentlyEnabled = e.target.dataset.enabled === 'true';
            await toggleSchedule(id, !currentlyEnabled);
        });
    });

    scheduleList.querySelectorAll('.btn-delete-schedule').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            const id = parseInt(e.target.dataset.id);
            await deleteSchedule(id);
        });
    });
}

async function addSchedule() {
    const startTime = scheduleStartTime?.value;
    const endTime = scheduleEndTime?.value;
    const targetState = scheduleTargetState?.value || 'on';

    if (!startTime || !endTime) {
        window.showError?.('Start- und Endzeit erforderlich');
        return;
    }

    // Validate time format
    const timeRegex = /^([01]?[0-9]|2[0-3]):[0-5][0-9]$/;
    if (!timeRegex.test(startTime) || !timeRegex.test(endTime)) {
        window.showError?.('Ungultiges Zeitformat (HH:MM)');
        return;
    }

    try {
        const data = await GrowPiAPI.createSchedule({
            start_time: startTime,
            end_time: endTime,
            target_state: targetState,
            enabled: true
        });

        if (data.success) {
            window.showSuccess?.('Zeitfenster erstellt');
            // Clear inputs
            if (scheduleStartTime) scheduleStartTime.value = '';
            if (scheduleEndTime) scheduleEndTime.value = '';
            // Refresh list
            await fetchSchedules();
        } else {
            window.showError?.(data.error || 'Fehler beim Erstellen');
        }
    } catch (error) {
        console.error('[Environment] Add schedule error:', error);
        window.showError?.('Verbindungsfehler');
    }
}

async function toggleSchedule(id, enabled) {
    try {
        const data = await GrowPiAPI.updateSchedule(id, { enabled });

        if (data.success) {
            await fetchSchedules();
        } else {
            window.showError?.(data.error || 'Fehler');
        }
    } catch (error) {
        console.error('[Environment] Toggle schedule error:', error);
        window.showError?.('Verbindungsfehler');
    }
}

async function deleteSchedule(id) {
    if (!confirm('Zeitfenster wirklich loschen?')) {
        return;
    }

    try {
        const data = await GrowPiAPI.deleteSchedule(id);

        if (data.success) {
            window.showSuccess?.('Zeitfenster geloscht');
            await fetchSchedules();
        } else {
            window.showError?.(data.error || 'Fehler beim Loschen');
        }
    } catch (error) {
        console.error('[Environment] Delete schedule error:', error);
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

    // Time schedule toggle (Feature #2)
    timeScheduleToggle?.addEventListener('click', () => {
        timeScheduleToggle.classList.toggle('enabled');
    });

    // Add schedule button (Feature #2)
    btnAddSchedule?.addEventListener('click', addSchedule);

    // Save configuration
    btnSaveRoomConfig?.addEventListener('click', saveRoomConfig);

    // FIX: Humidity input focus/blur handlers to prevent polling overwrites (v6.16.0 Bugfix)
    // Prevents race-condition where auto-refresh would overwrite user input
    targetHumidity?.addEventListener('focus', () => {
        isUserEditing.targetHumidity = true;
    });
    targetHumidity?.addEventListener('blur', () => {
        isUserEditing.targetHumidity = false;
    });

    thresholdHigh?.addEventListener('focus', () => {
        isUserEditing.thresholdHigh = true;
    });
    thresholdHigh?.addEventListener('blur', () => {
        isUserEditing.thresholdHigh = false;
    });

    thresholdLow?.addEventListener('focus', () => {
        isUserEditing.thresholdLow = true;
    });
    thresholdLow?.addEventListener('blur', () => {
        isUserEditing.thresholdLow = false;
    });
}

// ==========================================
// Version Display Update (v6.16.0)
// ==========================================

/**
 * Update version display from API
 * Fetches current GrowPi version and updates the header badge
 */
async function updateVersionDisplay() {
    const versionBadge = document.getElementById('versionBadge');
    if (!versionBadge) return;

    try {
        const data = await GrowPiAPI.getVersion();
        if (data.success) {
            versionBadge.textContent = data.version_display;
            versionBadge.title = `GrowPi ${data.version_display}`;
        }
    } catch (error) {
        console.error('[Environment] Failed to fetch version:', error);
        versionBadge.textContent = 'v?.?.?';
    }
}

// Call version update on page load
document.addEventListener('DOMContentLoaded', () => {
    updateVersionDisplay();
});
