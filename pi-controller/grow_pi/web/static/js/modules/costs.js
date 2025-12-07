/**
 * Costs Module - Energy Consumption & Cost Tracking
 * Handles electricity cost calculation, device-level breakdowns,
 * and kWh price configuration
 *
 * Part of GrowPi v6.3 - Extracted from monolithic index.html (2894 LOC)
 * @module costs
 */

import { GrowPiAPI } from '../api.js';

// ==========================================
// DOM Elements
// ==========================================
const costDevicesList = document.getElementById("costDevicesList");
const totalKwh = document.getElementById("totalKwh");
const totalCost = document.getElementById("totalCost");
const kwhPriceInput = document.getElementById("kwhPriceInput");
const btnSaveKwhPrice = document.getElementById("btnSaveKwhPrice");
const costPeriodLabel = document.getElementById("costPeriodLabel");
const costDateFrom = document.getElementById("costDateFrom");
const costDateTo = document.getElementById("costDateTo");
const btnApplyDateRange = document.getElementById("btnApplyDateRange");

// ==========================================
// State
// ==========================================
let currentCostPeriod = 'today';
let customDateFrom = null;
let customDateTo = null;

// ==========================================
// Public API
// ==========================================
export function initCostsTab() {
    console.log('[Costs] Initializing costs tab...');

    // Initialize date inputs with sensible defaults
    initializeDateInputs();

    // Setup event listeners
    setupEventListeners();

    // Initial fetch
    fetchCostsData();
}

// ==========================================
// Initialization
// ==========================================
function initializeDateInputs() {
    if (costDateTo) {
        costDateTo.value = new Date().toISOString().split('T')[0];
    }
    if (costDateFrom) {
        // Default to 30 days ago
        const thirtyDaysAgo = new Date();
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        costDateFrom.value = thirtyDaysAgo.toISOString().split('T')[0];
    }
}

// ==========================================
// Data Fetching
// ==========================================
export async function fetchCostsData() {
    try {
        // Use GrowPiAPI instead of direct fetch()
        const data = await GrowPiAPI.getCosts(
            currentCostPeriod,
            customDateFrom,
            customDateTo
        );

        if (data.success) {
            renderCostDevices(data.devices);
            totalKwh.textContent = data.total_kwh.toFixed(3);
            totalCost.textContent = data.total_cost.toFixed(2);

            // Show period label
            if (costPeriodLabel && data.period_label) {
                costPeriodLabel.textContent = `Zeitraum: ${data.period_label}`;
            }

            // Load current kWh price
            if (kwhPriceInput && data.kwh_price !== undefined) {
                kwhPriceInput.value = data.kwh_price;
            }
        } else {
            window.showError?.(data.error || "Fehler beim Laden der Kosten");
        }
    } catch (e) {
        console.error("[Costs] Fetch error:", e);
        window.showError?.("Verbindungsfehler");
    }
}

// ==========================================
// Rendering
// ==========================================
function renderCostDevices(devices) {
    if (!costDevicesList) return;

    costDevicesList.innerHTML = devices.map(device => `
        <div class="cost-device-card">
            <div class="cost-device-info">
                <span class="cost-device-name">${device.name}</span>
                <span class="cost-device-kwh">${device.kwh.toFixed(3)} kWh</span>
            </div>
            <div class="cost-device-cost">${device.cost.toFixed(2)} €</div>
        </div>
    `).join('');
}

// ==========================================
// Configuration Management
// ==========================================
async function saveKwhPrice() {
    const price = parseFloat(kwhPriceInput.value);
    if (isNaN(price) || price <= 0) {
        window.showError?.("Ungültiger kWh-Preis");
        return;
    }

    try {
        // Use GrowPiAPI instead of direct fetch()
        const data = await GrowPiAPI.saveCostsConfig(price);

        if (data.success) {
            window.showSuccess?.("kWh-Preis gespeichert!");
            fetchCostsData(); // Refresh to show updated costs
        } else {
            window.showError?.(data.error || "Fehler beim Speichern");
        }
    } catch (e) {
        window.showError?.("Verbindungsfehler");
    }
}

// ==========================================
// Event Handlers
// ==========================================
function handlePeriodChange(period) {
    // Clear custom date range when using preset buttons
    customDateFrom = null;
    customDateTo = null;

    document.querySelectorAll(".cost-period-btn").forEach(b => b.classList.remove("active"));
    currentCostPeriod = period;
    fetchCostsData();
}

function handleCustomDateRange() {
    const fromDate = costDateFrom.value;
    const toDate = costDateTo.value;

    if (!fromDate || !toDate) {
        window.showError?.("Bitte Von- und Bis-Datum auswählen");
        return;
    }

    if (new Date(fromDate) > new Date(toDate)) {
        window.showError?.("Von-Datum muss vor Bis-Datum liegen");
        return;
    }

    // Set custom date range
    customDateFrom = fromDate;
    customDateTo = toDate;

    // Remove active class from preset buttons
    document.querySelectorAll(".cost-period-btn").forEach(b => b.classList.remove("active"));

    fetchCostsData();
}

// ==========================================
// Event Listeners Setup
// ==========================================
function setupEventListeners() {
    // Period button event listeners
    document.querySelectorAll(".cost-period-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            handlePeriodChange(btn.dataset.period);
            btn.classList.add("active");
        });
    });

    // Custom date range button
    if (btnApplyDateRange) {
        btnApplyDateRange.addEventListener("click", handleCustomDateRange);
    }

    // Save kWh price button
    if (btnSaveKwhPrice) {
        btnSaveKwhPrice.addEventListener("click", saveKwhPrice);
    }
}
