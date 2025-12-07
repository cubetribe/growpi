/**
 * History Module
 *
 * Manages the History Tab (Tab 3) functionality:
 * - Chart.js initialization for Sensor, Lamp, and Plug charts
 * - Time range selection (24h, 7d, 30d)
 * - Data fetching and chart updates
 * - System logs table with color-coded severity
 */

import { GrowPiAPI } from '../api.js';

export class HistoryModule {
    constructor() {
        // Chart instances
        this.sensorChartInstance = null;
        this.lampChartInstance = null;
        this.plugChartInstance = null;

        // State
        this.currentRangeHours = 24;

        // Color scheme
        this.channelColors = {
            1: '#ff4444', // Far Red
            2: '#ffbb44', // Warm White
            3: '#88ddff', // Cool White
            4: '#cc66ff'  // UV
        };

        this.plugColors = ['#11ff55', '#ff4444', '#ffbb44', '#88ddff'];
    }

    /**
     * Initialize the History tab
     * Sets up event listeners and prepares UI
     */
    initHistoryTab() {
        console.log('[History] Initializing History Tab');

        // Range selector event listeners
        this.setupRangeSelectors();

        // Tab switch detection
        this.setupTabSwitchListener();
    }

    /**
     * Initialize all Chart.js charts
     * Creates sensor, lamp, and plug chart instances
     */
    initCharts() {
        console.log('[History] Initializing charts');

        // Set Chart.js global defaults
        Chart.defaults.color = '#888';
        Chart.defaults.borderColor = '#333';

        // Common chart options
        const commonOptions = {
            responsive: true,
            maintainAspectRatio: false,
            interaction: {
                mode: 'index',
                intersect: false
            },
            plugins: {
                legend: {
                    labels: { color: '#ccc' }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.9)',
                    titleColor: '#fff',
                    bodyColor: '#ccc',
                    borderColor: 'rgba(17, 255, 85, 0.3)',
                    borderWidth: 1
                }
            },
            scales: {
                x: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: { color: '#666' }
                },
                y: {
                    grid: {
                        color: 'rgba(255, 255, 255, 0.05)'
                    },
                    ticks: { color: '#666' }
                }
            }
        };

        // Initialize Sensor Chart (Dual-Axis: Temperature + Humidity)
        this.initSensorChart(commonOptions);

        // Initialize Lamp Chart (4 channels)
        this.initLampChart(commonOptions);

        // Initialize Plug Chart
        this.initPlugChart(commonOptions);
    }

    /**
     * Initialize the sensor chart (Temperature + Humidity)
     * Uses dual Y-axes for different units
     */
    initSensorChart(commonOptions) {
        const ctx = document.getElementById('sensorChart').getContext('2d');

        this.sensorChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Temperatur (°C)',
                        borderColor: '#11ff55',
                        backgroundColor: 'rgba(17, 255, 85, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y',
                        data: []
                    },
                    {
                        label: 'Feuchtigkeit (%)',
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1',
                        data: []
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: { color: '#666' },
                        title: {
                            display: true,
                            text: 'Temperatur (°C)',
                            color: '#11ff55'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        ticks: { color: '#666' },
                        title: {
                            display: true,
                            text: 'Feuchtigkeit (%)',
                            color: '#3b82f6'
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize the lamp chart (4 channels)
     */
    initLampChart(commonOptions) {
        const ctx = document.getElementById('lampChart').getContext('2d');

        this.lampChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Far Red',
                        borderColor: this.channelColors[1],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: []
                    },
                    {
                        label: 'Warm White',
                        borderColor: this.channelColors[2],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: []
                    },
                    {
                        label: 'Cool White',
                        borderColor: this.channelColors[3],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: []
                    },
                    {
                        label: 'UV',
                        borderColor: this.channelColors[4],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: []
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        min: 0,
                        max: 100,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: { color: '#666' },
                        title: {
                            display: true,
                            text: 'Intensität (%)',
                            color: '#888'
                        }
                    }
                }
            }
        });
    }

    /**
     * Initialize the plug chart
     * This chart is dynamically created based on available devices
     */
    initPlugChart(commonOptions) {
        const ctx = document.getElementById('plugChart').getContext('2d');

        this.plugChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                ...commonOptions,
                scales: {
                    ...commonOptions.scales,
                    y: {
                        min: 0,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: { color: '#666' },
                        title: {
                            display: true,
                            text: 'Leistung (W)',
                            color: '#888'
                        }
                    }
                }
            }
        });
    }

    /**
     * Load all history data for a given time range
     * @param {number} hours - Time range in hours (24, 168, 720)
     */
    async loadHistoryData(hours) {
        console.log(`[History] Loading data for ${hours} hours`);

        this.currentRangeHours = hours;

        // Load logs (independent)
        this.loadSystemLogs(hours);

        // Load chart data
        try {
            // Use GrowPiAPI instead of direct fetch()
            const [temps, hums, plugs] = await Promise.all([
                GrowPiAPI.getSensorLogs('temperature', hours, 1000),
                GrowPiAPI.getSensorLogs('humidity', hours, 1000),
                GrowPiAPI.getPlugLogs(hours, 1000)
            ]);

            // Update sensor chart
            if (temps.success && hums.success) {
                this.updateSensorChart(temps.readings, hums.readings);
            }

            // Fetch lamp data for all channels in parallel (use GrowPiAPI)
            const lampResults = await Promise.all(
                [1, 2, 3, 4].map(channel =>
                    GrowPiAPI.getLampLogs(channel, hours, 1000)
                )
            );
            this.updateLampChart(...lampResults);

            // Update plug chart
            if (plugs && Array.isArray(plugs)) {
                this.updatePlugChart(plugs);
            } else if (plugs && plugs.success && Array.isArray(plugs.data)) {
                this.updatePlugChart(plugs.data);
            } else {
                this.updatePlugChart(plugs);
            }

        } catch (e) {
            console.error('[History] Error loading charts:', e);
            this.showError('Fehler beim Laden der Diagramme');
        }
    }

    /**
     * Update the sensor chart with temperature and humidity data
     * @param {Array} tempReadings - Temperature readings
     * @param {Array} humReadings - Humidity readings
     */
    updateSensorChart(tempReadings, humReadings) {
        if (!this.sensorChartInstance) return;

        const temps = (tempReadings || []).reverse();
        const hums = (humReadings || []).reverse();

        // Generate labels from temperature data
        const labels = temps.map(r => this.formatTimestamp(new Date(r.created_at)));

        // Update chart data
        this.sensorChartInstance.data.labels = labels;
        this.sensorChartInstance.data.datasets[0].data = temps.map(r => r.value);
        this.sensorChartInstance.data.datasets[1].data = hums.map(r => r.value);

        this.sensorChartInstance.update();
    }

    /**
     * Update the lamp chart with data from all 4 channels
     * @param {Object} ch1 - Channel 1 data
     * @param {Object} ch2 - Channel 2 data
     * @param {Object} ch3 - Channel 3 data
     * @param {Object} ch4 - Channel 4 data
     */
    updateLampChart(ch1, ch2, ch3, ch4) {
        if (!this.lampChartInstance) return;

        const lampResults = [ch1, ch2, ch3, ch4];

        // Use Channel 1 timestamps for labels
        const ch1Logs = (lampResults[0].logs || []).reverse();
        const labels = ch1Logs.map(r => this.formatTimestamp(new Date(r.created_at)));

        // Update chart data
        this.lampChartInstance.data.labels = labels;

        lampResults.forEach((res, index) => {
            const logs = (res.logs || []).reverse();
            this.lampChartInstance.data.datasets[index].data = logs.map(r => r.intensity);
        });

        this.lampChartInstance.update();
    }

    /**
     * Update the plug chart with power consumption data
     * @param {Array} logs - Plug log data
     */
    updatePlugChart(logs) {
        if (!this.plugChartInstance) return;

        // Group by device
        const devices = {};
        logs.forEach(log => {
            if (!devices[log.device_id]) {
                devices[log.device_id] = [];
            }
            devices[log.device_id].push(log);
        });

        // Create datasets for each device
        const datasets = [];
        let colorIdx = 0;

        for (const [deviceId, deviceLogs] of Object.entries(devices)) {
            // Sort by time
            deviceLogs.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));

            const data = deviceLogs.map(l => ({
                x: new Date(l.created_at),
                y: l.power
            }));

            datasets.push({
                label: `Power (${deviceId.substr(0, 5)}...)`,
                data: data,
                borderColor: this.plugColors[colorIdx % this.plugColors.length],
                backgroundColor: this.plugColors[colorIdx % this.plugColors.length] + '20',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0
            });
            colorIdx++;
        }

        // Create labels from all timestamps
        const allDates = logs.map(l => new Date(l.created_at)).sort((a, b) => a - b);
        const labels = allDates.map(d => this.formatTimestamp(d));

        // Destroy old chart and create new one (to handle dynamic datasets)
        if (this.plugChartInstance) {
            this.plugChartInstance.destroy();
        }

        const ctx = document.getElementById('plugChart').getContext('2d');
        this.plugChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.1)'
                        },
                        ticks: {
                            color: '#888'
                        },
                        title: {
                            display: true,
                            text: 'Watt (W)',
                            color: '#888'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: '#888',
                            maxTicksLimit: 8
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: {
                            color: '#fff'
                        }
                    }
                }
            }
        });
    }

    /**
     * Load system logs from API
     * @param {number} hours - Time range in hours
     */
    async loadSystemLogs(hours) {
        try {
            // Use GrowPiAPI instead of direct fetch()
            const logsData = await GrowPiAPI.getEventLogs(hours, 100);

            if (logsData.success) {
                this.updateLogTable(logsData.events);
            } else {
                console.error('[History] Log API error:', logsData.error);
                this.showLogError('Fehler beim Laden der Logs');
            }
        } catch (e) {
            console.error('[History] Error loading logs:', e);
            this.showLogError('Verbindungsfehler');
        }
    }

    /**
     * Update the log table with event data
     * @param {Array} events - Event log entries
     */
    updateLogTable(events) {
        const tbody = document.getElementById('logTableBody');
        tbody.innerHTML = '';

        if (!events || events.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" style="text-align:center; padding:20px;">Keine Logs vorhanden</td></tr>';
            return;
        }

        events.forEach(event => {
            const tr = document.createElement('tr');

            // Apply color coding based on severity
            if (event.severity === 'error') tr.classList.add('log-row-error');
            if (event.severity === 'warning') tr.classList.add('log-row-warning');

            const d = new Date(event.created_at);
            const timeStr = d.toLocaleString([], {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });

            tr.innerHTML = `
                <td class="log-time">${timeStr}</td>
                <td>${event.event_type}</td>
                <td>${event.message}</td>
            `;
            tbody.appendChild(tr);
        });
    }

    /**
     * Handle time range change
     * @param {number} hours - New time range in hours
     */
    handleRangeChange(hours) {
        console.log(`[History] Range changed to ${hours} hours`);
        this.loadHistoryData(hours);
    }

    /**
     * Setup range selector button event listeners
     */
    setupRangeSelectors() {
        document.querySelectorAll('.range-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                // Update active state
                document.querySelectorAll('.range-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');

                // Load new data
                const hours = parseInt(e.target.dataset.range);
                this.handleRangeChange(hours);
            });
        });
    }

    /**
     * Setup tab switch listener to initialize charts on first view
     */
    setupTabSwitchListener() {
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                if (tabId === 'history') {
                    // Initialize charts if not already done
                    if (!this.sensorChartInstance) {
                        this.initCharts();
                    }
                    // Load data
                    this.loadHistoryData(this.currentRangeHours);
                }
            });
        });
    }

    /**
     * Format timestamp based on current time range
     * @param {Date} date - Date to format
     * @returns {string} Formatted timestamp
     */
    formatTimestamp(date) {
        if (this.currentRangeHours > 24) {
            return date.toLocaleString([], {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        }
        return date.toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    /**
     * Show error message in log table
     * @param {string} message - Error message
     */
    showLogError(message) {
        const tbody = document.getElementById('logTableBody');
        tbody.innerHTML = `<tr><td colspan="3" style="text-align:center; padding:20px; color:#ff4444">${message}</td></tr>`;
    }

    /**
     * Show error notification (uses global error handler)
     * @param {string} message - Error message
     */
    showError(message) {
        const errorMsg = document.getElementById('errorMsg');
        if (errorMsg) {
            errorMsg.textContent = message;
            errorMsg.classList.add('show');
            setTimeout(() => errorMsg.classList.remove('show'), 5000);
        }
    }
}
