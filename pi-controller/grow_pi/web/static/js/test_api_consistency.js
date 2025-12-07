/**
 * API Consistency Test Script
 *
 * Verifies that GrowPiAPI has all required methods
 * Run this in browser console to validate API completeness
 *
 * Usage:
 *   1. Open GrowPi web interface
 *   2. Open browser DevTools (F12)
 *   3. Copy-paste this script into console
 *   4. Check output for ✅ (pass) or ❌ (fail)
 */

import { GrowPiAPI } from './api.js';

console.log('🔍 API Consistency Check - Testing GrowPiAPI completeness...\n');

// List of all required methods (19 total)
const requiredMethods = [
    // Status & Sensors (3)
    'getStatus',
    'getTemperature',
    'getHumidity',

    // Mode Control (2)
    'getMode',
    'setMode',

    // Lamp Control (5)
    'setLamp',
    'getCurves',
    'updateCurve',
    'getCurvePreview',
    'getCurveIntensities',

    // Logging & History (4)
    'getSensorLogs',
    'getLampLogs',
    'getPlugLogs',
    'getEventLogs',

    // Room Environment (3)
    'getRoomStatus',
    'controlDehumidifier',
    'saveRoomConfig',

    // Costs Management (3) - ADDED by Agent #10
    'getCosts',
    'getCostsConfig',
    'saveCostsConfig'
];

// Category definitions for better reporting
const categories = {
    'Status & Sensors': ['getStatus', 'getTemperature', 'getHumidity'],
    'Mode Control': ['getMode', 'setMode'],
    'Lamp Control': ['setLamp', 'getCurves', 'updateCurve', 'getCurvePreview', 'getCurveIntensities'],
    'Logging & History': ['getSensorLogs', 'getLampLogs', 'getPlugLogs', 'getEventLogs'],
    'Room Environment': ['getRoomStatus', 'controlDehumidifier', 'saveRoomConfig'],
    'Costs Management': ['getCosts', 'getCostsConfig', 'saveCostsConfig']
};

// Run tests
let passed = 0;
let failed = 0;
const missingMethods = [];

console.log('──────────────────────────────────────────────────────');

for (const [category, methods] of Object.entries(categories)) {
    console.log(`\n📦 ${category}`);

    for (const method of methods) {
        if (typeof GrowPiAPI[method] === 'function') {
            console.log(`   ✅ GrowPiAPI.${method}()`);
            passed++;
        } else {
            console.error(`   ❌ MISSING: GrowPiAPI.${method}()`);
            failed++;
            missingMethods.push(method);
        }
    }
}

console.log('\n──────────────────────────────────────────────────────');
console.log(`\n📊 Test Results:`);
console.log(`   ✅ Passed: ${passed}/${requiredMethods.length}`);
console.log(`   ❌ Failed: ${failed}/${requiredMethods.length}`);

if (failed === 0) {
    console.log('\n🎉 SUCCESS! All API methods are present.');
    console.log('   GrowPi API is fully consistent.');
} else {
    console.error('\n🚨 FAILURE! Missing methods detected:');
    missingMethods.forEach(method => {
        console.error(`   - ${method}`);
    });
    console.error('\n   Please add missing methods to api.js');
}

console.log('\n──────────────────────────────────────────────────────\n');

// Additional check: Verify no direct fetch() in modules
console.log('🔎 Checking for direct fetch() calls in modules...');
console.log('   (This check requires server-side verification)');
console.log('   Run: grep -rn "fetch(" modules/ | grep -v GrowPiAPI');
console.log('   Expected: 0 results (only comments allowed)\n');

// Export result for programmatic use
export const testResults = {
    passed,
    failed,
    total: requiredMethods.length,
    missingMethods,
    success: failed === 0
};
