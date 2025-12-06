/**
 * GrowPi Global State Management
 * Centralized application state with pub/sub pattern for reactive updates
 *
 * Usage:
 *   import { GrowPiState } from './state.js';
 *   GrowPiState.setMode('auto');
 *   GrowPiState.subscribe('mode', (newMode) => console.log(newMode));
 *   const mode = GrowPiState.getMode();
 */

// ==========================================
// Private State Storage
// ==========================================

const state = {
    // Control mode: 'auto' (curve-based) or 'manual' (slider control)
    currentMode: 'auto',

    // Lamp curves data by channel
    // Format: { 1: { channel: 1, name: 'Far Red', curve: [...], enabled: true }, ... }
    curvesData: {},

    // Active tab index for curve editor (which channel is focused)
    activeChannel: 1,

    // Current lamp states from API
    // Format: [{ channel: 1, intensity: 50 }, ...]
    lampStates: [],

    // Sensor readings
    temperature: null,
    humidity: null,

    // System status
    online: false,
    lastUpdate: null,

    // History chart range (in hours)
    historyRange: 24,

    // Curve preview data (24h interpolated)
    previewData: []
};

// Subscribers for state changes
// Format: { 'currentMode': [callback1, callback2], ... }
const subscribers = {};

/**
 * Notify all subscribers of a state property change
 * @private
 */
function notify(key, value) {
    if (subscribers[key]) {
        subscribers[key].forEach(callback => {
            try {
                callback(value);
            } catch (error) {
                console.error(`Subscriber error for ${key}:`, error);
            }
        });
    }
}

/**
 * Set a state value and notify subscribers
 * @private
 */
function setState(key, value) {
    const oldValue = state[key];
    state[key] = value;

    // Only notify if value actually changed
    if (JSON.stringify(oldValue) !== JSON.stringify(value)) {
        notify(key, value);
    }
}

// ==========================================
// Public API
// ==========================================

export const GrowPiState = {
    /**
     * Subscribe to state changes for a specific property
     * @param {string} key - State property name
     * @param {Function} callback - Callback function to invoke on change
     * @returns {Function} Unsubscribe function
     */
    subscribe(key, callback) {
        if (!subscribers[key]) {
            subscribers[key] = [];
        }
        subscribers[key].push(callback);

        // Return unsubscribe function
        return () => {
            const index = subscribers[key].indexOf(callback);
            if (index > -1) {
                subscribers[key].splice(index, 1);
            }
        };
    },

    /**
     * Get current mode (auto/manual)
     * @returns {string} Current mode
     */
    getMode() {
        return state.currentMode;
    },

    /**
     * Set control mode
     * @param {string} mode - 'auto' or 'manual'
     */
    setMode(mode) {
        if (mode !== 'auto' && mode !== 'manual') {
            console.warn('Invalid mode:', mode);
            return;
        }
        setState('currentMode', mode);
    },

    /**
     * Get all curves data
     * @returns {Object} Curves data by channel
     */
    getCurvesData() {
        return { ...state.curvesData };
    },

    /**
     * Set curves data
     * @param {Object} curvesData - Curves data object
     */
    setCurvesData(curvesData) {
        setState('curvesData', curvesData);
    },

    /**
     * Get curve for a specific channel
     * @param {number} channel - Channel number (1-4)
     * @returns {Object|null} Curve data or null if not found
     */
    getCurve(channel) {
        return state.curvesData[channel] || null;
    },

    /**
     * Update a specific curve
     * @param {number} channel - Channel number
     * @param {Object} curveData - Curve data
     */
    updateCurve(channel, curveData) {
        const newCurvesData = { ...state.curvesData };
        newCurvesData[channel] = curveData;
        setState('curvesData', newCurvesData);
    },

    /**
     * Get active channel (for curve editor)
     * @returns {number} Active channel number
     */
    getActiveChannel() {
        return state.activeChannel;
    },

    /**
     * Set active channel
     * @param {number} channel - Channel number (1-4)
     */
    setActiveChannel(channel) {
        if (channel >= 1 && channel <= 4) {
            setState('activeChannel', channel);
        }
    },

    /**
     * Get lamp states
     * @returns {Array} Array of lamp state objects
     */
    getLampStates() {
        return [...state.lampStates];
    },

    /**
     * Set lamp states
     * @param {Array} lampStates - Array of lamp state objects
     */
    setLampStates(lampStates) {
        setState('lampStates', lampStates);
    },

    /**
     * Get lamp state for a specific channel
     * @param {number} channel - Channel number
     * @returns {Object|null} Lamp state or null
     */
    getLampState(channel) {
        return state.lampStates.find(lamp => lamp.channel === channel) || null;
    },

    /**
     * Get temperature
     * @returns {number|null} Temperature in °C
     */
    getTemperature() {
        return state.temperature;
    },

    /**
     * Set temperature
     * @param {number} temperature - Temperature value
     */
    setTemperature(temperature) {
        setState('temperature', temperature);
    },

    /**
     * Get humidity
     * @returns {number|null} Humidity in %
     */
    getHumidity() {
        return state.humidity;
    },

    /**
     * Set humidity
     * @param {number} humidity - Humidity value
     */
    setHumidity(humidity) {
        setState('humidity', humidity);
    },

    /**
     * Get online status
     * @returns {boolean} Online status
     */
    isOnline() {
        return state.online;
    },

    /**
     * Set online status
     * @param {boolean} online - Online status
     */
    setOnline(online) {
        setState('online', online);
    },

    /**
     * Get last update timestamp
     * @returns {Date|null} Last update time
     */
    getLastUpdate() {
        return state.lastUpdate;
    },

    /**
     * Set last update timestamp
     * @param {Date} timestamp - Update timestamp
     */
    setLastUpdate(timestamp) {
        setState('lastUpdate', timestamp);
    },

    /**
     * Get history range (in hours)
     * @returns {number} Hours
     */
    getHistoryRange() {
        return state.historyRange;
    },

    /**
     * Set history range
     * @param {number} hours - Number of hours
     */
    setHistoryRange(hours) {
        setState('historyRange', hours);
    },

    /**
     * Get preview data
     * @returns {Array} Preview data array
     */
    getPreviewData() {
        return [...state.previewData];
    },

    /**
     * Set preview data
     * @param {Array} previewData - Preview data array
     */
    setPreviewData(previewData) {
        setState('previewData', previewData);
    },

    /**
     * Get entire state (read-only copy)
     * @returns {Object} Complete state object
     */
    getState() {
        return JSON.parse(JSON.stringify(state));
    },

    /**
     * Reset state to defaults
     */
    reset() {
        Object.keys(state).forEach(key => {
            const defaultValue = {
                currentMode: 'auto',
                curvesData: {},
                activeChannel: 1,
                lampStates: [],
                temperature: null,
                humidity: null,
                online: false,
                lastUpdate: null,
                historyRange: 24,
                previewData: []
            }[key];

            setState(key, defaultValue);
        });
    }
};

