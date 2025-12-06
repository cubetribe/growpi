/**
 * GrowPi Accordion Module
 * Handles collapsible sections with localStorage persistence
 *
 * Feature #3: Collapsible Sections (Accordion)
 * Date: 2025-12-06
 */

// Storage key prefix for localStorage
const STORAGE_PREFIX = 'growpi-section-';

/**
 * Get the collapsed state from localStorage
 * @param {string} sectionId - The section identifier
 * @returns {boolean} - True if collapsed, false if expanded
 */
function getSectionState(sectionId) {
    const stored = localStorage.getItem(STORAGE_PREFIX + sectionId);
    // Default: both sections are expanded (not collapsed)
    return stored === 'collapsed';
}

/**
 * Save the collapsed state to localStorage
 * @param {string} sectionId - The section identifier
 * @param {boolean} isCollapsed - Whether the section is collapsed
 */
function saveSectionState(sectionId, isCollapsed) {
    if (isCollapsed) {
        localStorage.setItem(STORAGE_PREFIX + sectionId, 'collapsed');
    } else {
        localStorage.removeItem(STORAGE_PREFIX + sectionId);
    }
}

/**
 * Toggle a collapsible section
 * @param {HTMLElement} section - The section element
 */
function toggleSection(section) {
    const sectionId = section.dataset.sectionId;
    const isCurrentlyCollapsed = section.classList.contains('collapsed');

    if (isCurrentlyCollapsed) {
        // Expand
        section.classList.remove('collapsed');
        saveSectionState(sectionId, false);
    } else {
        // Collapse
        section.classList.add('collapsed');
        saveSectionState(sectionId, true);
    }
}

/**
 * Initialize all collapsible sections
 * - Attaches click handlers to headers
 * - Restores saved state from localStorage
 */
export function initAccordion() {
    const collapsibleSections = document.querySelectorAll('.collapsible-section');

    collapsibleSections.forEach(section => {
        const sectionId = section.dataset.sectionId;
        const header = section.querySelector('.collapsible-header');

        if (!header || !sectionId) {
            console.warn('Collapsible section missing header or sectionId:', section);
            return;
        }

        // Restore state from localStorage
        const isCollapsed = getSectionState(sectionId);
        if (isCollapsed) {
            section.classList.add('collapsed');
        }

        // Add click handler
        header.addEventListener('click', (e) => {
            e.preventDefault();
            toggleSection(section);
        });

        // Add keyboard accessibility
        header.setAttribute('role', 'button');
        header.setAttribute('tabindex', '0');
        header.setAttribute('aria-expanded', !isCollapsed);

        header.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                toggleSection(section);
                header.setAttribute('aria-expanded', !section.classList.contains('collapsed'));
            }
        });
    });

    console.log(`Accordion: Initialized ${collapsibleSections.length} collapsible sections`);
}

/**
 * Programmatically expand a section
 * @param {string} sectionId - The section identifier
 */
export function expandSection(sectionId) {
    const section = document.querySelector(`[data-section-id="${sectionId}"]`);
    if (section && section.classList.contains('collapsed')) {
        section.classList.remove('collapsed');
        saveSectionState(sectionId, false);

        const header = section.querySelector('.collapsible-header');
        if (header) {
            header.setAttribute('aria-expanded', 'true');
        }
    }
}

/**
 * Programmatically collapse a section
 * @param {string} sectionId - The section identifier
 */
export function collapseSection(sectionId) {
    const section = document.querySelector(`[data-section-id="${sectionId}"]`);
    if (section && !section.classList.contains('collapsed')) {
        section.classList.add('collapsed');
        saveSectionState(sectionId, true);

        const header = section.querySelector('.collapsible-header');
        if (header) {
            header.setAttribute('aria-expanded', 'false');
        }
    }
}

/**
 * Expand all collapsible sections
 */
export function expandAll() {
    document.querySelectorAll('.collapsible-section.collapsed').forEach(section => {
        const sectionId = section.dataset.sectionId;
        if (sectionId) {
            expandSection(sectionId);
        }
    });
}

/**
 * Collapse all collapsible sections
 */
export function collapseAll() {
    document.querySelectorAll('.collapsible-section:not(.collapsed)').forEach(section => {
        const sectionId = section.dataset.sectionId;
        if (sectionId) {
            collapseSection(sectionId);
        }
    });
}
