/**
 * Camera Module - Livestream for Start Tab
 * Handles webcam display with ~2 FPS polling
 */

import { GrowPiAPI } from '../api.js';

// ==========================================
// Configuration
// ==========================================
const REFRESH_INTERVAL_MS = 10000; // 0.1 FPS = 10s between frames (CPU-Optimierung)
const STATUS_CHECK_INTERVAL_MS = 10000; // Check camera status every 10s

// ==========================================
// State
// ==========================================
let refreshInterval = null;
let statusCheckInterval = null;
let isStreaming = false;
let cameraAvailable = false;

// ==========================================
// DOM Elements
// ==========================================
let cameraContainer = null;
let cameraImage = null;
let cameraStatus = null;
let cameraError = null;

// ==========================================
// Public API
// ==========================================

/**
 * Initialize camera module
 * Call this after DOM is ready
 */
export function initCameraModule() {
    console.log('[Camera] Initializing camera module...');

    // Get DOM elements
    cameraContainer = document.getElementById('cameraContainer');
    cameraImage = document.getElementById('cameraImage');
    cameraStatus = document.getElementById('cameraStatus');
    cameraError = document.getElementById('cameraError');

    if (!cameraContainer) {
        console.log('[Camera] Camera container not found - module disabled');
        return;
    }

    // Check initial camera status
    checkCameraStatus();

    // Start status monitoring
    statusCheckInterval = setInterval(checkCameraStatus, STATUS_CHECK_INTERVAL_MS);

    // Start streaming immediately if camera is available
    startStream();
}

/**
 * Cleanup camera module
 * Call when leaving the tab
 */
export function cleanupCameraModule() {
    console.log('[Camera] Cleaning up camera module...');
    stopStream();

    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
}

/**
 * Start the camera stream
 */
export function startStream() {
    if (isStreaming) return;

    console.log('[Camera] Starting stream...');
    isStreaming = true;

    // Initial frame
    refreshFrame();

    // Start polling
    refreshInterval = setInterval(refreshFrame, REFRESH_INTERVAL_MS);
}

/**
 * Stop the camera stream
 */
export function stopStream() {
    if (!isStreaming) return;

    console.log('[Camera] Stopping stream...');
    isStreaming = false;

    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// ==========================================
// Private Functions
// ==========================================

/**
 * Check camera availability
 */
async function checkCameraStatus() {
    try {
        const data = await GrowPiAPI.getCameraStatus();

        if (data.success) {
            cameraAvailable = data.available;

            if (cameraStatus) {
                if (cameraAvailable) {
                    cameraStatus.textContent = `${data.resolution || '1280x720'}`;
                    cameraStatus.classList.remove('offline');
                    cameraStatus.classList.add('online');
                } else {
                    cameraStatus.textContent = 'Nicht verfügbar';
                    cameraStatus.classList.remove('online');
                    cameraStatus.classList.add('offline');
                }
            }

            // Hide error message if camera is available
            if (cameraError && cameraAvailable) {
                cameraError.style.display = 'none';
            }
        }
    } catch (error) {
        console.error('[Camera] Status check failed:', error);
        cameraAvailable = false;

        if (cameraStatus) {
            cameraStatus.textContent = 'Fehler';
            cameraStatus.classList.remove('online');
            cameraStatus.classList.add('offline');
        }
    }
}

/**
 * Refresh the camera frame
 */
function refreshFrame() {
    if (!cameraImage || !isStreaming) return;

    // Create new image to preload
    const newImg = new Image();

    newImg.onload = () => {
        // Only update if we're still streaming
        if (isStreaming && cameraImage) {
            cameraImage.src = newImg.src;

            // Hide error, show image
            if (cameraError) cameraError.style.display = 'none';
            cameraImage.style.display = 'block';
        }
    };

    newImg.onerror = () => {
        // Show error message
        if (cameraError) {
            cameraError.textContent = 'Kamera nicht verfügbar';
            cameraError.style.display = 'block';
        }
        if (cameraImage) {
            cameraImage.style.display = 'none';
        }
    };

    // Load new frame with cache-busting
    newImg.src = GrowPiAPI.getCameraSnapshotUrl();
}

/**
 * Get current stream status
 */
export function getStreamStatus() {
    return {
        isStreaming,
        cameraAvailable,
        refreshInterval: REFRESH_INTERVAL_MS
    };
}
