"""
GrowPi PWM Controller

Controls 5 LED lamp channels via GPIO PWM signals using pigpio daemon.

Hardware PWM Channels (Pi 3B+):
- Channel 1 (Red):        GPIO-12 (Pin 32)
- Channel 2 (Blue):       GPIO-13 (Pin 33)
- Channel 3 (Warm White): GPIO-18 (Pin 12) - VERIFIED
- Channel 4 (Cool White): GPIO-19 (Pin 35)
- Channel 5 (UV):         GPIO-21 (Pin 40) - Software PWM
"""

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Try to import pigpio - will fail on non-Pi systems
try:
    import pigpio
    PIGPIO_AVAILABLE = True
except ImportError:
    PIGPIO_AVAILABLE = False
    logger.warning("pigpio not available - running in simulation mode")


@dataclass
class LampChannel:
    """Runtime state for a single lamp channel"""
    channel: int
    name: str
    gpio_pin: int
    pwm_frequency: int
    software_pwm: bool
    current_intensity: int = 0


# Singleton instance
_pwm_controller_instance: Optional["PWMController"] = None


def get_pwm_controller() -> "PWMController":
    """
    Get the global PWMController singleton instance.

    Returns:
        The shared PWMController instance
    """
    global _pwm_controller_instance
    if _pwm_controller_instance is None:
        _pwm_controller_instance = PWMController()
    return _pwm_controller_instance


class PWMController:
    """
    PWM Controller for GrowPi LED lamps.

    Uses pigpio daemon for hardware PWM control.
    Falls back to simulation mode when pigpio is not available.

    Note: Use get_pwm_controller() to get the singleton instance.
    """

    def __init__(self):
        self.pi: Optional["pigpio.pi"] = None
        self.channels: Dict[int, LampChannel] = {}
        self.simulation_mode = not PIGPIO_AVAILABLE
        self._initialized = False

    def initialize(self, channels_config: List[dict]) -> bool:
        """
        Initialize pigpio and configure PWM channels.

        Args:
            channels_config: List of channel configurations with keys:
                - channel: int (1-5)
                - name: str
                - gpio_pin: int
                - pwm_frequency: int (default 1000)
                - software_pwm: bool (default False)

        Returns:
            True if initialization successful
        """
        if self.simulation_mode:
            logger.warning("PWM Controller running in SIMULATION MODE")
            self._init_simulation(channels_config)
            return True

        try:
            # Connect to pigpio daemon
            self.pi = pigpio.pi()
            if not self.pi.connected:
                raise RuntimeError(
                    "Failed to connect to pigpio daemon.\n"
                    "Run: sudo systemctl start pigpiod"
                )

            # Configure each channel
            for ch_config in channels_config:
                channel = LampChannel(
                    channel=ch_config.channel,
                    name=ch_config.name,
                    gpio_pin=ch_config.gpio_pin,
                    pwm_frequency=ch_config.pwm_frequency,
                    software_pwm=ch_config.software_pwm,
                    current_intensity=0
                )
                self.channels[channel.channel] = channel

                # Set PWM frequency
                self.pi.set_PWM_frequency(channel.gpio_pin, channel.pwm_frequency)

                # Set PWM range to 0-100 for easier percentage control
                self.pi.set_PWM_range(channel.gpio_pin, 100)

                # Start with 0% intensity
                self.pi.set_PWM_dutycycle(channel.gpio_pin, 0)

                logger.debug(
                    f"Configured channel {channel.channel} ({channel.name}) "
                    f"on GPIO-{channel.gpio_pin}"
                )

            self._initialized = True
            logger.info(f"PWM Controller initialized with {len(self.channels)} channels")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize PWM controller: {e}")
            return False

    def _init_simulation(self, channels_config: List[dict]) -> None:
        """Initialize channels in simulation mode (no GPIO)"""
        for ch_config in channels_config:
            channel = LampChannel(
                channel=ch_config.channel,
                name=ch_config.name,
                gpio_pin=ch_config.gpio_pin,
                pwm_frequency=ch_config.pwm_frequency,
                software_pwm=ch_config.software_pwm,
                current_intensity=0
            )
            self.channels[channel.channel] = channel

        self._initialized = True
        logger.info(f"Simulation mode: {len(self.channels)} channels configured")

    def set_intensity(self, channel: int, intensity: int) -> bool:
        """
        Set lamp intensity for a specific channel.

        Args:
            channel: Channel number (1-5)
            intensity: Intensity percentage (0-100)

        Returns:
            True if successful
        """
        if not self._initialized:
            logger.error("PWM Controller not initialized")
            return False

        if channel not in self.channels:
            logger.error(f"Unknown channel: {channel}")
            return False

        # Clamp intensity to valid range
        intensity = max(0, min(100, intensity))

        ch = self.channels[channel]

        if self.simulation_mode:
            ch.current_intensity = intensity
            logger.debug(f"[SIM] Channel {channel} ({ch.name}): {intensity}%")
            return True

        try:
            # Set PWM duty cycle (range is 0-100)
            self.pi.set_PWM_dutycycle(ch.gpio_pin, intensity)
            ch.current_intensity = intensity
            logger.debug(f"Channel {channel} ({ch.name}): {intensity}%")
            return True

        except Exception as e:
            logger.error(f"Failed to set PWM for channel {channel}: {e}")
            return False

    def set_all_intensities(self, intensities: Dict[int, int]) -> None:
        """
        Set intensities for multiple channels at once.

        Args:
            intensities: Dict mapping channel number to intensity
        """
        for channel, intensity in intensities.items():
            self.set_intensity(channel, intensity)

    def all_on(self, intensity: int = 100) -> None:
        """Turn all lamps to specified intensity."""
        logger.info(f"All lamps ON at {intensity}%")
        for channel in self.channels:
            self.set_intensity(channel, intensity)

    def all_off(self) -> None:
        """Turn all lamps off."""
        logger.info("All lamps OFF")
        for channel in self.channels:
            self.set_intensity(channel, 0)

    def get_current_state(self) -> Dict[int, int]:
        """
        Get current intensity of all channels.

        Returns:
            Dict mapping channel number to current intensity
        """
        return {
            ch: self.channels[ch].current_intensity
            for ch in self.channels
        }

    def get_channel_info(self) -> List[Dict]:
        """
        Get detailed info for all channels.

        Returns:
            List of channel info dicts
        """
        return [
            {
                "channel": ch.channel,
                "name": ch.name,
                "gpio_pin": ch.gpio_pin,
                "intensity": ch.current_intensity,
                "software_pwm": ch.software_pwm
            }
            for ch in self.channels.values()
        ]

    def cleanup(self) -> None:
        """Cleanup GPIO resources."""
        if self.simulation_mode:
            logger.info("Simulation mode: cleanup complete")
            return

        if self.pi and self.pi.connected:
            # Turn all lamps off before cleanup
            self.all_off()
            self.pi.stop()
            logger.info("PWM Controller cleaned up")

        self._initialized = False
