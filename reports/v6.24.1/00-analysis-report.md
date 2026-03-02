# v6.24.1 Analysis Report – Cool White PWM Failure

## Summary
- User reports the Cool White LED channel is unresponsive even though the MOSFET reacts when the wire on the Raspberry Pi header is unplugged.
- Current software configuration still routes the Cool White channel (channel 3) to **GPIO 12 / physical pin 32** while UV uses **GPIO 18 / pin 12**.
- The hardware logbook and README mirror this mapping, so the firmware currently drives pin 32 for Cool White even though the user confirmed the affected wire sits on pin 12 (GPIO 18).
- Result: PWM updates go to the wrong header pin, so the Cool White MOSFET never receives duty-cycle changes.

## Evidence Collected
1. `pi-controller/config/config.yaml` defines channel 3 as `gpio_pin: 12` (GPIO numbering, i.e. physical pin 32) and channel 4 as `gpio_pin: 18` (physical pin 12). (lines 20-43)
2. `docs/HARDWARE_PINOUT.md` + `README.md` reproduce the same mapping, confirming the software currently expects Cool White on pin 32 and UV on pin 12.
3. The PWM controller simply trusts this list (`grow_pi/lamps/pwm_controller.py::initialize`), so all API/manual updates for channel 3 are routed to GPIO 12.
4. User validation (“Pin 12 … changes when unplugged”) shows the installation actually wired Cool White to physical pin 12 (GPIO 18) – therefore firmware and wiring disagree.

## Root Cause
The production wiring hooks the Cool White MOSFET to **GPIO 18 / pin 12**, but the codebase (config + docs) still assumes **GPIO 12 / pin 32**. Consequently, channel 3 drives the wrong pin and appears “dead”. UV is currently unused (default 0%), so no one noticed that the firmware is driving pin 32 for that channel.

## Next Steps
- Update the canonical pin map so Cool White (ch3) uses GPIO 18 / pin 12.
- Move the UV placeholder channel to the freed GPIO 12 / pin 32 (or mark it as dormant) and document the change everywhere (config, README, hardware spec, CLAUDE, etc.).
- Bump VERSION/CHANGELOG to 6.24.1 and add verification instructions so deployments can confirm the new mapping quickly.
