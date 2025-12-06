import logging
from dataclasses import dataclass
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

@dataclass
class LampCommand:
    channel: int
    intensity: int

@dataclass
class ServerConfig:
    sensor_interval: int
    lamps: List[Dict]

class GrowPiClient:
    """
    Client for communicating with the GrowPi VPS Server.
    
    Current Status: Skeleton Implementation (MVP Level 4b)
    """
    
    def __init__(self, server_url: str, api_key: str, timeout: int = 10):
        self.server_url = server_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        # self.session = requests.Session() # TODO: Uncomment when implementing
        
    def register(self, version: str, ip_address: str) -> Optional[ServerConfig]:
        """Register Pi with server and get initial configuration."""
        logger.info(f"Mock: Registering with server {self.server_url} (v{version})")
        return None
            
    def send_heartbeat(self, status: Dict[str, Any]) -> bool:
        """Send heartbeat to confirm Pi is online."""
        # logger.debug("Mock: Sending heartbeat")
        return True
            
    def send_readings(self, readings: List[Dict]) -> bool:
        """Send sensor readings to server."""
        # logger.debug(f"Mock: Sending {len(readings)} readings")
        return True
            
    def get_commands(self) -> Optional[Dict]:
        """Poll server for pending commands."""
        return None
            
    def get_lamp_curves(self) -> Optional[List[Dict]]:
        """Fetch current lamp curves from server."""
        return None
