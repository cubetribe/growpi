/**
 * Calendar Module - Grow Calendar & Daily Log
 * Handles grow phase tracking, daily logs, and calendar view
 *
 * Part of GrowPi v6.20 - Grow Calendar Feature
 * @module calendar
 */

import { GrowPiAPI } from '../api.js';
import { showError, showSuccess } from '../utils.js';

// ==========================================
// DOM Elements
// ==========================================
const calendarHeader = document.getElementById('calendarHeader');
const calendarGrid = document.getElementById('calendarGrid');
const currentGrowName = document.getElementById('currentGrowName');
const currentPhaseInfo = document.getElementById('currentPhaseInfo');
const phaseButtonSeedling = document.getElementById('phaseBtnSeedling');
const phaseButtonVeggie = document.getElementById('phaseBtnVeggie');
const phaseButtonBloom = document.getElementById('phaseBtnBloom');
const btnNewGrow = document.getElementById('btnNewGrow');
const btnPrevMonth = document.getElementById('btnPrevMonth');
const btnNextMonth = document.getElementById('btnNextMonth');
const monthYearLabel = document.getElementById('monthYearLabel');

// Events Section elements
const eventsSection = document.getElementById('eventsSection');
const eventsPhaseLabel = document.getElementById('eventsPhaseLabel');
const eventsList = document.getElementById('eventsList');
const btnAddEvent = document.getElementById('btnAddEvent');
const eventsCategoryFilters = document.getElementById('eventsCategoryFilters');

// Status Dashboard elements
const statusPhaseIcon = document.getElementById('statusPhaseIcon');
const statusPhaseName = document.getElementById('statusPhaseName');
const statusPhaseDay = document.getElementById('statusPhaseDay');
const statusGrowStart = document.getElementById('statusGrowStart');
const statusPhaseStart = document.getElementById('statusPhaseStart');
const btnEditGrowSettings = document.getElementById('btnEditGrowSettings');

// Actionable Grow Tip Banner elements
const growTipBanner = document.getElementById('growTipBanner');
const growTipIcon = document.getElementById('growTipIcon');
const growTipTitle = document.getElementById('growTipTitle');
const growTipDesc = document.getElementById('growTipDesc');
const growTipEnv = document.getElementById('growTipEnv');

// Modal elements
const dailyLogModal = document.getElementById('dailyLogModal');
const modalDate = document.getElementById('modalDate');
const modalPhaseInfo = document.getElementById('modalPhaseInfo');
const modalClose = document.getElementById('modalClose');
const btnSaveDailyLog = document.getElementById('btnSaveDailyLog');
const btnCancelLog = document.getElementById('btnCancelLog');

// Settings Modal elements
const growSettingsModal = document.getElementById('growSettingsModal');
const settingsModalClose = document.getElementById('settingsModalClose');
const settingsGrowName = document.getElementById('settingsGrowName');
const settingsGrowNameInput = document.getElementById('settingsGrowNameInput');
const settingsStrainInput = document.getElementById('settingsStrainInput');
const settingsGrowStartDate = document.getElementById('settingsGrowStartDate');
const settingsPhaseStartDate = document.getElementById('settingsPhaseStartDate');
const btnCancelSettings = document.getElementById('btnCancelSettings');
const btnSaveSettings = document.getElementById('btnSaveSettings');

// Add Event Modal elements
const addEventModal = document.getElementById('addEventModal');
const addEventModalClose = document.getElementById('addEventModalClose');
const newEventTitle = document.getElementById('newEventTitle');
const newEventDescription = document.getElementById('newEventDescription');
const newEventDayMin = document.getElementById('newEventDayMin');
const newEventDayMax = document.getElementById('newEventDayMax');
const newEventIcon = document.getElementById('newEventIcon');
const btnCancelAddEvent = document.getElementById('btnCancelAddEvent');
const btnSaveNewEvent = document.getElementById('btnSaveNewEvent');

// Form elements
const logFertilized = document.getElementById('logFertilized');
const logEcValue = document.getElementById('logEcValue');
const logPhValue = document.getElementById('logPhValue');
const logFertilizerNotes = document.getElementById('logFertilizerNotes');
const logWatered = document.getElementById('logWatered');
const logWaterAmount = document.getElementById('logWaterAmount');
const logNotes = document.getElementById('logNotes');
const logObservations = document.querySelectorAll('input[name="observations"]');

// ==========================================
// State
// ==========================================
let currentGrow = null;
let currentMonth = new Date();
let monthLogs = [];
let monthEvents = [];
let selectedDate = null;
let selectedDateEvents = []; // Events for the selected date
let currentPhaseEvents = []; // Events for current phase (for events section)
let selectedCategory = 'all'; // Current category filter
let todayTipsData = null; // Loaded today tips

// Phase translations
const PHASE_LABELS = {
    seedling: { de: 'Keim', en: 'Seedling', color: '#4ade80', icon: '🌱' },
    vegetative: { de: 'Wachstum', en: 'Veggie', color: '#60a5fa', icon: '🌿' },
    flowering: { de: 'Blüte', en: 'Bloom', color: '#c084fc', icon: '🌸' },
    drying: { de: 'Trocknung', en: 'Drying', color: '#f59e0b', icon: '🌾' },
    curing: { de: 'Aushärtung', en: 'Curing', color: '#fbbf24', icon: '🏺' }
};

// Observation labels
const OBSERVATIONS = [
    { key: 'burnt_tips', label: 'Verbrannte Spitzen', icon: '🔥' },
    { key: 'yellowing', label: 'Gelbe Blätter', icon: '💛' },
    { key: 'drooping', label: 'Hängende Blätter', icon: '🥀' },
    { key: 'curling', label: 'Eingerollte Blätter', icon: '🌀' },
    { key: 'spots', label: 'Flecken auf Blättern', icon: '🔵' },
    { key: 'pests', label: 'Schädlinge', icon: '🐛' },
    { key: 'mold', label: 'Schimmel', icon: '🦠' },
    { key: 'slow_growth', label: 'Langsames Wachstum', icon: '🐌' },
    { key: 'healthy', label: 'Alles gut', icon: '✅' }
];

// ==========================================
// Public API
// ==========================================
export function initCalendarTab() {
    console.log('[Calendar] Initializing calendar tab...');

    // Setup event listeners
    setupEventListeners();

    // Load active grow
    loadGrows();
}

export function cleanupCalendarTab() {
    console.log('[Calendar] Cleaning up calendar tab...');
    // Nothing to clean up yet (no intervals)
}

// ==========================================
// Event Listeners Setup
// ==========================================
function setupEventListeners() {
    // Navigation
    btnPrevMonth?.addEventListener('click', () => {
        currentMonth.setMonth(currentMonth.getMonth() - 1);
        renderCalendar();
    });

    btnNextMonth?.addEventListener('click', () => {
        currentMonth.setMonth(currentMonth.getMonth() + 1);
        renderCalendar();
    });

    // Phase buttons
    phaseButtonSeedling?.addEventListener('click', () => transitionPhase('seedling'));
    phaseButtonVeggie?.addEventListener('click', () => transitionPhase('vegetative'));
    phaseButtonBloom?.addEventListener('click', () => transitionPhase('flowering'));

    // New grow button
    btnNewGrow?.addEventListener('click', createNewGrow);

    // Modal controls
    modalClose?.addEventListener('click', closeDailyLogModal);
    btnCancelLog?.addEventListener('click', closeDailyLogModal);
    btnSaveDailyLog?.addEventListener('click', saveDailyLog);

    // Fertilized checkbox toggle
    logFertilized?.addEventListener('change', (e) => {
        const enabled = e.target.checked;
        logEcValue.disabled = !enabled;
        logPhValue.disabled = !enabled;
        logFertilizerNotes.disabled = !enabled;
    });

    // Watered checkbox toggle
    logWatered?.addEventListener('change', (e) => {
        const enabled = e.target.checked;
        logWaterAmount.disabled = !enabled;
    });

    // Close modal on overlay click
    dailyLogModal?.addEventListener('click', (e) => {
        if (e.target === dailyLogModal) {
            closeDailyLogModal();
        }
    });

    // Settings Modal
    btnEditGrowSettings?.addEventListener('click', openGrowSettingsModal);
    settingsModalClose?.addEventListener('click', closeGrowSettingsModal);
    btnCancelSettings?.addEventListener('click', closeGrowSettingsModal);
    btnSaveSettings?.addEventListener('click', saveGrowSettings);
    growSettingsModal?.addEventListener('click', (e) => {
        if (e.target === growSettingsModal) closeGrowSettingsModal();
    });

    // Category filters
    document.querySelectorAll('.cat-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.cat-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            selectedCategory = btn.dataset.cat || 'all';
            renderEventsList();
        });
    });

    // Add Event Modal
    btnAddEvent?.addEventListener('click', openAddEventModal);
    addEventModalClose?.addEventListener('click', closeAddEventModal);
    btnCancelAddEvent?.addEventListener('click', closeAddEventModal);
    btnSaveNewEvent?.addEventListener('click', saveNewEvent);
    addEventModal?.addEventListener('click', (e) => {
        if (e.target === addEventModal) closeAddEventModal();
    });
}

// ==========================================
// Grows Management
// ==========================================
async function loadGrows() {
    try {
        const data = await GrowPiAPI.getGrows(false); // Only active grows

        if (data.success && data.grows && data.grows.length > 0) {
            currentGrow = data.grows[0]; // Use first active grow
            updateGrowDisplay();
            await loadPhaseEvents(); // Load events for current phase
            await loadTodayTips(); // Load actionable cultivation tips
            renderCalendar();
        } else {
            // No active grow found
            currentGrowName.textContent = 'Kein aktiver Grow';
            currentPhaseInfo.textContent = 'Starte einen neuen Grow';
            calendarGrid.innerHTML = '<div class="calendar-empty">Bitte starte einen neuen Grow</div>';
            eventsList.innerHTML = '<div class="events-empty">Kein aktiver Grow</div>';
            growTipBanner?.classList.add('hidden');
        }
    } catch (error) {
        console.error('[Calendar] Failed to load grows:', error);
        showError('Fehler beim Laden der Grows');
    }
}

async function createNewGrow() {
    const name = prompt('Grow-Name:', 'Grow ' + new Date().getFullYear());
    if (!name) return;

    const strain = prompt('Sorte (optional):', '');
    const startDate = prompt('Startdatum (YYYY-MM-DD):', new Date().toISOString().split('T')[0]);

    try {
        const data = await GrowPiAPI.createGrow({
            name: name,
            strain: strain || null,
            start_date: startDate
        });

        if (data.success) {
            showSuccess('Grow erstellt!');
            await loadGrows();
        } else {
            showError(data.error || 'Fehler beim Erstellen');
        }
    } catch (error) {
        console.error('[Calendar] Create grow error:', error);
        showError('Verbindungsfehler');
    }
}

async function transitionPhase(phase) {
    if (!currentGrow) {
        showError('Kein aktiver Grow');
        return;
    }

    if (currentGrow.current_phase === phase) {
        showError('Phase ist bereits aktiv');
        return;
    }

    const confirmed = confirm(`Phase zu "${translatePhase(phase)}" wechseln?`);
    if (!confirmed) return;

    try {
        const data = await GrowPiAPI.transitionPhase(currentGrow.id, {
            new_phase: phase,
            notes: ''
        });

        if (data.success) {
            showSuccess('Phase gewechselt!');
            await loadGrows();
        } else {
            showError(data.error || 'Fehler beim Wechseln');
        }
    } catch (error) {
        console.error('[Calendar] Phase transition error:', error);
        showError('Verbindungsfehler');
    }
}

function updateGrowDisplay() {
    if (!currentGrow) return;

    const phaseInfo = PHASE_LABELS[currentGrow.current_phase] || PHASE_LABELS.seedling;

    currentGrowName.textContent = currentGrow.name;
    currentPhaseInfo.innerHTML = `
        <span style="color: ${phaseInfo.color}">${phaseInfo.icon} ${phaseInfo.de}</span>
        ${currentGrow.phase_day ? ` - Tag ${currentGrow.phase_day}` : ''}
    `;

    // Update phase button states
    [phaseButtonSeedling, phaseButtonVeggie, phaseButtonBloom].forEach(btn => {
        btn?.classList.remove('active');
    });

    if (currentGrow.current_phase === 'seedling') {
        phaseButtonSeedling?.classList.add('active');
    } else if (currentGrow.current_phase === 'vegetative') {
        phaseButtonVeggie?.classList.add('active');
    } else if (currentGrow.current_phase === 'flowering') {
        phaseButtonBloom?.classList.add('active');
    }

    // Update Status Dashboard & Tips
    updateStatusDashboard();
    loadTodayTips();
}

async function loadTodayTips() {
    if (!currentGrow || !growTipBanner) return;

    try {
        const data = await GrowPiAPI.getTodayTips();
        if (data.success && data.active_grow) {
            todayTipsData = data;
            growTipBanner.classList.remove('hidden');

            const activeTips = data.active_tips || [];
            if (activeTips.length > 0) {
                const primary = activeTips[0];
                if (growTipIcon) growTipIcon.textContent = primary.icon || '💡';
                const dayRange = primary.day_offset_max ? `Tag ${primary.day_offset_min}–${primary.day_offset_max}` : `Tag ${primary.day_offset_min}`;
                if (growTipTitle) growTipTitle.textContent = `${primary.title} (${dayRange})`;
                if (growTipDesc) growTipDesc.textContent = primary.description || '';
            } else {
                if (growTipIcon) growTipIcon.textContent = '💡';
                if (growTipTitle) growTipTitle.textContent = `Tipp für ${PHASE_LABELS[data.active_grow.current_phase]?.de || 'Phase'} (Tag ${data.active_grow.phase_day})`;
                if (growTipDesc) growTipDesc.textContent = data.primary_tip || 'Klima und Pflanzengesundheit regelmäßig prüfen.';
            }

            if (growTipEnv) {
                if (data.target_env) {
                    try {
                        const envObj = typeof data.target_env === 'string' ? JSON.parse(data.target_env) : data.target_env;
                        const tempText = envObj.temp ? `🌡️ ${envObj.temp.min}–${envObj.temp.max}°C` : '';
                        const rhText = envObj.rh ? `💧 ${envObj.rh.min}–${envObj.rh.max}% rLF` : '';
                        growTipEnv.innerHTML = `<span>${tempText}</span> <span>${rhText}</span>`;
                    } catch {
                        growTipEnv.innerHTML = '';
                    }
                } else {
                    growTipEnv.innerHTML = '';
                }
            }
        } else {
            growTipBanner.classList.add('hidden');
        }
    } catch (e) {
        console.warn('[Calendar] Failed to load today tips:', e);
        growTipBanner?.classList.add('hidden');
    }
}

function updateStatusDashboard() {
    if (!currentGrow) {
        // Hide dashboard when no grow
        document.getElementById('growStatusDashboard')?.classList.add('hidden');
        growTipBanner?.classList.add('hidden');
        return;
    }

    document.getElementById('growStatusDashboard')?.classList.remove('hidden');

    const phaseInfo = PHASE_LABELS[currentGrow.current_phase] || PHASE_LABELS.seedling;

    if (statusPhaseIcon) statusPhaseIcon.textContent = phaseInfo.icon;
    if (statusPhaseName) statusPhaseName.textContent = phaseInfo.de;
    if (statusPhaseDay) statusPhaseDay.textContent = currentGrow.phase_day || '-';
    if (statusGrowStart) statusGrowStart.textContent = formatDateDE(currentGrow.start_date);
    if (statusPhaseStart) {
        const phaseStartDate = currentGrow.phase_started_at ? currentGrow.phase_started_at.split('T')[0] : null;
        statusPhaseStart.textContent = formatDateDE(phaseStartDate);
    }
}

function formatDateDE(dateStr) {
    if (!dateStr) return '-';
    try {
        const date = new Date(dateStr);
        return date.toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' });
    } catch {
        return dateStr;
    }
}

// ==========================================
// Calendar Rendering
// ==========================================
async function renderCalendar() {
    if (!currentGrow) {
        calendarGrid.innerHTML = '<div class="calendar-empty">Kein aktiver Grow</div>';
        return;
    }

    // Update month/year label
    const monthNames = ['Januar', 'Februar', 'März', 'April', 'Mai', 'Juni', 'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'];
    monthYearLabel.textContent = `${monthNames[currentMonth.getMonth()]} ${currentMonth.getFullYear()}`;

    // Load logs for this month
    await loadMonthData();

    // Generate calendar grid
    const firstDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), 1);
    const lastDay = new Date(currentMonth.getFullYear(), currentMonth.getMonth() + 1, 0);
    const startDay = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1; // Monday = 0

    let html = '<div class="calendar-header">';
    ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].forEach(day => {
        html += `<div class="calendar-day-label">${day}</div>`;
    });
    html += '</div>';

    html += '<div class="calendar-body">';

    // Empty cells before first day
    for (let i = 0; i < startDay; i++) {
        html += '<div class="calendar-day empty"></div>';
    }

    // Days of month
    const today = new Date();
    const todayStr = formatDate(today);

    for (let day = 1; day <= lastDay.getDate(); day++) {
        const date = new Date(currentMonth.getFullYear(), currentMonth.getMonth(), day);
        const dateStr = formatDate(date);
        const log = monthLogs.find(l => l.date === dateStr);
        const dayEvents = monthEvents.filter(e => e.date === dateStr);

        const isToday = dateStr === todayStr;
        const phaseInfo = getPhaseForDate(dateStr);
        const phaseColor = phaseInfo ? PHASE_LABELS[phaseInfo.phase]?.color : '#333';

        let classes = 'calendar-day';
        if (isToday) classes += ' today';
        if (log) classes += ' has-log';

        html += `<div class="${classes}" data-date="${dateStr}" style="border-left: 3px solid ${phaseColor}">`;
        html += `<div class="day-number">${day}</div>`;
        html += '<div class="day-indicators">';

        if (log?.watered) html += '<span class="indicator watered" title="Bewässert">💧</span>';
        if (log?.fertilized) html += '<span class="indicator fertilized" title="Gedüngt">🧪</span>';
        if (log?.observations?.length > 0) {
            const hasProblems = log.observations.some(o => o !== 'healthy');
            if (hasProblems) {
                html += '<span class="indicator warning" title="Problem">⚠️</span>';
            } else {
                html += '<span class="indicator healthy" title="Alles gut">✅</span>';
            }
        }

        html += '</div>';

        // Event dots
        if (dayEvents.length > 0) {
            html += '<div class="day-events">';
            dayEvents.forEach(event => {
                const category = event.category || 'observation';
                html += `<span class="event-dot ${category}" title="${event.title}"></span>`;
            });
            html += '</div>';
        }

        html += '</div>';
    }

    html += '</div>';

    calendarGrid.innerHTML = html;

    // Add click handlers
    document.querySelectorAll('.calendar-day:not(.empty)').forEach(dayEl => {
        dayEl.addEventListener('click', () => {
            const dateStr = dayEl.dataset.date;
            openDailyLogModal(dateStr);
        });
    });
}

async function loadMonthData() {
    const monthStr = `${currentMonth.getFullYear()}-${String(currentMonth.getMonth() + 1).padStart(2, '0')}`;

    try {
        const data = await GrowPiAPI.getCalendarMonth(monthStr);

        if (data.success) {
            monthLogs = data.logs || [];
            monthEvents = data.events || [];
            if (data.grow) {
                currentGrow = data.grow;
                updateGrowDisplay();
            }
        }
    } catch (error) {
        console.error('[Calendar] Failed to load month data:', error);
    }
}

function getPhaseForDate(dateStr) {
    if (!currentGrow) return null;

    const growStart = new Date(currentGrow.start_date);
    const date = new Date(dateStr);

    if (date < growStart) return null;

    // Simple phase detection (could be enhanced with actual phase_started_at)
    return {
        phase: currentGrow.current_phase,
        day: Math.floor((date - growStart) / (1000 * 60 * 60 * 24)) + 1
    };
}

// ==========================================
// Daily Log Modal
// ==========================================
async function openDailyLogModal(dateStr) {
    selectedDate = dateStr;

    // Format date for display
    const date = new Date(dateStr);
    const dateOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    modalDate.textContent = date.toLocaleDateString('de-DE', dateOptions);

    // Show phase info
    const phaseInfo = getPhaseForDate(dateStr);
    if (phaseInfo) {
        const phaseLabel = PHASE_LABELS[phaseInfo.phase];
        modalPhaseInfo.innerHTML = `${phaseLabel.icon} ${phaseLabel.de} - Tag ${phaseInfo.day}`;
    } else {
        modalPhaseInfo.textContent = 'Vor Grow-Start';
    }

    // Load events for this date
    await loadEventsForDate(dateStr);

    // Load existing log if any
    const existingLog = monthLogs.find(l => l.date === dateStr);
    populateLogForm(existingLog);

    // Show modal
    dailyLogModal.style.display = 'flex';
}

async function loadEventsForDate(dateStr) {
    if (!currentGrow) {
        selectedDateEvents = [];
        updateModalEvents();
        return;
    }

    try {
        const data = await GrowPiAPI.getMilestonesForDate(currentGrow.id, dateStr);

        if (data.success && data.milestones) {
            selectedDateEvents = data.milestones;
            updateModalEvents();
        } else {
            selectedDateEvents = [];
            updateModalEvents();
        }
    } catch (error) {
        console.error('[Calendar] Failed to load events for date:', error);
        selectedDateEvents = [];
        updateModalEvents();
    }
}

function updateModalEvents() {
    const modalEventsContainer = document.getElementById('modalEvents');
    const eventsListContainer = document.getElementById('modalEventsList');

    if (!modalEventsContainer || !eventsListContainer) return;

    if (selectedDateEvents.length === 0) {
        modalEventsContainer.style.display = 'none';
        return;
    }

    modalEventsContainer.style.display = 'block';
    eventsListContainer.innerHTML = selectedDateEvents
        .map(event => `
            <div class="modal-event-item">
                <span class="modal-event-icon">${event.icon || '📌'}</span>
                <div>
                    <strong>${event.title}:</strong>
                    <span>${event.description || ''}</span>
                </div>
            </div>
        `)
        .join('');
}

function renderEventBadge(event) {
    const category = event.category || 'observation';
    const icon = getCategoryIcon(event.category);

    return `
        <div class="event-badge ${category}">
            <span class="event-icon">${icon}</span>
            <span class="event-title">${event.title}</span>
        </div>
    `;
}

function getCategoryIcon(category) {
    const icons = {
        training: '✂️',
        environment: '🌡️',
        nutrients: '🧪',
        observation: '👁️',
        harvest: '🌾'
    };
    return icons[category] || '📅';
}

function populateLogForm(log) {
    if (!log) {
        // Reset form
        logFertilized.checked = false;
        logEcValue.value = '';
        logEcValue.disabled = true;
        logPhValue.value = '';
        logPhValue.disabled = true;
        logFertilizerNotes.value = '';
        logFertilizerNotes.disabled = true;
        logWatered.checked = false;
        logWaterAmount.value = '';
        logWaterAmount.disabled = true;
        logNotes.value = '';
        logObservations.forEach(cb => cb.checked = false);
        return;
    }

    // Populate with existing data
    logFertilized.checked = log.fertilized || false;
    logEcValue.disabled = !log.fertilized;
    logPhValue.disabled = !log.fertilized;
    logFertilizerNotes.disabled = !log.fertilized;
    logEcValue.value = '';  // Not stored in database
    logPhValue.value = '';  // Not stored in database
    logFertilizerNotes.value = log.fertilizer_type || '';

    logWatered.checked = log.watered || false;
    logWaterAmount.disabled = !log.watered;
    logWaterAmount.value = log.water_amount_ml || '';

    logNotes.value = log.notes || '';

    // Observations (not stored in current schema)
    logObservations.forEach(cb => {
        cb.checked = false;
    });
}

function closeDailyLogModal() {
    dailyLogModal.style.display = 'none';
    selectedDate = null;
}

async function saveDailyLog() {
    if (!currentGrow || !selectedDate) return;

    // Collect observations
    const observations = Array.from(logObservations)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    const logData = {
        grow_id: currentGrow.id,
        log_date: selectedDate,
        watered: logWatered.checked,
        water_amount_ml: logWatered.checked ? parseInt(logWaterAmount.value) || null : null,
        fertilized: logFertilized.checked,
        fertilizer_type: logFertilized.checked ? logFertilizerNotes.value : null,
        fertilizer_amount_ml: null,
        notes: logNotes.value || null,
        plant_height_cm: null,
        photos: null
    };

    try {
        const data = await GrowPiAPI.saveDailyLog(logData);

        if (data.success) {
            showSuccess('Log gespeichert!');
            closeDailyLogModal();
            await renderCalendar(); // Reload calendar
        } else {
            showError(data.error || 'Fehler beim Speichern');
        }
    } catch (error) {
        console.error('[Calendar] Save log error:', error);
        showError('Verbindungsfehler');
    }
}

// ==========================================
// Utility Functions
// ==========================================
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

function translatePhase(phase) {
    return PHASE_LABELS[phase]?.de || phase;
}

// ==========================================
// Grow Settings Modal
// ==========================================

function openGrowSettingsModal() {
    if (!currentGrow) {
        showError('Kein aktiver Grow');
        return;
    }

    // Populate form with current values
    if (settingsGrowName) settingsGrowName.textContent = currentGrow.name;
    if (settingsGrowNameInput) settingsGrowNameInput.value = currentGrow.name || '';
    if (settingsStrainInput) settingsStrainInput.value = currentGrow.strain || '';

    // Convert dates to input format (YYYY-MM-DD)
    if (settingsGrowStartDate) {
        settingsGrowStartDate.value = currentGrow.start_date || '';
    }
    if (settingsPhaseStartDate) {
        const phaseDate = currentGrow.phase_started_at?.split('T')[0] || '';
        settingsPhaseStartDate.value = phaseDate;
    }

    // Show modal
    if (growSettingsModal) growSettingsModal.style.display = 'flex';
}

function closeGrowSettingsModal() {
    if (growSettingsModal) growSettingsModal.style.display = 'none';
}

async function saveGrowSettings() {
    if (!currentGrow) return;

    const updates = {};

    // Collect changed values
    const newName = settingsGrowNameInput?.value?.trim();
    const newStrain = settingsStrainInput?.value?.trim();
    const newGrowStart = settingsGrowStartDate?.value;
    const newPhaseStart = settingsPhaseStartDate?.value;

    if (newName && newName !== currentGrow.name) {
        updates.name = newName;
    }
    if (newStrain !== currentGrow.strain) {
        updates.strain = newStrain || null;
    }
    if (newGrowStart && newGrowStart !== currentGrow.start_date) {
        updates.start_date = newGrowStart;
    }
    if (newPhaseStart) {
        const currentPhaseDate = currentGrow.phase_started_at?.split('T')[0] || null;
        if (newPhaseStart !== currentPhaseDate) {
            // Validate date is not in the future
            const phaseDate = new Date(newPhaseStart);
            const today = new Date();
            today.setHours(0, 0, 0, 0);
            if (phaseDate > today) {
                showError('Phase-Startdatum darf nicht in der Zukunft liegen');
                return;
            }
            // Convert to ISO datetime format
            updates.phase_started_at = newPhaseStart + 'T00:00:00';
        }
    }

    // Check if anything changed
    if (Object.keys(updates).length === 0) {
        showError('Keine Änderungen');
        closeGrowSettingsModal();
        return;
    }

    try {
        const data = await GrowPiAPI.updateGrow(currentGrow.id, updates);

        if (data.success) {
            showSuccess('Einstellungen gespeichert!');
            closeGrowSettingsModal();
            await loadGrows(); // Reload to get updated data
        } else {
            showError(data.error || 'Fehler beim Speichern');
        }
    } catch (error) {
        console.error('[Calendar] Save settings error:', error);
        showError('Verbindungsfehler');
    }
}

// ==========================================
// Events Section (Phase Milestones)
// ==========================================

async function loadPhaseEvents() {
    if (!currentGrow) {
        eventsList.innerHTML = '<div class="events-empty">Kein aktiver Grow</div>';
        return;
    }

    const phase = currentGrow.current_phase;
    eventsPhaseLabel.textContent = PHASE_LABELS[phase]?.de || phase;

    try {
        const data = await GrowPiAPI.getMilestones(phase);

        if (data.success && data.milestones) {
            currentPhaseEvents = data.milestones;
            renderEventsList();
        } else {
            eventsList.innerHTML = '<div class="events-empty">Keine Ereignisse gefunden</div>';
        }
    } catch (error) {
        console.error('[Calendar] Failed to load events:', error);
        eventsList.innerHTML = '<div class="events-error">Fehler beim Laden</div>';
    }
}

function renderEventsList() {
    if (currentPhaseEvents.length === 0) {
        eventsList.innerHTML = '<div class="events-empty">Keine Ereignisse für diese Phase</div>';
        return;
    }

    const filtered = selectedCategory === 'all'
        ? currentPhaseEvents
        : currentPhaseEvents.filter(e => e.category === selectedCategory);

    if (filtered.length === 0) {
        eventsList.innerHTML = `<div class="events-empty">Keine Meilensteine in dieser Kategorie</div>`;
        return;
    }

    const catLabels = {
        training: '✂️ Training & Entlaubung',
        environment: '🌡️ Klima & Licht',
        nutrients: '🧪 Düngung & Spülen',
        observation: '🔬 Beobachtung',
        harvest: '🌾 Ernte'
    };

    const html = filtered.map(event => {
        const dayRange = event.day_offset_max
            ? `Tag ${event.day_offset_min}–${event.day_offset_max}`
            : `Tag ${event.day_offset_min}`;

        const isSystem = event.is_system;
        const isEnabled = event.is_enabled;
        const categoryClass = event.category || 'observation';
        const catLabel = catLabels[categoryClass] || categoryClass;

        // Parse climate targets if present
        let envHtml = '';
        if (event.env_params) {
            try {
                const env = typeof event.env_params === 'string' ? JSON.parse(event.env_params) : event.env_params;
                const tempStr = env.temp ? `${env.temp.min}–${env.temp.max}°C` : '';
                const rhStr = env.rh ? `${env.rh.min}–${env.rh.max}% rLF` : '';
                if (tempStr || rhStr) {
                    envHtml = `<span class="event-env-badge" title="Empfohlene Ziel-Klimawerte">🌡️ ${tempStr} | 💧 ${rhStr}</span>`;
                }
            } catch {}
        }

        return `
            <div class="event-item ${categoryClass} ${isEnabled ? '' : 'disabled'}" data-id="${event.id}">
                <div class="event-toggle">
                    <label class="toggle-switch">
                        <input type="checkbox" ${isEnabled ? 'checked' : ''}
                               onchange="window.toggleEvent('${event.id}', this.checked)">
                        <span class="toggle-slider"></span>
                    </label>
                </div>
                <div class="event-content">
                    <div class="event-header-row">
                        <span class="event-icon">${event.icon || '📅'}</span>
                        <span class="event-title">${event.title}</span>
                        <span class="event-day-badge">${dayRange}</span>
                        <span class="event-cat-badge ${categoryClass}">${catLabel}</span>
                        ${envHtml}
                    </div>
                    ${event.description ? `<div class="event-description">${event.description}</div>` : ''}
                </div>
                ${!isSystem ? `
                    <button class="event-delete-btn" onclick="window.deleteEvent('${event.id}')" title="Löschen">
                        🗑️
                    </button>
                ` : ''}
            </div>
        `;
    }).join('');

    eventsList.innerHTML = html;
}

// Global functions for event handlers (needed for onclick)
window.toggleEvent = async function(eventId, enabled) {
    try {
        const data = await GrowPiAPI.toggleMilestone(eventId, enabled);
        if (data.success) {
            showSuccess(enabled ? 'Event aktiviert' : 'Event deaktiviert');
            // Update local state
            const event = currentPhaseEvents.find(e => e.id === eventId);
            if (event) event.is_enabled = enabled;
            renderEventsList();
        } else {
            showError(data.error || 'Fehler');
            await loadPhaseEvents(); // Reload on error
        }
    } catch (error) {
        console.error('[Calendar] Toggle error:', error);
        showError('Verbindungsfehler');
    }
};

window.deleteEvent = async function(eventId) {
    if (!confirm('Event wirklich löschen?')) return;

    try {
        const data = await GrowPiAPI.deleteMilestone(eventId);
        if (data.success) {
            showSuccess('Event gelöscht');
            await loadPhaseEvents();
        } else {
            showError(data.error || 'Fehler beim Löschen');
        }
    } catch (error) {
        console.error('[Calendar] Delete error:', error);
        showError('Verbindungsfehler');
    }
};

// ==========================================
// Add Event Modal
// ==========================================

function openAddEventModal() {
    if (!currentGrow) {
        showError('Kein aktiver Grow');
        return;
    }
    // Reset form
    newEventTitle.value = '';
    newEventDescription.value = '';
    newEventDayMin.value = currentGrow.phase_day || 1;
    newEventDayMax.value = '';
    newEventIcon.value = '';
    addEventModal.style.display = 'flex';
}

function closeAddEventModal() {
    addEventModal.style.display = 'none';
}

async function saveNewEvent() {
    const title = newEventTitle?.value?.trim();
    const dayMin = parseInt(newEventDayMin?.value);

    if (!title) {
        showError('Titel ist erforderlich');
        return;
    }
    if (!dayMin || dayMin < 1) {
        showError('Ab-Tag muss mindestens 1 sein');
        return;
    }

    const eventData = {
        phase: currentGrow.current_phase,
        day_offset_min: dayMin,
        day_offset_max: newEventDayMax?.value ? parseInt(newEventDayMax.value) : null,
        title: title,
        description: newEventDescription?.value?.trim() || null,
        icon: newEventIcon?.value?.trim() || '📌',
        category: 'observation'
    };

    try {
        const data = await GrowPiAPI.createMilestone(eventData);
        if (data.success) {
            showSuccess('Event erstellt!');
            closeAddEventModal();
            await loadPhaseEvents();
        } else {
            showError(data.error || 'Fehler beim Erstellen');
        }
    } catch (error) {
        console.error('[Calendar] Create event error:', error);
        showError('Verbindungsfehler');
    }
}
