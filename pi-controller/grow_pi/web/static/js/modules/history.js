/**
 * History Module
 *
 * Manages the History Tab (Tab 3) functionality:
 * - Chart.js initialization for Sensor, Lamp, and Plug charts
 * - Time range selection (24h, 7d, 30d)
 * - Data fetching and chart updates
 * - System logs table with color-coded severity
 *
 * FIX 2025-12-07: X-Achse wird jetzt auf die gewählte Zeitspanne fixiert,
 * auch wenn weniger Daten vorhanden sind.
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

        // Device name mapping (loaded from config)
        this.deviceNames = {};

        // Color scheme
        this.channelColors = {
            1: '#ff4444', // Far Red
            2: '#ffbb44', // Warm White
            3: '#88ddff', // Cool White
            4: '#cc66ff'  // UV
        };

        this.plugColors = ['#11ff55', '#ff4444', '#ffbb44', '#88ddff', '#cc66ff', '#ff88aa'];
    }

    /**
     * Calculate time range boundaries for X-axis
     * @returns {Object} { min: Date, max: Date }
     */
    getTimeRangeBounds() {
        const now = new Date();
        const startTime = new Date(now.getTime() - (this.currentRangeHours * 60 * 60 * 1000));
        return { min: startTime, max: now };
    }

    /**
     * Initialize the History tab
     * Sets up event listeners and prepares UI
     */
    initHistoryTab() {
        console.log('[History] Initializing History Tab');

        // Load device names from config
        this.loadDeviceNames();

        // Range selector event listeners
        this.setupRangeSelectors();

        // Tab switch detection
        this.setupTabSwitchListener();
    }

    /**
     * Load device names from costs config API
     * Maps device IDs to human-readable names
     */
    async loadDeviceNames() {
        try {
            const config = await GrowPiAPI.getCostsConfig();
            if (config.success && config.devices) {
                this.deviceNames = config.devices;
                console.log('[History] Loaded device names:', this.deviceNames);
            }
        } catch (e) {
            console.error('[History] Error loading device names:', e);
        }
    }

    /**
     * Get device display name from ID
     * @param {string} deviceId - Tuya device ID
     * @returns {string} Human-readable device name or truncated ID
     */
    getDeviceName(deviceId) {
        if (this.deviceNames[deviceId]) {
            return this.deviceNames[deviceId];
        }
        // Fallback: return truncated ID
        return deviceId.substr(0, 8) + '...';
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
     * Uses dual Y-axes for different units and time-based X-axis
     */
    initSensorChart(commonOptions) {
        const ctx = document.getElementById('sensorChart').getContext('2d');
        const bounds = this.getTimeRangeBounds();

        this.sensorChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Temperatur (°C)',
                        borderColor: '#11ff55',
                        backgroundColor: 'rgba(17, 255, 85, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y',
                        data: [],
                        spanGaps: true
                    },
                    {
                        label: 'Feuchtigkeit (%)',
                        borderColor: '#3b82f6',
                        backgroundColor: 'rgba(59, 130, 246, 0.1)',
                        borderWidth: 2,
                        fill: true,
                        tension: 0.4,
                        yAxisID: 'y1',
                        data: [],
                        spanGaps: true
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentRangeHours <= 24 ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'dd.MM.'
                            },
                            tooltipFormat: 'dd.MM. HH:mm'
                        },
                        min: bounds.min,
                        max: bounds.max,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            maxTicksLimit: 8
                        }
                    },
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
     * Uses time-based X-axis for consistent time range display
     */
    initLampChart(commonOptions) {
        const ctx = document.getElementById('lampChart').getContext('2d');
        const bounds = this.getTimeRangeBounds();

        this.lampChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'Far Red',
                        borderColor: this.channelColors[1],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: [],
                        spanGaps: true
                    },
                    {
                        label: 'Warm White',
                        borderColor: this.channelColors[2],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: [],
                        spanGaps: true
                    },
                    {
                        label: 'Cool White',
                        borderColor: this.channelColors[3],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: [],
                        spanGaps: true
                    },
                    {
                        label: 'UV',
                        borderColor: this.channelColors[4],
                        borderWidth: 2,
                        tension: 0.2,
                        pointRadius: 0,
                        data: [],
                        spanGaps: true
                    }
                ]
            },
            options: {
                ...commonOptions,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentRangeHours <= 24 ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'dd.MM.'
                            },
                            tooltipFormat: 'dd.MM. HH:mm'
                        },
                        min: bounds.min,
                        max: bounds.max,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            maxTicksLimit: 8
                        }
                    },
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
     * Uses time-based X-axis for consistent time range display
     */
    initPlugChart(commonOptions) {
        const ctx = document.getElementById('plugChart').getContext('2d');
        const bounds = this.getTimeRangeBounds();

        this.plugChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: []
            },
            options: {
                ...commonOptions,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentRangeHours <= 24 ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'dd.MM.'
                            },
                            tooltipFormat: 'dd.MM. HH:mm'
                        },
                        min: bounds.min,
                        max: bounds.max,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#666',
                            maxTicksLimit: 8
                        }
                    },
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
     * Backend automatically applies intelligent downsampling:
     * - 0-4h: raw data (1min)
     * - 4-24h: 5min averages
     * - 1-7d: 15min averages
     * - 7-30d: 30min averages
     * - >30d: 1h averages
     * @param {number} hours - Time range in hours (24, 168, 720, etc.)
     */
    async loadHistoryData(hours) {
        console.log(`[History] Loading data for ${hours} hours (downsampled)`);

        this.currentRangeHours = hours;

        // Load logs (independent)
        this.loadSystemLogs(hours);

        // Load chart data - no limit needed, backend handles downsampling
        try {
            // Use GrowPiAPI - limit parameter removed, backend auto-aggregates
            const [temps, hums, plugs] = await Promise.all([
                GrowPiAPI.getSensorLogs('temperature', hours),
                GrowPiAPI.getSensorLogs('humidity', hours),
                GrowPiAPI.getPlugLogs(hours)
            ]);

            // Update sensor chart
            if (temps.success && hums.success) {
                this.updateSensorChart(temps.readings, hums.readings);
            }

            // Fetch lamp data for all channels in parallel (use GrowPiAPI)
            // No limit needed - backend auto-downsamples based on time range
            const lampResults = await Promise.all(
                [1, 2, 3, 4].map(channel =>
                    GrowPiAPI.getLampLogs(channel, hours)
                )
            );
            this.updateLampChart(...lampResults);

            // Update plug chart
            // API returns { count: N, data: [...] } format
            if (plugs && Array.isArray(plugs)) {
                this.updatePlugChart(plugs);
            } else if (plugs && Array.isArray(plugs.data)) {
                // Handle { count: N, data: [...] } format from /api/logs/plugs
                this.updatePlugChart(plugs.data);
            } else {
                console.warn('[History] Unexpected plugs format:', plugs);
                this.updatePlugChart([]);
            }

        } catch (e) {
            console.error('[History] Error loading charts:', e);
            this.showError('Fehler beim Laden der Diagramme');
        }
    }

    /**
     * Update the sensor chart with temperature and humidity data
     * Uses {x: Date, y: value} format for time-based X-axis
     * @param {Array} tempReadings - Temperature readings
     * @param {Array} humReadings - Humidity readings
     */
    updateSensorChart(tempReadings, humReadings) {
        if (!this.sensorChartInstance) return;

        const temps = (tempReadings || []).reverse();
        const hums = (humReadings || []).reverse();

        // Convert to {x, y} format for time scale
        const tempData = temps.map(r => ({
            x: new Date(r.created_at),
            y: r.value
        }));
        const humData = hums.map(r => ({
            x: new Date(r.created_at),
            y: r.value
        }));

        // Update time range bounds
        const bounds = this.getTimeRangeBounds();
        this.sensorChartInstance.options.scales.x.min = bounds.min;
        this.sensorChartInstance.options.scales.x.max = bounds.max;
        this.sensorChartInstance.options.scales.x.time.unit = this.currentRangeHours <= 24 ? 'hour' : 'day';

        // Update chart data
        this.sensorChartInstance.data.datasets[0].data = tempData;
        this.sensorChartInstance.data.datasets[1].data = humData;

        this.sensorChartInstance.update();
    }

    /**
     * Update the lamp chart with data from all 4 channels
     * Uses {x: Date, y: value} format for time-based X-axis
     * @param {Object} ch1 - Channel 1 data
     * @param {Object} ch2 - Channel 2 data
     * @param {Object} ch3 - Channel 3 data
     * @param {Object} ch4 - Channel 4 data
     */
    updateLampChart(ch1, ch2, ch3, ch4) {
        if (!this.lampChartInstance) return;

        const lampResults = [ch1, ch2, ch3, ch4];

        // Update time range bounds
        const bounds = this.getTimeRangeBounds();
        this.lampChartInstance.options.scales.x.min = bounds.min;
        this.lampChartInstance.options.scales.x.max = bounds.max;
        this.lampChartInstance.options.scales.x.time.unit = this.currentRangeHours <= 24 ? 'hour' : 'day';

        // Update chart data with {x, y} format for each channel
        lampResults.forEach((res, index) => {
            const logs = (res.logs || []).reverse();
            this.lampChartInstance.data.datasets[index].data = logs.map(r => ({
                x: new Date(r.created_at),
                y: r.intensity
            }));
        });

        this.lampChartInstance.update();
    }

    /**
     * Update the plug chart with power consumption data
     * Uses time-based X-axis with fixed time range bounds
     * @param {Array} logs - Plug log data
     */
    updatePlugChart(logs) {
        if (!this.plugChartInstance) return;

        const bounds = this.getTimeRangeBounds();

        // Handle empty data - still show chart with correct time range
        if (!logs || logs.length === 0) {
            console.log('[History] No plug data available');
            // Update time bounds but keep empty datasets
            this.plugChartInstance.options.scales.x.min = bounds.min;
            this.plugChartInstance.options.scales.x.max = bounds.max;
            this.plugChartInstance.options.scales.x.time.unit = this.currentRangeHours <= 24 ? 'hour' : 'day';
            this.plugChartInstance.data.datasets = [];
            this.plugChartInstance.update();
            return;
        }

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

            // Use device name from config instead of truncated ID
            const deviceName = this.getDeviceName(deviceId);

            datasets.push({
                label: deviceName,
                data: data,
                borderColor: this.plugColors[colorIdx % this.plugColors.length],
                backgroundColor: this.plugColors[colorIdx % this.plugColors.length] + '20',
                borderWidth: 2,
                tension: 0.4,
                fill: true,
                pointRadius: 0,
                spanGaps: true
            });
            colorIdx++;
        }

        // Destroy old chart and create new one (to handle dynamic datasets)
        if (this.plugChartInstance) {
            this.plugChartInstance.destroy();
        }

        const ctx = document.getElementById('plugChart').getContext('2d');
        this.plugChartInstance = new Chart(ctx, {
            type: 'line',
            data: {
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
                    x: {
                        type: 'time',
                        time: {
                            unit: this.currentRangeHours <= 24 ? 'hour' : 'day',
                            displayFormats: {
                                hour: 'HH:mm',
                                day: 'dd.MM.'
                            },
                            tooltipFormat: 'dd.MM. HH:mm'
                        },
                        min: bounds.min,
                        max: bounds.max,
                        grid: {
                            color: 'rgba(255, 255, 255, 0.05)'
                        },
                        ticks: {
                            color: '#888',
                            maxTicksLimit: 8
                        }
                    },
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
