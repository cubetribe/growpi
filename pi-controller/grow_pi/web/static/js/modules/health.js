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
 * - Circuit breaker status display and reset (v6.24.1)
 * - Service restart button (v6.24.1)
 */

import { GrowPiAPI } from '../api.js';

// Polling interval (30 seconds)
const HEALTH_POLL_INTERVAL = 30000;

// DOM Elements
let elements = {
    cpuTemp: null,
    memory: null,
    disk: null,
    uptime: null,
    // v6.24.1: Circuit breaker elements
    circuitBreakerStatus: null,
    btnResetCircuitBreaker: null,
    btnRestartService: null
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

    // v6.24.1: Circuit breaker elements
    elements.circuitBreakerStatus = document.getElementById('circuitBreakerStatus');
    elements.btnResetCircuitBreaker = document.getElementById('btnResetCircuitBreaker');
    elements.btnRestartService = document.getElementById('btnRestartService');

    if (!elements.cpuTemp || !elements.memory || !elements.disk || !elements.uptime) {
        console.warn('Health monitoring: DOM elements not found');
        return;
    }

    // Setup event listeners for buttons
    setupEventListeners();

    // Initial fetch
    fetchHealthData();
    fetchSensorHealth();

    // Start polling
    pollInterval = setInterval(() => {
        fetchHealthData();
        fetchSensorHealth();
    }, HEALTH_POLL_INTERVAL);

    console.log('Health monitoring initialized (polling every 30s)');
}

/**
 * Setup event listeners for circuit breaker and service restart buttons.
 */
function setupEventListeners() {
    // Reset circuit breaker button
    if (elements.btnResetCircuitBreaker) {
        elements.btnResetCircuitBreaker.addEventListener('click', async () => {
            if (!confirm('Sensor-Sicherung zurücksetzen?')) return;

            elements.btnResetCircuitBreaker.disabled = true;
            elements.btnResetCircuitBreaker.textContent = 'Reset...';

            try {
                const response = await fetch('/api/health', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'reset_circuit_breaker' })
                });

                const data = await response.json();

                if (data.success) {
                    window.showSuccess?.('Sensor-Sicherung zurückgesetzt!');
                    // Refresh sensor health immediately
                    setTimeout(fetchSensorHealth, 500);
                } else {
                    window.showError?.(data.error || 'Reset fehlgeschlagen');
                }
            } catch (error) {
                console.error('Circuit breaker reset failed:', error);
                window.showError?.('Verbindungsfehler');
            } finally {
                elements.btnResetCircuitBreaker.disabled = false;
                elements.btnResetCircuitBreaker.textContent = 'Sicherung Reset';
            }
        });
    }

    // Service restart button
    if (elements.btnRestartService) {
        elements.btnRestartService.addEventListener('click', async () => {
            if (!confirm('GrowPi Service wirklich neu starten?\n\nDie Verbindung wird kurz unterbrochen.')) return;

            elements.btnRestartService.disabled = true;
            elements.btnRestartService.textContent = 'Neustart...';

            try {
                const response = await fetch('/api/health', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action: 'restart_service' })
                });

                // Service will restart, connection will be lost
                window.showSuccess?.('Service wird neu gestartet...');

                // Wait and try to reconnect
                setTimeout(() => {
                    window.showSuccess?.('Verbinde erneut...');
                    // Reload page after service restart
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                }, 2000);

            } catch (error) {
                // Expected - connection lost during restart
                console.log('Service restart initiated, connection lost as expected');
                window.showSuccess?.('Service wird neu gestartet...');

                setTimeout(() => {
                    window.location.reload();
                }, 5000);
            }
        });
    }
}

/**
 * Fetch sensor health data including circuit breaker status.
 * Uses the main /api/health endpoint which includes circuit_breaker directly.
 */
async function fetchSensorHealth() {
    try {
        const response = await fetch('/api/health');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // Circuit breaker is directly in the response (v6.24.1)
        if (data.circuit_breaker) {
            updateCircuitBreakerStatus(data.circuit_breaker);
        }
    } catch (error) {
        console.error('Failed to fetch sensor health:', error);
        // Show unknown state
        if (elements.circuitBreakerStatus) {
            elements.circuitBreakerStatus.textContent = 'Fehler';
            elements.circuitBreakerStatus.className = 'sensor-status-value';
        }
    }
}

/**
 * Update circuit breaker status display.
 */
function updateCircuitBreakerStatus(cb) {
    if (!elements.circuitBreakerStatus) return;

    // Parse state from pybreaker format
    const stateStr = cb.state.toLowerCase();
    let displayText = 'Unbekannt';
    let statusClass = '';

    if (stateStr.includes('closed')) {
        displayText = 'OK';
        statusClass = 'status-closed';
    } else if (stateStr.includes('open')) {
        displayText = 'OFFEN';
        statusClass = 'status-open';
    } else if (stateStr.includes('half')) {
        displayText = 'Test...';
        statusClass = 'status-half-open';
    }

    elements.circuitBreakerStatus.textContent = displayText;
    elements.circuitBreakerStatus.className = `sensor-status-value ${statusClass}`;

    // Show/hide reset button based on state
    if (elements.btnResetCircuitBreaker) {
        // Always show button but highlight when open
        if (stateStr.includes('open')) {
            elements.btnResetCircuitBreaker.style.animation = 'pulse-critical 1.5s infinite';
        } else {
            elements.btnResetCircuitBreaker.style.animation = 'none';
        }
    }
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
