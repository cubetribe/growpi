"""
GrowPi Configuration Loader

Loads and validates configuration from YAML file.
"""

import os
import yaml
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class LampChannelConfig:
    """Configuration for a single lamp channel"""
    channel: int
    name: str
    gpio_pin: int
    pwm_frequency: int = 1000
    software_pwm: bool = False
    default_intensity: int = 0  # MVP: Fixed intensity on startup


@dataclass
class LampsConfig:
    """Lamp system configuration"""
    update_interval: int = 1
    channels: List[LampChannelConfig] = field(default_factory=list)


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: str = "INFO"
    file: Optional[str] = None


@dataclass
class GrowPiConfig:
    """Main configuration container"""
    lamps: LampsConfig
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Future expansion fields (not used in MVP)
    server: Optional[Dict] = None
    sensors: Optional[Dict] = None
    offline: Optional[Dict] = None
    system: Optional[Dict] = None


def find_config_file() -> Path:
    """
    Find configuration file in order of priority:
    1. Environment variable GROWPI_CONFIG
    2. ./config/config.yaml (relative to script)
    3. /opt/grow-pi/config/config.yaml (production)
    """
    # Check environment variable
    env_path = os.environ.get("GROWPI_CONFIG")
    if env_path and Path(env_path).exists():
        return Path(env_path)

    # Check relative path (development)
    script_dir = Path(__file__).parent.parent
    local_config = script_dir / "config" / "config.yaml"
    if local_config.exists():
        return local_config

    # Check production path
    prod_config = Path("/opt/grow-pi/config/config.yaml")
    if prod_config.exists():
        return prod_config

    raise FileNotFoundError(
        "Configuration file not found. Checked:\n"
        f"  - GROWPI_CONFIG env var\n"
        f"  - {local_config}\n"
        f"  - {prod_config}"
    )


def load_config(config_path: Optional[str] = None) -> GrowPiConfig:
    """
    Load configuration from YAML file.

    Args:
        config_path: Optional path to config file. If None, auto-detect.

    Returns:
        GrowPiConfig object
    """
    if config_path:
        path = Path(config_path)
    else:
        path = find_config_file()

    logger.info(f"Loading configuration from: {path}")

    with open(path, "r") as f:
        raw_config = yaml.safe_load(f)

    # Parse lamp channels
    lamp_channels = []
    if "lamps" in raw_config and "channels" in raw_config["lamps"]:
        for ch in raw_config["lamps"]["channels"]:
            lamp_channels.append(LampChannelConfig(
                channel=ch["channel"],
                name=ch["name"],
                gpio_pin=ch["gpio_pin"],
                pwm_frequency=ch.get("pwm_frequency", 1000),
                software_pwm=ch.get("software_pwm", False),
                default_intensity=ch.get("default_intensity", 0)
            ))

    lamps_config = LampsConfig(
        update_interval=raw_config.get("lamps", {}).get("update_interval", 1),
        channels=lamp_channels
    )

    # Parse logging config
    log_raw = raw_config.get("logging", {})
    logging_config = LoggingConfig(
        level=log_raw.get("level", "INFO"),
        file=log_raw.get("file")
    )

    config = GrowPiConfig(
        lamps=lamps_config,
        logging=logging_config,
        server=raw_config.get("server"),
        sensors=raw_config.get("sensors"),
        offline=raw_config.get("offline"),
        system=raw_config.get("system")
    )

    logger.info(f"Loaded {len(lamp_channels)} lamp channels")

    return config
