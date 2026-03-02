# v6.24.1 Builder Report – PWM Pin Realignment

## Scope
- Align all software pin definitions with the physical wiring confirmed on 2026-02-03.
- Ensure documentation, fallback configs, and operator guides expose the corrected mapping so the Cool White (channel 3) MOSFET receives PWM again.

## Changes Implemented
1. **Configuration Source of Truth**
   - `pi-controller/config/config.yaml`: channel 3 now targets GPIO-18 / Pin 12; channel 4 (UV) uses GPIO-12 / Pin 32. Updated header comments to mark the 2026-02-03 wiring baseline.
   - `pi-controller/VERSION`: bumped to 6.24.1 to signal the hardware fix rollout.
2. **Runtime Fallbacks & Docs**
   - `grow_pi/lamps/pwm_controller.py`, `grow_pi/web/api.py`, `grow_pi/web/services/lamp_config.py`, and `grow_pi/web/README_REFACTORING.md` now reference the corrected pins so every import path (CLI, Flask, fallback configs) is consistent.
3. **User-Facing Documentation**
   - Updated `README.md`, `pi-controller/README.md`, `CLAUDE.md`, `docs/HARDWARE_PINOUT.md`, and `docs/SPEC_RASPBERRY_PI.md` with the new mapping, diagrams, and timelines.
   - Added release notes to `CHANGELOG.md` and `pi-controller/CHANGELOG.md` describing the fix + report location.
4. **Reporting Artifacts**
   - Created `reports/v6.24.1/00-analysis-report.md` (root cause) and this builder report to document the work.

## Deployment Notes
- After deploying, restart `grow-pi.service` so the controller reloads `config.yaml` and reinitializes pigpiod with the swapped pins.
- Confirm via the web UI or `journalctl -u grow-pi -f` that channel 3 PWM writes now show on GPIO-18 and that UV (channel 4) remains idle unless explicitly used.
