"""
Tuya Cloud API Service for Smart Plug Control

Provides cloud-based control for Tuya smart plugs via the official API.
Used for dehumidifier and other appliance control.
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# TinyTuya availability
TINYTUYA_AVAILABLE = False
try:
    import tinytuya
    TINYTUYA_AVAILABLE = True
except ImportError:
    logger.warning("tinytuya not available - smart plug control disabled")


class TuyaCloudService:
    """
    Tuya Cloud API client for controlling smart plugs.

    Usage:
        service = TuyaCloudService(
            access_id="your_access_id",
            access_secret="your_access_secret",
            region="eu"
        )
        service.switch_on("device_id")
        service.switch_off("device_id")
    """

    def __init__(
        self,
        access_id: str,
        access_secret: str,
        region: str = "eu"
    ):
        """
        Initialize Tuya Cloud connection.

        Args:
            access_id: Tuya IoT Access ID
            access_secret: Tuya IoT Access Secret
            region: Cloud region (eu, us, cn, in)
        """
        self.access_id = access_id
        self.access_secret = access_secret
        self.region = region
        self._cloud = None
        self._initialized = False

        if TINYTUYA_AVAILABLE:
            try:
                self._cloud = tinytuya.Cloud(
                    apiRegion=region,
                    apiKey=access_id,
                    apiSecret=access_secret
                )
                self._initialized = True
                logger.info(f"TuyaCloudService initialized (region: {region})")
            except Exception as e:
                logger.error(f"Failed to initialize Tuya Cloud: {e}")

    @property
    def is_available(self) -> bool:
        """Check if cloud service is available."""
        return self._initialized and self._cloud is not None

    def switch_on(self, device_id: str) -> bool:
        """
        Turn device ON.

        Args:
            device_id: Tuya device ID

        Returns:
            True if successful, False otherwise
        """
        return self._send_switch_command(device_id, True)

    def switch_off(self, device_id: str) -> bool:
        """
        Turn device OFF.

        Args:
            device_id: Tuya device ID

        Returns:
            True if successful, False otherwise
        """
        return self._send_switch_command(device_id, False)

    def _send_switch_command(self, device_id: str, state: bool) -> bool:
        """Send switch command to device."""
        if not self.is_available:
            logger.warning("Tuya Cloud not available")
            return False

        try:
            result = self._cloud.sendcommand(
                device_id,
                {'commands': [{'code': 'switch_1', 'value': state}]}
            )

            success = result.get('success', False)
            if success:
                logger.info(f"Device {device_id[:8]}... switched {'ON' if state else 'OFF'}")
            else:
                logger.warning(f"Switch command failed: {result}")

            return success

        except Exception as e:
            logger.error(f"Error sending switch command: {e}")
            return False

    def get_device_status(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Get device status including power consumption.

        Args:
            device_id: Tuya device ID

        Returns:
            Dict with status data or None if failed
        """
        if not self.is_available:
            return None

        try:
            result = self._cloud.getstatus(device_id)

            if result and 'result' in result:
                # Parse DPS values
                dps = {}
                for item in result['result']:
                    dps[item['code']] = item['value']

                return {
                    'switch': dps.get('switch_1', False),
                    'power': dps.get('cur_power', 0) / 10,  # Convert to W
                    'voltage': dps.get('cur_voltage', 0) / 10,  # Convert to V
                    'current': dps.get('cur_current', 0) / 1000,  # Convert to A
                    'raw': dps
                }

            return None

        except Exception as e:
            logger.error(f"Error getting device status: {e}")
            return None

    def get_devices(self) -> list:
        """
        Get all devices from Tuya Cloud.

        Returns:
            List of device dicts
        """
        if not self.is_available:
            return []

        try:
            return self._cloud.getdevices() or []
        except Exception as e:
            logger.error(f"Error fetching devices: {e}")
            return []


# Singleton instance
_tuya_service: Optional[TuyaCloudService] = None


def get_tuya_service() -> Optional[TuyaCloudService]:
    """
    Get or create singleton TuyaCloudService instance.

    Reads credentials from environment or config.
    """
    global _tuya_service

    if _tuya_service is not None:
        return _tuya_service

    # Try to load credentials
    access_id = None
    access_secret = None
    region = "eu"

    # Try environment variables first
    import os
    access_id = os.environ.get('TUYA_ACCESS_ID')
    access_secret = os.environ.get('TUYA_ACCESS_SECRET')
    region = os.environ.get('TUYA_REGION', 'eu')

    # Never fallback to hardcoded credentials in open-source code.
    if not access_id or not access_secret:
        logger.warning(
            "Tuya credentials missing. Set TUYA_ACCESS_ID/TUYA_ACCESS_SECRET in environment."
        )
        return None

    if access_id and access_secret:
        _tuya_service = TuyaCloudService(access_id, access_secret, region)
        return _tuya_service

    logger.warning("No Tuya credentials found")
    return None
