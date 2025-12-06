"""
Lamp Configuration Service

Provides centralized lamp channel configuration management.
Loads configuration from config file and exposes it to blueprints.
"""

import logging
from dataclasses import dataclass
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class LampChannel:
    """Lamp channel configuration"""
    id: int
    name: str
    gpio_pin: int
    color: str


# Global lamp channels dictionary
_LAMP_CHANNELS: Dict[int, LampChannel] = {}


def load_lamp_channels() -> Dict[int, LampChannel]:
    """
    Load lamp channels from config file.

    Returns:
        Dictionary mapping channel ID to LampChannel configuration
    """
    global _LAMP_CHANNELS

    if _LAMP_CHANNELS:
        # Already loaded
        return _LAMP_CHANNELS

    try:
        # Try to load from config file
        try:
            from ...config import load_config
        except ImportError:
            from grow_pi.config import load_config

        config = load_config()

        # Colors for each channel: Far Red, Warm White, Cool White, UV
        colors = ["#ff4444", "#ffbb44", "#88ddff", "#cc66ff"]

        for i, ch in enumerate(config.lamps.channels):
            color = colors[i] if i < len(colors) else "#ffffff"
            _LAMP_CHANNELS[ch.channel] = LampChannel(
                id=ch.channel,
                name=ch.name,
                gpio_pin=ch.gpio_pin,
                color=color
            )

        logger.info(f"Loaded {len(_LAMP_CHANNELS)} lamp channels from config")

    except Exception as e:
        logger.warning(f"Failed to load lamp channels from config: {e}")
        logger.info("Using fallback lamp channel configuration")

        # Fallback - Final Pin Configuration 2025-12-05
        _LAMP_CHANNELS = {
            1: LampChannel(1, "Far Red", 16, "#ff4444"),
            2: LampChannel(2, "Warm White", 13, "#ffbb44"),
            3: LampChannel(3, "Cool White", 12, "#88ddff"),
            4: LampChannel(4, "UV", 18, "#cc66ff")
        }

    return _LAMP_CHANNELS


def get_lamp_channels() -> Dict[int, LampChannel]:
    """
    Get lamp channel configuration.

    Returns:
        Dictionary mapping channel ID to LampChannel configuration
    """
    if not _LAMP_CHANNELS:
        load_lamp_channels()
    return _LAMP_CHANNELS


def get_lamp_channel(channel_id: int) -> LampChannel:
    """
    Get configuration for a specific lamp channel.

    Args:
        channel_id: Channel ID (1-4)

    Returns:
        LampChannel configuration

    Raises:
        KeyError: If channel_id is invalid
    """
    channels = get_lamp_channels()
    return channels[channel_id]


def is_valid_channel(channel_id: int) -> bool:
    """
    Check if a channel ID is valid.

    Args:
        channel_id: Channel ID to check

    Returns:
        True if channel ID exists, False otherwise
    """
    return channel_id in get_lamp_channels()


# Initialize on module import
load_lamp_channels()
