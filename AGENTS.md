# GrowPi Local Project Governance

## Scope

This repository contains the Raspberry Pi controller backend, embedded web UI,
deployment scripts, and operational documentation for GrowPi.

## Working Rules

- Keep changes small, buildable, and scoped to the requested subsystem.
- Do not commit secrets, `.env` files, runtime databases, logs, local runner
  workspaces, or generated Python caches.
- Prefer existing project patterns and scripts over introducing new tooling.
- For operational incidents, persist durable findings in `reports/generated/`
  and keep transient workflow coordination in `state/`.
- Treat Raspberry Pi hardware faults separately from software regressions:
  software changes must not mask undervoltage, throttling, or failed sensor
  hardware.

## Validation

- Run focused unit tests for touched Python modules.
- Run shell syntax checks for changed shell scripts.
- For Pi operations changes, run `pi-controller/smoke_test.sh` against the
  target API when it is reachable.
- Record known hardware-dependent failures explicitly instead of marking the
  software validation as clean.

## Git And Release

- Use patch release impact for hardening, diagnostics, docs, and backwards
  compatible health endpoint fixes.
- Do not bump `VERSION` or edit release changelog entries unless the task is a
  release preparation.
- Never commit or push secrets. Never force-push shared branches.
