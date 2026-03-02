# GrowPi - Raspberry Pi Greenhouse Controller

GrowPi is a Raspberry Pi based greenhouse automation system with lighting control, sensor monitoring, and a local web UI.

**Version**: v6.25.3 (2026-03-02)
**Status**: Production-hardened on Raspberry Pi
**Scope of this repository**: Pi controller backend + embedded web UI

> The separate Next.js frontend repository is available at [cubetribe/growpi_web_public](https://github.com/cubetribe/growpi_web_public).

---

## Highlights

- 4-channel PWM light control (Far Red, Warm White, Cool White, UV)
- Time-curve automation with interpolation
- DHT22 environment monitoring
- SQLite logging (sensor, lamp, events, power)
- Dehumidifier and smart plug integration
- Camera/timelapse support
- Process-split runtime (`grow-pi` controller + `growpi-web` API/UI)
- systemd watchdog and restart hardening
- Health endpoints for runtime monitoring (`/api/health/*`)

---

## Architecture

```text
Pi Runtime
├── grow-pi.service      (controller loop, hardware I/O)
├── growpi-web.service   (Flask API + embedded web UI on port 5000)
└── SQLite               (local telemetry + config persistence)

GitHub
└── Actions self-hosted runner on Pi
    └── auto-deploy workflow with live PASS/FAIL feedback
```

---

## Quick Start (Local Development)

```bash
git clone https://github.com/cubetribe/growpi.git
cd growpi/pi-controller
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v
python -m grow_pi.web.api
```

Open UI/API:

```text
http://localhost:5000
```

---

## Raspberry Pi Deployment

Use the installer in `pi-controller/`:

```bash
cd pi-controller
chmod +x install.sh
./install.sh
```

After installation:

```bash
sudo systemctl status grow-pi
sudo systemctl status growpi-web
curl -fsS http://127.0.0.1:5000/api/health/
```

Detailed deployment and operations guide:
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)

---

## CI/CD to Raspberry Pi

This repository includes GitHub Actions auto-deploy for a self-hosted Pi runner.

- Workflow: `.github/workflows/pi-autodeploy.yml`
- Deploy script: `scripts/pi/github_runner_deploy.sh`
- Runner setup: `scripts/pi/install_github_runner.sh`
- Documentation: `docs/GITHUB_ACTIONS_PI_AUTODEPLOY.md`

No inbound router ports are required. The Pi runner connects outbound to GitHub.

---

## Security and Configuration

- Do not commit `.env` files or real credentials.
- Use placeholders/examples (`.env.example`, `config.example.yaml`) only.
- Tuya cloud credentials must be supplied via environment variables (`TUYA_ACCESS_ID`, `TUYA_ACCESS_SECRET`).

---

## License

This project is licensed under **GrowPi Non-Commercial License v1.0**.

- Private / personal / non-commercial usage: free
- Commercial or professional usage: requires prior permission from Dennis Westermann

See [LICENSE](LICENSE) for the full legal text.

Important: because commercial use is restricted, this is a **source-available** license model, not an OSI open-source license.

---

## Changelog

- [CHANGELOG.md](CHANGELOG.md) (root project)
- [pi-controller/CHANGELOG.md](pi-controller/CHANGELOG.md) (Pi controller)

---

## Contact

Rights holder: **Dennis Westermann**

Commercial licensing requests: please open an issue in this repository.
