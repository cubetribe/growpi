# v6.24.1 Validation Report – PWM Pin Realignment

## Test Matrix (Local Mac)
| Suite | Command | Result |
|-------|---------|--------|
| Unit tests | `venv/bin/python -m pytest tests/unit` | ✅ 140 passed (Python 3.13.5) |

## Observations
- The swapped GPIO assignments do not affect higher-level logic; all scheduling, mode handling, dehumidifier, and cost-calculation tests continue to pass.
- `venv/bin/pytest` still has an outdated shebang but invoking `venv/bin/python -m pytest` works reliably; noted for future DX improvements.

## Pending Manual Checks
- Hardware validation on the Raspberry Pi (GPIO-18 output scope/LED) is still required to fully close the incident. The Pi-side restart + observation must be done after deployment.
