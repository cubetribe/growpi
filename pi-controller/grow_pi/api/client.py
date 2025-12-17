"""
GrowPi VPS Sync Client
======================
Kommuniziert mit dem VPS Server für Daten-Sync und Command-Polling.

Server: https://growpi.nm-forum.de
API-Prefix: /api/pi/

Features:
- Registration & Token-Management
- Heartbeat (Health-Check)
- Sensor-Batch-Upload
- Lamp-Status-Sync
- Command-Polling & ACK
"""

import os
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

import httpx

logger = logging.getLogger(__name__)


@dataclass
class SyncConfig:
    """Konfiguration für VPS-Sync"""
    server_url: str
    api_token: Optional[str] = None
    pi_id: Optional[str] = None
    timeout: int = 10

    @classmethod
    def from_env(cls) -> 'SyncConfig':
        """Erstellt Config aus Environment-Variablen"""
        return cls(
            server_url=os.getenv('GROWPI_SERVER_URL', 'https://growpi.nm-forum.de'),
            api_token=os.getenv('GROWPI_API_TOKEN'),
            pi_id=os.getenv('GROWPI_PI_ID'),
            timeout=int(os.getenv('GROWPI_TIMEOUT', '10'))
        )


class GrowPiClient:
    """
    Client für VPS-Kommunikation.

    Features:
    - Registration & Token-Management
    - Heartbeat (alle 30s empfohlen)
    - Sensor-Batch-Upload
    - Command-Polling & ACK

    Usage:
        # Init with auto-config from env
        client = GrowPiClient()

        # Or with explicit config
        config = SyncConfig(server_url="https://growpi.nm-forum.de")
        client = GrowPiClient(config)

        # Register Pi
        result = client.register(
            serial="pi-12345",
            hostname="growpi",
            version="1.0.0"
        )

        # Send heartbeat
        client.send_heartbeat(
            uptime_seconds=3600,
            version="1.0.0",
            ip_local="192.168.1.100"
        )

        # Send sensor data
        client.send_readings([
            {
                'timestamp': '2025-12-16T12:00:00Z',
                'temperature': 22.5,
                'humidity': 65.0
            }
        ])

        # Poll commands
        commands = client.get_commands()
        for cmd in commands:
            # Execute command...
            success = True
            client.ack_command(cmd['id'], success, {'result': 'ok'})
    """

    def __init__(self, config: Optional[SyncConfig] = None):
        self.config = config or SyncConfig.from_env()
        self._client = httpx.Client(timeout=self.config.timeout)
        logger.info(f"GrowPiClient initialized (Server: {self.config.server_url})")

    def _headers(self) -> Dict[str, str]:
        """Standard-Headers mit API-Token"""
        headers = {'Content-Type': 'application/json'}
        if self.config.api_token:
            headers['X-Pi-Token'] = self.config.api_token
        return headers

    def _url(self, endpoint: str) -> str:
        """Baut vollständige URL"""
        base = self.config.server_url.rstrip('/')
        endpoint = endpoint.lstrip('/')
        return f"{base}/api/pi/{endpoint}"

    # =========================================
    # REGISTRATION
    # =========================================

    def register(self, serial: str, hostname: str, version: str) -> Dict[str, Any]:
        """
        Registriert Pi beim Server und erhält API-Token.

        Args:
            serial: Raspberry Pi Serial Number (z.B. aus /proc/cpuinfo)
            hostname: Hostname des Pi (z.B. 'growpi')
            version: Software-Version (z.B. '1.0.0')

        Returns:
            {
                'pi_id': str,           # UUID des registrierten Pi
                'api_token': str,       # API-Token für zukünftige Requests
                'zone': {               # Zugewiesene Zone
                    'id': str,
                    'name': str
                }
            }

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Example:
            >>> client = GrowPiClient()
            >>> result = client.register('pi-12345', 'growpi', '1.0.0')
            >>> print(result['api_token'])
            'abc123...'
        """
        try:
            logger.info(f"Registering Pi: {hostname} (Serial: {serial}, Version: {version})")

            response = self._client.post(
                self._url('register'),
                json={
                    'serial': serial,
                    'hostname': hostname,
                    'version': version
                },
                headers={'Content-Type': 'application/json'}
            )
            response.raise_for_status()

            data = response.json()

            # Speichere Token für zukünftige Requests
            self.config.api_token = data.get('api_token')
            self.config.pi_id = data.get('pi_id')

            logger.info(f"Registration successful. Pi ID: {self.config.pi_id}")
            logger.debug(f"API Token: {self.config.api_token[:10]}...")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Registration failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Registration error: {e}")
            raise

    # =========================================
    # HEARTBEAT
    # =========================================

    def send_heartbeat(
        self,
        uptime_seconds: int,
        version: str,
        ip_local: str,
        last_sensor_read: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Sendet Health-Check an Server.

        Args:
            uptime_seconds: System-Uptime in Sekunden
            version: Software-Version
            ip_local: Lokale IP-Adresse
            last_sensor_read: Timestamp des letzten Sensor-Reads (optional)

        Returns:
            {
                'status': 'ok',
                'commands_pending': bool,    # Gibt es ausstehende Commands?
                'server_time': str          # Aktuelle Server-Zeit (ISO)
            }

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Example:
            >>> result = client.send_heartbeat(3600, '1.0.0', '192.168.1.100')
            >>> if result['commands_pending']:
            ...     commands = client.get_commands()
        """
        try:
            payload = {
                'uptimeSeconds': uptime_seconds,
                'version': version,
                'ipLocal': ip_local
            }

            if last_sensor_read:
                payload['lastSensorRead'] = last_sensor_read.isoformat()

            logger.debug(f"Sending heartbeat (Uptime: {uptime_seconds}s, IP: {ip_local})")

            response = self._client.post(
                self._url('heartbeat'),
                json=payload,
                headers=self._headers()
            )
            response.raise_for_status()

            data = response.json()
            logger.debug(f"Heartbeat OK (Commands pending: {data.get('commands_pending', False)})")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Heartbeat failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Heartbeat error: {e}")
            raise

    # =========================================
    # SENSOR DATA
    # =========================================

    def send_readings(self, readings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sendet Sensor-Daten als Batch an Server.

        Args:
            readings: Liste von Sensor-Readings im Pi-Format
                [
                    {
                        'timestamp': str,        # ISO format
                        'temperature': float,    # Celsius
                        'humidity': float,       # Prozent
                        'soil_moisture': float,  # Prozent (optional)
                        'light': float,          # Lux (optional)
                        ...
                    }
                ]

        Returns:
            {
                'synced': int,          # Anzahl gespeicherter Readings
                'last_sync': str,       # Timestamp des letzten Syncs (ISO)
                'skipped': int          # Anzahl übersprungener Readings
            }

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Notes:
            - Max 50 Readings pro Request
            - Bei mehr als 50 Readings werden automatisch mehrere Requests gemacht
            - Timestamps sollten ISO-Format haben (z.B. '2025-12-16T12:00:00Z')
            - Format-Transformation: Pi-Format {'timestamp': '...', 'temperature': X, 'humidity': Y}
              wird transformiert zu Server-Format [{'type': 'temperature', 'value': X, 'timestamp': '...'}]

        Example:
            >>> readings = [
            ...     {
            ...         'timestamp': '2025-12-16T12:00:00Z',
            ...         'temperature': 22.5,
            ...         'humidity': 65.0
            ...     }
            ... ]
            >>> result = client.send_readings(readings)
            >>> print(f"Synced {result['synced']} readings")
        """
        if not readings:
            logger.warning("send_readings called with empty list")
            return {'synced': 0, 'last_sync': None, 'skipped': 0}

        # Transform Pi format to Server format
        # Pi: [{'timestamp': '...', 'temperature': 22.5, 'humidity': 65.0}]
        # Server: [{'type': 'temperature', 'value': 22.5, 'timestamp': '...'}]
        transformed_readings = []
        for reading in readings:
            timestamp = reading.get('timestamp', datetime.utcnow().isoformat() + 'Z')
            for key, value in reading.items():
                if key == 'timestamp':
                    continue
                if isinstance(value, (int, float)):
                    transformed_readings.append({
                        'type': key,
                        'value': value,
                        'timestamp': timestamp
                    })

        if not transformed_readings:
            logger.warning("No valid sensor values found after transformation")
            return {'synced': 0, 'last_sync': None, 'skipped': 0}

        # Max 50 Readings pro Request (Server-Limit)
        batch_size = 50
        total_synced = 0
        total_skipped = 0
        last_sync = None

        try:
            num_batches = (len(transformed_readings) + batch_size - 1) // batch_size
            logger.info(f"Sending {len(transformed_readings)} readings in {num_batches} batch(es)")

            for i in range(0, len(transformed_readings), batch_size):
                batch = transformed_readings[i:i + batch_size]
                batch_num = i // batch_size + 1

                logger.debug(f"Sending batch {batch_num}/{num_batches} ({len(batch)} readings)")

                response = self._client.post(
                    self._url('sensors'),
                    json={'readings': batch},
                    headers=self._headers()
                )
                response.raise_for_status()

                data = response.json()
                synced = data.get('synced', 0)
                skipped = data.get('skipped', 0)
                total_synced += synced
                total_skipped += skipped
                last_sync = data.get('last_sync')

                logger.debug(f"Batch {batch_num} complete: {synced} synced, {skipped} skipped")

            logger.info(f"Sensor sync complete: {total_synced} synced, {total_skipped} skipped")

            return {
                'synced': total_synced,
                'last_sync': last_sync,
                'skipped': total_skipped
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Sensor upload failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Sensor upload error: {e}")
            raise

    # =========================================
    # LAMP STATUS
    # =========================================

    def send_lamp_status(
        self,
        channels: List[Dict[str, Any]],
        curves_hash: str
    ) -> Dict[str, Any]:
        """
        Sendet aktuellen Lampenstatus an Server.

        Args:
            channels: Liste der Kanal-Stati im Pi-Format
                [
                    {
                        'channel': int,         # Kanal-Nummer
                        'name': str,           # Kanal-Name (z.B. 'Far Red')
                        'intensity': int,      # Aktuelle Intensität 0-100
                        'enabled': bool        # Ist Kanal aktiv?
                    }
                ]
            curves_hash: Hash der aktuellen Lichtkurven (z.B. MD5)

        Returns:
            {
                'status': 'ok',
                'timestamp': str           # Server-Timestamp (ISO)
            }

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Notes:
            - Format-Transformation: Pi-Format 'intensity' wird zu Server-Format 'current_pwm'

        Example:
            >>> channels = [
            ...     {'channel': 1, 'name': 'Far Red', 'intensity': 75, 'enabled': True},
            ...     {'channel': 2, 'name': 'UV', 'intensity': 0, 'enabled': False}
            ... ]
            >>> result = client.send_lamp_status(channels, 'abc123...')
        """
        try:
            logger.debug(f"Sending lamp status ({len(channels)} channels, hash: {curves_hash[:8]}...)")

            # Transform Pi format to Server format
            # Pi: {'channel': 1, 'intensity': 75, ...}
            # Server: {'channel': 1, 'current_pwm': 75}
            transformed_channels = []
            for ch in channels:
                transformed_channels.append({
                    'channel': ch.get('channel'),
                    'current_pwm': ch.get('intensity', ch.get('current_pwm', 0))
                })

            response = self._client.post(
                self._url('lamp-status'),
                json={
                    'channels': transformed_channels,
                    'curves_hash': curves_hash
                },
                headers=self._headers()
            )
            response.raise_for_status()

            data = response.json()
            logger.debug("Lamp status sent successfully")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Lamp status upload failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Lamp status upload error: {e}")
            raise

    # =========================================
    # COMMANDS
    # =========================================

    def get_commands(self) -> List[Dict[str, Any]]:
        """
        Holt ausstehende Befehle vom Server.

        Returns:
            [
                {
                    'id': str,              # Command-ID (UUID)
                    'type': str,            # Command-Type (z.B. 'set_lamp', 'reboot')
                    'payload': dict,        # Command-spezifische Daten
                    'created_at': str       # Erstellungszeitpunkt (ISO)
                }
            ]

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Example:
            >>> commands = client.get_commands()
            >>> for cmd in commands:
            ...     if cmd['type'] == 'set_lamp':
            ...         channel = cmd['payload']['channel']
            ...         intensity = cmd['payload']['intensity']
            ...         # Execute command...
            ...         client.ack_command(cmd['id'], True)
        """
        try:
            logger.debug("Polling for commands")

            response = self._client.get(
                self._url('commands'),
                headers=self._headers()
            )
            response.raise_for_status()

            data = response.json()
            commands = data.get('commands', [])

            if commands:
                logger.info(f"Received {len(commands)} pending command(s)")
                for cmd in commands:
                    logger.debug(f"  - Command {cmd.get('id')}: {cmd.get('type')}")
            else:
                logger.debug("No pending commands")

            return commands

        except httpx.HTTPStatusError as e:
            logger.error(f"Command polling failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Command polling error: {e}")
            raise

    def ack_command(
        self,
        command_id: str,
        success: bool,
        result: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Bestätigt Ausführung eines Befehls.

        Args:
            command_id: ID des Befehls (UUID)
            success: True wenn erfolgreich ausgeführt
            result: Optionales Ergebnis-Dict (z.B. Fehlermeldungen)

        Returns:
            {
                'status': 'acknowledged',
                'timestamp': str           # Server-Timestamp (ISO)
            }

        Raises:
            httpx.HTTPStatusError: Bei Server-Fehlern

        Notes:
            - Format-Transformation: Pi bool 'success' wird zu Server string 'status'
            - success=True -> status='completed'
            - success=False -> status='failed'

        Example:
            >>> # Bei Erfolg
            >>> client.ack_command('cmd-123', True, {'new_intensity': 75})

            >>> # Bei Fehler
            >>> client.ack_command('cmd-123', False, {'error': 'Invalid channel'})
        """
        try:
            logger.debug(f"Acknowledging command {command_id} (Success: {success})")

            # Transform Pi format to Server format
            # Pi: {'success': bool, 'result': {...}}
            # Server: {'status': 'completed'|'failed', 'result': {...}}
            response = self._client.post(
                self._url(f'commands/{command_id}/ack'),
                json={
                    'status': 'completed' if success else 'failed',
                    'result': result or {}
                },
                headers=self._headers()
            )
            response.raise_for_status()

            data = response.json()

            status_msg = 'success' if success else 'failed'
            logger.info(f"Command {command_id} acknowledged: {status_msg}")

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"Command ACK failed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Command ACK error: {e}")
            raise

    # =========================================
    # UTILITY
    # =========================================

    def is_registered(self) -> bool:
        """
        Prüft ob Pi registriert ist (Token vorhanden).

        Returns:
            True wenn api_token gesetzt ist

        Example:
            >>> if not client.is_registered():
            ...     result = client.register(serial, hostname, version)
        """
        return bool(self.config.api_token)

    def close(self):
        """Schließt HTTP-Client und gibt Ressourcen frei."""
        logger.debug("Closing HTTP client")
        self._client.close()

    def __enter__(self):
        """Context Manager Support"""
        return self

    def __exit__(self, *args):
        """Context Manager Support"""
        self.close()


# =========================================
# SINGLETON PATTERN
# =========================================

_client: Optional[GrowPiClient] = None


def get_client() -> GrowPiClient:
    """
    Gibt Singleton-Client zurück.

    Returns:
        GrowPiClient-Instanz (wird beim ersten Aufruf erstellt)

    Example:
        >>> from grow_pi.api.client import get_client
        >>> client = get_client()
        >>> client.send_heartbeat(3600, '1.0.0', '192.168.1.100')
    """
    global _client
    if _client is None:
        _client = GrowPiClient()
    return _client


def reset_client():
    """
    Setzt Singleton zurück (nützlich für Tests).

    Example:
        >>> from grow_pi.api.client import reset_client
        >>> reset_client()  # Nächster get_client() erstellt neue Instanz
    """
    global _client
    if _client:
        _client.close()
    _client = None
