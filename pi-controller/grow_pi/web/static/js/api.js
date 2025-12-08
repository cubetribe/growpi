/**
 * GrowPi API Client
 * Centralized API communication layer for all backend requests
 *
 * Usage:
 *   import { GrowPiAPI } from './api.js';
 *   const status = await GrowPiAPI.getStatus();
 *   await GrowPiAPI.setLamp(1, 50);
 */

const BASE_URL = '';  // Relative to current domain

/**
 * Generic fetch wrapper with error handling
 * @private
 */
async function request(url, options = {}) {
    try {
        const response = await fetch(BASE_URL + url, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error [${url}]:`, error);
        throw error;
    }
}

/**
 * GET request helper
 * @private
 */
function get(url) {
    return request(url, { method: 'GET' });
}

/**
 * POST request helper
 * @private
 */
function post(url, data) {
    return request(url, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

/**
 * PUT request helper
 * @private
 */
function put(url, data) {
    return request(url, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

// ==========================================
// Public API Methods
// ==========================================

export const GrowPiAPI = {
    /**
     * Get current system status (temperature, humidity, lamp states)
     * @returns {Promise<Object>} Status data
     */
    async getStatus() {
        return await get('/api/status');
    },

    /**
     * Set lamp intensity for a specific channel
     * @param {number} channel - Lamp channel (1-4)
     * @param {number} intensity - Intensity value (0-100)
     * @returns {Promise<Object>} Response data
     */
    async setLamp(channel, intensity) {
        return await post(`/api/lamp/${channel}`, {
            intensity: parseInt(intensity, 10)
        });
    },

    /**
     * Get temperature sensor reading
     * @returns {Promise<Object>} Temperature data
     */
    async getTemperature() {
        const status = await this.getStatus();
        return {
            value: status.temperature,
            unit: '°C'
        };
    },

    /**
     * Get humidity sensor reading
     * @returns {Promise<Object>} Humidity data
     */
    async getHumidity() {
        const status = await this.getStatus();
        return {
            value: status.humidity,
            unit: '%'
        };
    },

    /**
     * Get current mode (auto/manual)
     * @returns {Promise<Object>} Mode data { mode: 'auto' | 'manual' }
     */
    async getMode() {
        return await get('/api/mode');
    },

    /**
     * Set control mode
     * @param {string} mode - Either 'auto' or 'manual'
     * @returns {Promise<Object>} Response data
     */
    async setMode(mode) {
        if (mode !== 'auto' && mode !== 'manual') {
            throw new Error('Mode must be "auto" or "manual"');
        }
        return await post('/api/mode', { mode });
    },

    /**
     * Get all lamp curves
     * @returns {Promise<Object>} Curves data
     */
    async getCurves() {
        return await get('/api/curves');
    },

    /**
     * Update a specific curve for a channel
     * @param {number} channel - Channel number (1-4)
     * @param {Object} data - Curve data { curve: [...], enabled: boolean }
     * @returns {Promise<Object>} Response data
     */
    async updateCurve(channel, data) {
        return await put(`/api/curves/${channel}`, data);
    },

    /**
     * Get curve preview (24h interpolated intensities)
     * @returns {Promise<Object>} Preview data
     */
    async getCurvePreview() {
        return await get('/api/curves/preview');
    },

    /**
     * Get current curve intensities for all channels
     * @returns {Promise<Object>} Current intensities by channel
     */
    async getCurveIntensities() {
        return await get('/api/curves/intensities');
    },

    // ==========================================
    // Curve Presets API (v6.8)
    // ==========================================

    /**
     * Get all curve presets
     * @returns {Promise<Object>} List of presets
     */
    async getCurvePresets() {
        return await get('/api/curves/presets');
    },

    /**
     * Create a new curve preset from current curves
     * @param {string} name - Preset name
     * @param {string} description - Optional description
     * @returns {Promise<Object>} Created preset data
     */
    async createCurvePreset(name, description = '') {
        return await post('/api/curves/presets', { name, description });
    },

    /**
     * Update a curve preset (rename or change description)
     * @param {number} presetId - Preset ID
     * @param {Object} data - { name?: string, description?: string }
     * @returns {Promise<Object>} Updated preset data
     */
    async updateCurvePreset(presetId, data) {
        return await put(`/api/curves/presets/${presetId}`, data);
    },

    /**
     * Delete a curve preset
     * @param {number} presetId - Preset ID
     * @returns {Promise<Object>} Response data
     */
    async deleteCurvePreset(presetId) {
        return await request(`/api/curves/presets/${presetId}`, { method: 'DELETE' });
    },

    /**
     * Apply a curve preset to all lamp channels
     * @param {number} presetId - Preset ID
     * @returns {Promise<Object>} Response with updated curves
     */
    async applyCurvePreset(presetId) {
        return await post(`/api/curves/presets/${presetId}/apply`, {});
    },

    /**
     * Get sensor logs with automatic downsampling
     * Backend applies intelligent downsampling based on time range:
     * - 0-4h: raw data, 4-24h: 5min avg, 1-7d: 15min avg, 7-30d: 30min avg, >30d: 1h avg
     * @param {string} type - Sensor type ('temperature' | 'humidity')
     * @param {number} hours - Hours of history to fetch (default: 24, no limit!)
     * @returns {Promise<Object>} Sensor readings (downsampled)
     */
    async getSensorLogs(type, hours = 24) {
        return await get(`/api/logs/sensors?type=${type}&hours=${hours}`);
    },

    /**
     * Get lamp logs for a specific channel with automatic downsampling
     * Backend applies intelligent downsampling based on time range:
     * - 0-4h: raw data, 4-24h: 5min avg, 1-7d: 15min avg, 7-30d: 30min avg, >30d: 1h avg
     * @param {number} channel - Channel number (1-4)
     * @param {number} hours - Hours of history (default: 24, no limit!)
     * @returns {Promise<Object>} Lamp intensity logs (downsampled)
     */
    async getLampLogs(channel, hours = 24) {
        return await get(`/api/logs/lamps?channel=${channel}&hours=${hours}`);
    },

    /**
     * Get smart plug logs with automatic downsampling
     * Backend applies intelligent downsampling based on time range:
     * - 0-4h: raw data, 4-24h: 5min avg, 1-7d: 15min avg, 7-30d: 30min avg, >30d: 1h avg
     * @param {number} hours - Hours of history (default: 24, no limit!)
     * @returns {Promise<Object>} Plug power consumption logs (downsampled)
     */
    async getPlugLogs(hours = 24) {
        return await get(`/api/logs/plugs?hours=${hours}`);
    },

    /**
     * Get system event logs
     * @param {number} hours - Hours of history (default: 24)
     * @param {number} limit - Maximum records (default: 100)
     * @returns {Promise<Object>} System events
     */
    async getEventLogs(hours = 24, limit = 100) {
        return await get(`/api/logs/events?hours=${hours}&limit=${limit}`);
    },

    // ==========================================
    // Room Environment API (v6.4)
    // ==========================================

    /**
     * Get room environment status (temperature, humidity, dehumidifier)
     * @returns {Promise<Object>} Room status data
     */
    async getRoomStatus() {
        return await get('/api/room');
    },

    /**
     * Control dehumidifier (manual mode)
     * @param {string} action - 'on' or 'off'
     * @returns {Promise<Object>} Response data
     */
    async controlDehumidifier(action) {
        if (action !== 'on' && action !== 'off') {
            throw new Error('Action must be "on" or "off"');
        }
        return await post('/api/room/dehumidifier', { action });
    },

    /**
     * Save room configuration (auto-control settings)
     * @param {Object} config - Configuration object
     * @param {boolean} config.enabled - Enable auto-control
     * @param {number} config.target - Target humidity percentage
     * @param {number} config.threshold_high - High threshold (turn on)
     * @param {number} config.threshold_low - Low threshold (turn off)
     * @param {boolean} config.time_schedule_enabled - Enable time-based scheduling
     * @returns {Promise<Object>} Response data
     */
    async saveRoomConfig(config) {
        return await post('/api/room/config', config);
    },

    // ==========================================
    // Time Schedule API (v6.8 - Feature #2)
    // ==========================================

    /**
     * Get all time schedules for dehumidifier
     * @returns {Promise<Object>} Schedules list and active schedule
     */
    async getSchedules() {
        return await get('/api/room/schedules');
    },

    /**
     * Create a new time schedule
     * @param {Object} schedule - Schedule data
     * @param {string} schedule.start_time - Start time "HH:MM"
     * @param {string} schedule.end_time - End time "HH:MM"
     * @param {string} schedule.target_state - "on" or "off" (default: "on")
     * @param {boolean} schedule.enabled - Whether schedule is active (default: true)
     * @returns {Promise<Object>} Created schedule with ID
     */
    async createSchedule(schedule) {
        return await post('/api/room/schedules', schedule);
    },

    /**
     * Update an existing time schedule
     * @param {number} scheduleId - Schedule ID
     * @param {Object} updates - Fields to update
     * @returns {Promise<Object>} Success response
     */
    async updateSchedule(scheduleId, updates) {
        return await put(`/api/room/schedules/${scheduleId}`, updates);
    },

    /**
     * Delete a time schedule
     * @param {number} scheduleId - Schedule ID
     * @returns {Promise<Object>} Success response
     */
    async deleteSchedule(scheduleId) {
        return await request(`/api/room/schedules/${scheduleId}`, { method: 'DELETE' });
    },

    // ==========================================
    // Costs Management API (v6.3)
    // ==========================================

    /**
     * Get energy costs for a specific period
     * @param {string} period - Period preset ('today', 'week', 'month')
     * @param {string} dateFrom - Custom start date (YYYY-MM-DD)
     * @param {string} dateTo - Custom end date (YYYY-MM-DD)
     * @returns {Promise<Object>} Costs data with devices breakdown
     */
    async getCosts(period = 'today', dateFrom = null, dateTo = null) {
        let url = `/api/costs?period=${period}`;
        if (dateFrom && dateTo) {
            url = `/api/costs?from=${dateFrom}&to=${dateTo}`;
        }
        return await get(url);
    },

    /**
     * Get current kWh price configuration
     * @returns {Promise<Object>} Configuration data
     */
    async getCostsConfig() {
        return await get('/api/costs/config');
    },

    /**
     * Save kWh price configuration
     * @param {number} kwhPrice - Price per kWh in EUR
     * @returns {Promise<Object>} Response data
     */
    async saveCostsConfig(kwhPrice) {
        return await post('/api/costs/config', { kwh_price: kwhPrice });
    },

    // ==========================================
    // Camera API (v6.5)
    // ==========================================

    /**
     * Get camera snapshot URL (for img src)
     * Returns the URL, not the image data
     * @returns {string} Snapshot URL with cache-busting parameter
     */
    getCameraSnapshotUrl() {
        return `/api/camera/snapshot?t=${Date.now()}`;
    },

    /**
     * Get camera status
     * @returns {Promise<Object>} Camera status data
     */
    async getCameraStatus() {
        return await get('/api/camera/status');
    },

    /**
     * Update camera configuration
     * @param {Object} config - Configuration object
     * @returns {Promise<Object>} Response data
     */
    async updateCameraConfig(config) {
        return await post('/api/camera/config', config);
    },

    /**
     * Get timelapse configuration
     * @returns {Promise<Object>} Timelapse config data
     */
    async getTimelapseConfig() {
        return await get('/api/camera/timelapse/config');
    },

    /**
     * Update timelapse configuration
     * @param {Object} config - Timelapse configuration
     * @returns {Promise<Object>} Response data
     */
    async updateTimelapseConfig(config) {
        return await post('/api/camera/timelapse/config', config);
    },

    /**
     * Get list of timelapse images
     * @param {number} limit - Maximum number of images
     * @returns {Promise<Object>} List of timelapse images
     */
    async getTimelapseImages(limit = 50) {
        return await get(`/api/camera/timelapse/images?limit=${limit}`);
    },

    // ==========================================
    // Version API (v6.16.0)
    // ==========================================

    /**
     * Get GrowPi version information
     * @returns {Promise<Object>} Version data { version, version_display, api_version }
     */
    async getVersion() {
        return await get('/api/version');
    }
};

