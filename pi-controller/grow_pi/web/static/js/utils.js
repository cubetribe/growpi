/**
 * GrowPi Utility Functions
 * Common helpers for UI interactions and tab management
 */

// DOM Elements for Notifications
const errorMsg = document.getElementById('errorMsg');
const successMsg = document.getElementById('successMsg');

/**
 * Show error notification
 * @param {string} message - Error message to display
 */
export function showError(message) {
    if (errorMsg) {
        errorMsg.textContent = message;
        errorMsg.classList.add('show');
        setTimeout(() => errorMsg.classList.remove('show'), 5000);
    } else {
        console.error('Error:', message);
    }
}

/**
 * Show success notification
 * @param {string} message - Success message to display
 */
export function showSuccess(message) {
    if (successMsg) {
        successMsg.textContent = message;
        successMsg.classList.add('show');
        setTimeout(() => successMsg.classList.remove('show'), 3000);
    } else {
        console.log('Success:', message);
    }
}

/**
 * Setup tab switching logic
 * Handles active class toggling for tab buttons and content
 * Also triggers data loading for specific tabs when switched to
 */
export function setupTabs() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all buttons and content
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));

            // Add active class to clicked button and corresponding content
            btn.classList.add('active');
            const tabId = btn.dataset.tab;
            const content = document.getElementById(`tab-${tabId}`);
            if (content) {
                content.classList.add('active');
            }

            // Load data when switching to specific tabs
            if (tabId === 'curves') {
                // Dynamically import and call fetchCurves
                import('./modules/curves.js').then(module => {
                    module.fetchCurves();
                }).catch(err => {
                    console.error('Failed to load curves module:', err);
                });
            }
        });
    });
}

/**
 * Format current time
 * @returns {string} Formatted time string (HH:MM:SS)
 */
export function formatTime() {
    return new Date().toLocaleTimeString('de-DE', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
    });
}

/**
 * Debounce function for limiting event firing frequency
 * @param {Function} fn - Function to debounce
 * @param {number} delay - Delay in ms
 * @param {string} key - Unique key for the timer
 */
const debounceTimers = {};
export function debounce(fn, delay, key) {
    clearTimeout(debounceTimers[key]);
    debounceTimers[key] = setTimeout(fn, delay);
}

/**
 * Setup mobile navigation (hamburger menu)
 * Handles side drawer for tabs on mobile devices
 */
export function setupMobileNav() {
    const toggle = document.getElementById('mobileNavToggle');
    const tabs = document.getElementById('mainTabs');
    const overlay = document.getElementById('mobileNavOverlay');

    if (!toggle || !tabs || !overlay) return;

    // Toggle menu
    toggle.addEventListener('click', () => {
        const isOpen = tabs.classList.contains('mobile-open');

        if (isOpen) {
            tabs.classList.remove('mobile-open');
            overlay.classList.remove('active');
            toggle.classList.remove('active');
        } else {
            tabs.classList.add('mobile-open');
            overlay.classList.add('active');
            toggle.classList.add('active');
        }
    });

    // Close on overlay click
    overlay.addEventListener('click', () => {
        tabs.classList.remove('mobile-open');
        overlay.classList.remove('active');
        toggle.classList.remove('active');
    });

    // Close on tab click
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            tabs.classList.remove('mobile-open');
            overlay.classList.remove('active');
            toggle.classList.remove('active');
        });
    });
}
