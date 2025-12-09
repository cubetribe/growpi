/**
 * Timelapse Module - Timelapse Camera Configuration & Gallery
 * Handles timelapse capture settings and image browsing
 *
 * Part of GrowPi v6.17.0
 * @module timelapse
 */

import { GrowPiAPI } from '../api.js';

// ==========================================
// DOM Elements
// ==========================================
let timelapseToggle = null;
let intervalInput = null;
let brightnessThresholdInput = null;
let skipDarkToggle = null;
let btnSaveTimelapseConfig = null;
let btnTestBrightness = null;
let brightnessTestResult = null;
let folderSelect = null;
let imageGallery = null;
let btnRefreshGallery = null;
let storageInfo = null;

// ==========================================
// State
// ==========================================
let refreshInterval = null;
let currentConfig = null;

// ==========================================
// Public API
// ==========================================

export function initTimelapseModule() {
    console.log('[Timelapse] Initializing timelapse module...');

    // Get DOM elements
    timelapseToggle = document.getElementById('timelapseToggle');
    intervalInput = document.getElementById('timelapseInterval');
    brightnessThresholdInput = document.getElementById('brightnessThreshold');
    skipDarkToggle = document.getElementById('skipDarkToggle');
    btnSaveTimelapseConfig = document.getElementById('btnSaveTimelapseConfig');
    btnTestBrightness = document.getElementById('btnTestBrightness');
    brightnessTestResult = document.getElementById('brightnessTestResult');
    folderSelect = document.getElementById('timelapseFolderSelect');
    imageGallery = document.getElementById('timelapseGallery');
    btnRefreshGallery = document.getElementById('btnRefreshGallery');
    storageInfo = document.getElementById('timelapseStorageInfo');

    if (!timelapseToggle) {
        console.log('[Timelapse] Timelapse elements not found - module disabled');
        return;
    }

    // Setup event listeners
    setupEventListeners();

    // Initial fetch
    fetchTimelapseStats();
    fetchFolders();

    // Auto-refresh stats every 30 seconds
    refreshInterval = setInterval(() => {
        fetchTimelapseStats();
    }, 30000);

    console.log('[Timelapse] Module initialized');
}

export function cleanupTimelapseModule() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
    console.log('[Timelapse] Module cleaned up');
}

// ==========================================
// Configuration Management
// ==========================================

async function fetchTimelapseStats() {
    try {
        const data = await GrowPiAPI.getTimelapseStats();

        if (data.success) {
            currentConfig = data.config;

            // Update UI with config values
            updateConfigUI(data.config);

            // Update storage info
            if (storageInfo) {
                storageInfo.textContent = `${data.storage_size_mb} MB (${data.total_images} Bilder)`;
            }

            // Update running status indicator
            updateRunningStatus(data.is_running);
        }
    } catch (error) {
        console.error('[Timelapse] Stats fetch error:', error);
    }
}

function updateConfigUI(config) {
    if (timelapseToggle) {
        timelapseToggle.classList.toggle('enabled', config.enabled);
    }
    if (intervalInput) {
        intervalInput.value = config.interval_seconds;
    }
    if (brightnessThresholdInput) {
        brightnessThresholdInput.value = config.brightness_threshold;
    }
    if (skipDarkToggle) {
        skipDarkToggle.classList.toggle('enabled', config.skip_dark_images);
    }
}

function updateRunningStatus(isRunning) {
    const statusIndicator = document.getElementById('timelapseStatus');
    if (statusIndicator) {
        statusIndicator.textContent = isRunning ? 'Aktiv' : 'Inaktiv';
        statusIndicator.className = `timelapse-status ${isRunning ? 'running' : 'stopped'}`;
    }
}

async function saveTimelapseConfig() {
    try {
        const config = {
            enabled: timelapseToggle?.classList.contains('enabled') || false,
            interval_seconds: parseInt(intervalInput?.value || 300),
            brightness_threshold: parseInt(brightnessThresholdInput?.value || 15),
            skip_dark_images: skipDarkToggle?.classList.contains('enabled') ?? true
        };

        console.log('[Timelapse] Saving config:', config);

        const data = await GrowPiAPI.updateTimelapseConfig(config);

        if (data.success) {
            window.showSuccess?.('Timelapse-Konfiguration gespeichert!');
            // Refresh stats to get updated running status
            setTimeout(fetchTimelapseStats, 500);
        } else {
            window.showError?.(data.error || 'Fehler beim Speichern');
        }
    } catch (error) {
        console.error('[Timelapse] Config save error:', error);
        window.showError?.('Verbindungsfehler');
    }
}

// ==========================================
// Brightness Test
// ==========================================

async function testBrightness() {
    if (brightnessTestResult) {
        brightnessTestResult.innerHTML = '<span class="testing">Teste...</span>';
        brightnessTestResult.className = 'brightness-test-result testing';
    }

    try {
        const data = await GrowPiAPI.testBrightness();

        if (data.success && brightnessTestResult) {
            const b = data.brightness;
            const status = b.is_too_dark ? 'ZU DUNKEL' : 'OK';
            const statusClass = b.is_too_dark ? 'too-dark' : 'ok';

            brightnessTestResult.innerHTML = `
                <span class="status ${statusClass}">${status}</span>
                <div class="details">
                    <span>Helligkeit: ${b.average_brightness}/255</span>
                    <span>Helle Pixel: ${b.bright_pixel_percent}%</span>
                    <span>Schwelle: ${b.threshold}</span>
                </div>
                <div class="verdict">
                    ${data.would_save ? 'Bild w\u00fcrde gespeichert' : 'Bild wird \u00fcbersprungen'}
                </div>
            `;
            brightnessTestResult.className = `brightness-test-result ${statusClass}`;
        } else if (!data.success) {
            brightnessTestResult.innerHTML = `<span class="error">${data.error || 'Fehler'}</span>`;
            brightnessTestResult.className = 'brightness-test-result error';
        }
    } catch (error) {
        console.error('[Timelapse] Brightness test error:', error);
        if (brightnessTestResult) {
            brightnessTestResult.innerHTML = '<span class="error">Verbindungsfehler</span>';
            brightnessTestResult.className = 'brightness-test-result error';
        }
    }
}

// ==========================================
// Gallery Management
// ==========================================

async function fetchFolders() {
    try {
        const data = await GrowPiAPI.getTimelapseFolders();

        if (data.success && folderSelect) {
            folderSelect.innerHTML = '<option value="">Alle Ordner</option>';

            if (data.folders && data.folders.length > 0) {
                data.folders.forEach(folder => {
                    const option = document.createElement('option');
                    option.value = folder.name;
                    option.textContent = `${folder.name} (${folder.image_count} Bilder)`;
                    folderSelect.appendChild(option);
                });
            }

            // Load images
            fetchImages();
        }
    } catch (error) {
        console.error('[Timelapse] Folders fetch error:', error);
    }
}

async function fetchImages() {
    const selectedFolder = folderSelect?.value || null;

    if (imageGallery) {
        imageGallery.innerHTML = '<div class="gallery-loading">Lade Bilder...</div>';
    }

    try {
        const data = await GrowPiAPI.getTimelapseImages(50, selectedFolder);

        if (data.success && imageGallery) {
            if (!data.images || data.images.length === 0) {
                imageGallery.innerHTML = `
                    <div class="gallery-empty">
                        <span>Keine Bilder vorhanden</span>
                        <small>Timelapse aktivieren um Bilder aufzunehmen</small>
                    </div>
                `;
                return;
            }

            imageGallery.innerHTML = data.images.map(img => `
                <div class="gallery-item" data-folder="${img.folder}" data-filename="${img.filename}">
                    <img src="${img.path}" alt="${img.timestamp}" loading="lazy">
                    <div class="gallery-item-info">
                        <span class="time">${formatTimestamp(img.timestamp)}</span>
                        <span class="date">${img.folder}</span>
                    </div>
                </div>
            `).join('');

            // Add click handlers for lightbox
            imageGallery.querySelectorAll('.gallery-item').forEach(item => {
                item.addEventListener('click', () => {
                    openLightbox(item.dataset.folder, item.dataset.filename);
                });
            });
        }
    } catch (error) {
        console.error('[Timelapse] Images fetch error:', error);
        if (imageGallery) {
            imageGallery.innerHTML = '<div class="gallery-empty error">Fehler beim Laden</div>';
        }
    }
}

function formatTimestamp(ts) {
    // Format: YYYYMMDD_HHMMSS -> HH:MM:SS
    if (ts && ts.length >= 15) {
        return `${ts.slice(9, 11)}:${ts.slice(11, 13)}:${ts.slice(13, 15)}`;
    }
    return ts;
}

function openLightbox(folder, filename) {
    const url = GrowPiAPI.getTimelapseImageUrl(folder, filename);

    // Create lightbox overlay
    const overlay = document.createElement('div');
    overlay.className = 'timelapse-lightbox';
    overlay.innerHTML = `
        <div class="lightbox-content">
            <img src="${url}" alt="${filename}">
            <div class="lightbox-info">
                <span class="folder">${folder}</span>
                <span class="filename">${filename}</span>
            </div>
            <button class="lightbox-close" aria-label="Schlie\u00dfen">&times;</button>
        </div>
    `;

    document.body.appendChild(overlay);

    // Prevent body scroll
    document.body.style.overflow = 'hidden';

    // Close handlers
    const closeHandler = (e) => {
        if (e.target === overlay || e.target.classList.contains('lightbox-close')) {
            overlay.remove();
            document.body.style.overflow = '';
        }
    };

    overlay.addEventListener('click', closeHandler);

    // ESC key to close
    const keyHandler = (e) => {
        if (e.key === 'Escape') {
            overlay.remove();
            document.body.style.overflow = '';
            document.removeEventListener('keydown', keyHandler);
        }
    };
    document.addEventListener('keydown', keyHandler);
}

// ==========================================
// Event Listeners
// ==========================================

function setupEventListeners() {
    // Toggle buttons
    timelapseToggle?.addEventListener('click', () => {
        timelapseToggle.classList.toggle('enabled');
    });

    skipDarkToggle?.addEventListener('click', () => {
        skipDarkToggle.classList.toggle('enabled');
    });

    // Save button
    btnSaveTimelapseConfig?.addEventListener('click', saveTimelapseConfig);

    // Test brightness button
    btnTestBrightness?.addEventListener('click', testBrightness);

    // Folder select change
    folderSelect?.addEventListener('change', fetchImages);

    // Refresh gallery button
    btnRefreshGallery?.addEventListener('click', () => {
        fetchFolders();
    });

    // Input validation
    intervalInput?.addEventListener('change', () => {
        let val = parseInt(intervalInput.value);
        if (val < 30) intervalInput.value = 30;
        if (val > 600) intervalInput.value = 600;
    });

    brightnessThresholdInput?.addEventListener('change', () => {
        let val = parseInt(brightnessThresholdInput.value);
        if (val < 0) brightnessThresholdInput.value = 0;
        if (val > 255) brightnessThresholdInput.value = 255;
    });
}

// Export for external use
export { testBrightness, fetchImages, fetchTimelapseStats };
