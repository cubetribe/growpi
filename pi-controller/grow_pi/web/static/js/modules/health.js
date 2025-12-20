/**
 * Health Monitoring Module
 * Polls /api/health endpoint and updates system health widget.
 *
 * Features:
 * - CPU Temperature monitoring with status colors
 * - RAM usage with visual progress bar
 * - Disk usage with visual progress bar
 * - System uptime display
 * - Auto-refresh every 30 seconds
 * - Status-based color coding (normal/warning/critical)
 */

import { GrowPiAPI } from '../api.js';

// Polling interval (30 seconds)
const HEALTH_POLL_INTERVAL = 30000;

// DOM Elements
let elements = {
    cpuTemp: null,
    memory: null,
    disk: null,
    uptime: null
};

let pollInterval = null;

/**
 * Initialize health monitoring.
 */
export function initHealthMonitoring() {
    // Cache DOM elements
    elements.cpuTemp = document.getElementById('healthCpuTemp');
    elements.memory = document.getElementById('healthMemory');
    elements.disk = document.getElementById('healthDisk');
    elements.uptime = document.getElementById('healthUptime');

    if (!elements.cpuTemp || !elements.memory || !elements.disk || !elements.uptime) {
        console.warn('Health monitoring: DOM elements not found');
        return;
    }

    // Initial fetch
    fetchHealthData();

    // Start polling
    pollInterval = setInterval(fetchHealthData, HEALTH_POLL_INTERVAL);

    console.log('Health monitoring initialized (polling every 30s)');
}

/**
 * Fetch health data from API.
 */
async function fetchHealthData() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        if (data.system) {
            updateHealthWidget(data.system);
        }
    } catch (error) {
        console.error('Failed to fetch health data:', error);
        // Show error state in widget
        showErrorState();
    }
}

/**
 * Update health widget with fresh data.
 */
function updateHealthWidget(system) {
    // CPU Temperature
    if (system.cpu_temp !== null && system.cpu_temp !== undefined) {
        updateMetric(
            elements.cpuTemp,
            system.cpu_temp,
            '°C',
            system.cpu_temp_status,
            system.cpu_temp,
            80 // Max temp for bar (80°C = 100%)
        );
    } else {
        updateMetric(elements.cpuTemp, 'N/A', '', 'unknown', 0, 100);
    }

    // Memory
    updateMetric(
        elements.memory,
        system.memory_percent,
        '%',
        system.memory_status,
        system.memory_percent,
        100
    );

    // Disk
    updateMetric(
        elements.disk,
        system.disk_percent,
        '%',
        system.disk_status,
        system.disk_percent,
        100
    );

    // Uptime
    const uptimeDays = formatUptime(system.uptime_seconds);
    updateMetric(
        elements.uptime,
        uptimeDays.value,
        uptimeDays.unit,
        'normal',
        100, // Always show full bar for uptime
        100
    );
}

/**
 * Update individual metric element.
 */
function updateMetric(element, value, unit, status, barValue, barMax) {
    if (!element) return;

    // Update number
    const numberEl = element.querySelector('.metric-number');
    if (numberEl) {
        if (typeof value === 'number') {
            numberEl.textContent = value.toFixed(1);
        } else {
            numberEl.textContent = value;
        }
    }

    // Update unit
    const unitEl = element.querySelector('.metric-unit');
    if (unitEl) {
        unitEl.textContent = unit;
    }

    // Update status text
    const statusEl = element.querySelector('.metric-status');
    if (statusEl) {
        statusEl.textContent = getStatusLabel(status);
        statusEl.className = `metric-status status-${status}`;
    }

    // Update bar fill
    const fillEl = element.querySelector('.metric-fill');
    if (fillEl) {
        const percentage = Math.min((barValue / barMax) * 100, 100);
        fillEl.style.width = `${percentage}%`;
        fillEl.className = `metric-fill fill-${status}`;
    }

    // Update metric container status class
    element.className = `health-metric metric-${status}`;
}

/**
 * Get human-readable status label.
 */
function getStatusLabel(status) {
    switch (status) {
        case 'normal':
            return 'Normal';
        case 'warning':
            return 'Warnung';
        case 'critical':
            return 'Kritisch';
        case 'unknown':
            return 'Unbekannt';
        default:
            return 'Läuft';
    }
}

/**
 * Format uptime seconds to human-readable format.
 */
function formatUptime(seconds) {
    const days = Math.floor(seconds / 86400);
    const hours = Math.floor((seconds % 86400) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);

    if (days > 0) {
        return { value: days, unit: days === 1 ? 'Tag' : 'Tage' };
    } else if (hours > 0) {
        return { value: hours, unit: hours === 1 ? 'Stunde' : 'Stunden' };
    } else {
        return { value: minutes, unit: minutes === 1 ? 'Minute' : 'Minuten' };
    }
}

/**
 * Show error state when API call fails.
 */
function showErrorState() {
    [elements.cpuTemp, elements.memory, elements.disk, elements.uptime].forEach(el => {
        if (!el) return;

        const numberEl = el.querySelector('.metric-number');
        if (numberEl) numberEl.textContent = '--';

        const statusEl = el.querySelector('.metric-status');
        if (statusEl) {
            statusEl.textContent = 'Fehler';
            statusEl.className = 'metric-status status-unknown';
        }

        const fillEl = el.querySelector('.metric-fill');
        if (fillEl) {
            fillEl.style.width = '0%';
            fillEl.className = 'metric-fill fill-unknown';
        }

        el.className = 'health-metric metric-unknown';
    });
}

/**
 * Cleanup function (stop polling).
 */
export function cleanupHealthMonitoring() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
        console.log('Health monitoring stopped');
    }
}
