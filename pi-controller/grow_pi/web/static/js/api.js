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

    /**
     * Get sensor logs
     * @param {string} type - Sensor type ('temperature' | 'humidity')
     * @param {number} hours - Hours of history to fetch (default: 24)
     * @param {number} limit - Maximum number of records (default: 1000)
     * @returns {Promise<Object>} Sensor readings
     */
    async getSensorLogs(type, hours = 24, limit = 1000) {
        return await get(`/api/logs/sensors?type=${type}&hours=${hours}&limit=${limit}`);
    },

    /**
     * Get lamp logs for a specific channel
     * @param {number} channel - Channel number (1-4)
     * @param {number} hours - Hours of history (default: 24)
     * @param {number} limit - Maximum records (default: 1000)
     * @returns {Promise<Object>} Lamp intensity logs
     */
    async getLampLogs(channel, hours = 24, limit = 1000) {
        return await get(`/api/logs/lamps?channel=${channel}&hours=${hours}&limit=${limit}`);
    },

    /**
     * Get smart plug logs
     * @param {number} hours - Hours of history (default: 24)
     * @param {number} limit - Maximum records (default: 1000)
     * @returns {Promise<Object>} Plug power consumption logs
     */
    async getPlugLogs(hours = 24, limit = 1000) {
        return await get(`/api/logs/plugs?hours=${hours}&limit=${limit}`);
    },

    /**
     * Get system event logs
     * @param {number} hours - Hours of history (default: 24)
     * @param {number} limit - Maximum records (default: 100)
     * @returns {Promise<Object>} System events
     */
    async getEventLogs(hours = 24, limit = 100) {
        return await get(`/api/logs/events?hours=${hours}&limit=${limit}`);
    }
};

