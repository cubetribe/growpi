#!/usr/bin/env bash
set -euo pipefail

# Install a self-hosted GitHub Actions runner on Raspberry Pi.
# Requires:
# 1) gh CLI authenticated for the target repository
# 2) passwordless sudo for the current user
# 3) network access to github.com

REPO_SLUG="${REPO_SLUG:-cubetribe/growpi}"
RUNNER_NAME="${RUNNER_NAME:-growpi-01}"
RUNNER_LABELS="${RUNNER_LABELS:-growpi,prod}"
RUNNER_DIR="${RUNNER_DIR:-$HOME/actions-runner}"

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found" >&2
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "curl not found" >&2
  exit 1
fi

TOKEN="$(gh api -X POST "repos/${REPO_SLUG}/actions/runners/registration-token" --jq '.token')"
RUNNER_URL="$(gh api repos/actions/runner/releases/latest --jq '.assets[] | select(.name | test("linux-arm64")) | .browser_download_url')"

mkdir -p "${RUNNER_DIR}"
cd "${RUNNER_DIR}"

if [[ ! -f .runner ]]; then
  rm -rf ./*
  curl -fsSL -o actions-runner.tar.gz "${RUNNER_URL}"
  tar xzf actions-runner.tar.gz
  ./config.sh \
    --url "https://github.com/${REPO_SLUG}" \
    --token "${TOKEN}" \
    --unattended \
    --name "${RUNNER_NAME}" \
    --labels "${RUNNER_LABELS}" \
    --work _work \
    --replace

  sudo ./svc.sh install "$(whoami)"
fi

sudo ./svc.sh start
SERVICE_NAME="actions.runner.${REPO_SLUG//\//-}.${RUNNER_NAME}.service"
systemctl status "${SERVICE_NAME}" --no-pager -n 20
