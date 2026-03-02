# GitHub Actions -> Raspberry Pi Auto-Deploy

## Ziel
Automatisches Deployment auf den Raspberry Pi nach `git push` mit direktem Feedback im GitHub Actions Run.

## Kernprinzip
Wir verwenden **einen Self-Hosted Runner direkt auf dem Pi**.

- GitHub Actions Jobs laufen auf dem Pi selbst
- Deployment und Health-Checks passieren lokal auf dem Gerät
- Das Ergebnis (PASS/FAIL + Logs) ist sofort im Actions-Run sichtbar

## Ports / Netzwerk
**Es müssen keine eingehenden Ports am Heimnetz geöffnet werden.**

Der Runner baut nur **ausgehende HTTPS-Verbindungen** zu GitHub auf (Polling/Job-Abholung).

## Komponenten
- Workflow: `.github/workflows/pi-autodeploy.yml`
- Deploy-Skript: `scripts/pi/github_runner_deploy.sh`
- Runner-Setup-Skript: `scripts/pi/install_github_runner.sh`

## Deployment-Ablauf pro Push
1. Workflow startet auf Runner-Label `growpi`.
2. `pi-controller/` wird nach `/opt/grow-pi` synchronisiert.
3. `grow-pi` und `growpi-web` werden via systemd neu gestartet.
4. Verifikation:
   - Services sind `active`
   - `/api/version` antwortet
   - API-Version entspricht `/opt/grow-pi/VERSION`
   - `/api/health` ist nicht `critical`

## Setup auf dem Pi
Voraussetzungen:
- `gh` CLI auf dem Pi oder lokal verfügbar (authentifiziert für `cubetribe/growpi`)
- `sudo` ohne Passwort für den Runner-User

Beispiel:

```bash
cd /path/to/GrowPi
./scripts/pi/install_github_runner.sh
```

Optional:

```bash
REPO_SLUG=cubetribe/growpi RUNNER_NAME=growpi-01 RUNNER_LABELS=growpi,prod ./scripts/pi/install_github_runner.sh
```

## Sicherheitsempfehlungen
- Runner nur für dieses Repo verwenden
- Eigener Linux-User für Runner (optional)
- `sudoers` auf nötige Kommandos einschränken:
  - `systemctl restart/status grow-pi growpi-web`
  - `rsync` nach `/opt/grow-pi`
- Regelmäßige Updates von Runner und Pi-Paketen

## Manuelle Auslösung
Workflow kann jederzeit über `workflow_dispatch` in GitHub manuell gestartet werden.

## Troubleshooting
- Runner-Status auf Pi:

```bash
systemctl list-units | grep actions.runner
sudo journalctl -u actions.runner.cubetribe-growpi.growpi-01 -f
```

- Deploy-Skript lokal auf Pi testen:

```bash
cd /opt/actions-runner/_work/growpi/growpi
./scripts/pi/github_runner_deploy.sh
```
