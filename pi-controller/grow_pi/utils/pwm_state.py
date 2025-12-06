"""
GrowPi PWM State Persistence

Zero-Downtime Restarts: Speichert PWM-Zustand in /run/growpi/
für nahtlose Service-Neustarts ohne LED-Flackern.

Nutzt die pigpiod-Persistenz: PWM-Werte bleiben stabil,
solange pigpiod läuft - unabhängig vom Python-Prozess.

Author: Dennis Westermann
Created: 2025-12-06
"""

import json
import os
import fcntl
from datetime import datetime
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)

# State-Verzeichnis (tmpfs, wird bei Reboot gelöscht)
STATE_DIR = '/run/growpi'
STATE_FILE = f'{STATE_DIR}/pwm_state.json'
LOCK_FILE = f'{STATE_DIR}/pwm.lock'

# Fallback für Entwicklung (nicht-Pi Systeme)
FALLBACK_STATE_DIR = '/tmp/growpi'
FALLBACK_STATE_FILE = f'{FALLBACK_STATE_DIR}/pwm_state.json'
FALLBACK_LOCK_FILE = f'{FALLBACK_STATE_DIR}/pwm.lock'


def _get_state_paths() -> tuple:
    """
    Ermittelt die korrekten Pfade für State-Files.

    Verwendet /run/growpi/ auf Pi (systemd RuntimeDirectory),
    /tmp/growpi/ als Fallback für Entwicklung.

    Returns:
        Tuple (state_dir, state_file, lock_file)
    """
    # Prüfe ob /run/growpi existiert (systemd RuntimeDirectory)
    if os.path.isdir(STATE_DIR):
        return STATE_DIR, STATE_FILE, LOCK_FILE

    # Fallback für Entwicklung
    return FALLBACK_STATE_DIR, FALLBACK_STATE_FILE, FALLBACK_LOCK_FILE


def ensure_state_dir() -> str:
    """
    Erstellt State-Verzeichnis falls nicht vorhanden.

    Returns:
        Pfad zum State-Verzeichnis
    """
    state_dir, _, _ = _get_state_paths()

    try:
        os.makedirs(state_dir, exist_ok=True)
        logger.debug(f"State directory ensured: {state_dir}")
        return state_dir
    except PermissionError:
        # Fallback wenn /run/growpi nicht beschreibbar
        os.makedirs(FALLBACK_STATE_DIR, exist_ok=True)
        logger.warning(f"Using fallback state dir: {FALLBACK_STATE_DIR}")
        return FALLBACK_STATE_DIR


def save_state(pwm_controller, mode: str = 'auto') -> bool:
    """
    Speichert aktuellen PWM-Zustand für Zero-Downtime Restart.

    Args:
        pwm_controller: PWMController Instanz
        mode: Aktueller Modus ('auto' oder 'manual')

    Returns:
        True wenn erfolgreich gespeichert
    """
    ensure_state_dir()
    _, state_file, lock_file = _get_state_paths()

    # State-Objekt aufbauen
    state: Dict[str, Any] = {
        'version': 1,
        'timestamp': datetime.now().isoformat(),
        'mode': mode,
        'channels': {}
    }

    # Channel-Daten aus PWMController extrahieren
    for channel_num, channel_info in pwm_controller.channels.items():
        state['channels'][str(channel_num)] = {
            'gpio': channel_info.gpio_pin,
            'name': channel_info.name,
            'intensity': channel_info.current_intensity,
            'source': 'curve' if mode == 'auto' else 'manual',
            'updated_at': datetime.now().isoformat()
        }

    # Atomisches Schreiben mit File-Lock
    try:
        # Lock-File erstellen/öffnen
        with open(lock_file, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)

            # State schreiben
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2)

            fcntl.flock(lock, fcntl.LOCK_UN)

        logger.info(f"PWM state saved to {state_file}")
        logger.debug(f"State: {state}")
        return True

    except Exception as e:
        logger.error(f"Failed to save PWM state: {e}")
        return False


def load_state() -> Optional[Dict[str, Any]]:
    """
    Lädt gespeicherten PWM-Zustand.

    Returns:
        State-Dictionary oder None wenn nicht vorhanden/fehlerhaft
    """
    _, state_file, lock_file = _get_state_paths()

    if not os.path.exists(state_file):
        logger.debug(f"No state file found at {state_file}")
        return None

    try:
        # Lock für Lesen
        with open(lock_file, 'w') as lock:
            fcntl.flock(lock, fcntl.LOCK_SH)

            with open(state_file, 'r') as f:
                state = json.load(f)

            fcntl.flock(lock, fcntl.LOCK_UN)

        # Version prüfen
        if state.get('version') != 1:
            logger.warning(f"Unknown state version: {state.get('version')}")
            return None

        logger.info(f"PWM state loaded from {state_file}")
        logger.debug(f"Loaded state: {state}")
        return state

    except json.JSONDecodeError as e:
        logger.error(f"Corrupted state file: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load PWM state: {e}")
        return None


def state_exists() -> bool:
    """
    Prüft ob ein gültiger State-File existiert.

    Returns:
        True wenn State-File existiert und lesbar ist
    """
    _, state_file, _ = _get_state_paths()

    if not os.path.exists(state_file):
        return False

    # Prüfe ob Datei lesbar und nicht leer
    try:
        with open(state_file, 'r') as f:
            content = f.read()
            if not content.strip():
                return False
            # Prüfe ob valides JSON
            json.loads(content)
            return True
    except (json.JSONDecodeError, IOError):
        return False


def clear_state() -> bool:
    """
    Löscht State-Files (für intentionalen Full-Shutdown).

    Returns:
        True wenn erfolgreich gelöscht
    """
    _, state_file, lock_file = _get_state_paths()

    try:
        if os.path.exists(state_file):
            os.remove(state_file)
            logger.info(f"State file removed: {state_file}")

        return True

    except Exception as e:
        logger.error(f"Failed to clear state: {e}")
        return False


def get_state_age_seconds() -> Optional[float]:
    """
    Ermittelt das Alter des State-Files in Sekunden.

    Nützlich für Watchdog-Logik: Wenn State zu alt,
    könnte der Hauptservice abgestürzt sein.

    Returns:
        Alter in Sekunden oder None wenn kein State existiert
    """
    state = load_state()
    if not state:
        return None

    try:
        timestamp = datetime.fromisoformat(state['timestamp'])
        age = (datetime.now() - timestamp).total_seconds()
        return age
    except (KeyError, ValueError):
        return None
