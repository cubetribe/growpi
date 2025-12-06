import json
import os
import time
import logging
import tinytuya
from typing import Dict, Optional, List
from dotenv import load_dotenv

# Configure logging
logger = logging.getLogger(__name__)

class SmartPlugController:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SmartPlugController, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
            
        self.devices: Dict[str, tinytuya.OutletDevice] = {}
        self.cloud: Optional[tinytuya.Cloud] = None
        self.device_info: Dict[str, dict] = {}
        self.last_update: Dict[str, float] = {}
        self.cache: Dict[str, dict] = {}
        self.cache_ttl = 60.0  # Cache status for 60 seconds (Cloud API rate limits)
        
        self._load_config()
        self.initialized = True
        logger.info("SmartPlugController initialized")

    def _load_config(self):
        """Load configuration and initialize Cloud API"""
        # Load .env
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
        if not os.path.exists(env_path):
             env_path = os.path.join('/opt/grow-pi', '.env')
        
        load_dotenv(env_path)
        
        # Load devices.json
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'config', 'devices.json')
            if not os.path.exists(config_path):
                config_path = os.path.join('config', 'devices.json')
                
            if not os.path.exists(config_path):
                logger.error(f"devices.json not found at {config_path}")
                return

            with open(config_path, 'r') as f:
                data = json.load(f)
                
            # Initialize Cloud API if credentials exist
            tuya_config = data.get('tuya_cloud', {})
            api_key = tuya_config.get('access_id')
            api_secret = os.getenv('TUYA_ACCESS_SECRET')
            region = tuya_config.get('region', 'eu')
            
            if api_key and api_secret:
                try:
                    self.cloud = tinytuya.Cloud(
                        apiRegion=region, 
                        apiKey=api_key, 
                        apiSecret=api_secret, 
                        apiDeviceID=None # Not needed for init
                    )
                    logger.info("Tuya Cloud API initialized")
                except Exception as e:
                    logger.error(f"Failed to initialize Tuya Cloud: {e}")

            # Load Devices
            for device_cfg in data.get('devices', []):
                dev_id = device_cfg['device_id']
                self.device_info[dev_id] = device_cfg
                
                # WiFi Devices (Direct Control)
                if device_cfg.get('connection') == 'wifi' and device_cfg.get('ip'):
                    try:
                        device = tinytuya.OutletDevice(
                            dev_id=dev_id,
                            address=device_cfg['ip'],
                            local_key=device_cfg['local_key'],
                            version=float(device_cfg.get('version', 3.3))
                        )
                        device.set_socketPersistent(True)
                        self.devices[dev_id] = device
                        logger.info(f"Loaded WiFi Plug: {device_cfg['name']}")
                    except Exception as e:
                        logger.error(f"Failed to initialize WiFi plug {device_cfg.get('name')}: {e}")
                
                # BLE Devices (Cloud Control)
                elif device_cfg.get('connection') == 'ble':
                     logger.info(f"Loaded BLE Plug (Cloud): {device_cfg['name']}")
                        
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")

    def get_plugs(self) -> List[dict]:
        """Get list of all configured plugs"""
        return list(self.device_info.values())

    def get_status(self, device_id: str) -> Optional[dict]:
        """Get current status (voltage, current, power)"""
        # Check cache
        now = time.time()
        if device_id in self.cache and (now - self.last_update.get(device_id, 0)) < self.cache_ttl:
            return self.cache[device_id]

        # 1. Try WiFi (Local)
        device = self.devices.get(device_id)
        if device:
            try:
                status = device.status()
                if status and 'dps' in status:
                    dps = status['dps']
                    result = {
                        'on': dps.get('1', False),
                        'power': float(dps.get('19', 0)) / 10.0,
                        'voltage': float(dps.get('20', 0)) / 10.0,
                        'current': float(dps.get('18', 0)) / 1000.0,
                        'updated_at': now
                    }
                    self.cache[device_id] = result
                    self.last_update[device_id] = now
                    return result
            except Exception as e:
                logger.error(f"Error getting local status for {device_id}: {e}")

        # 2. Try Cloud (BLE)
        if self.cloud:
            try:
                # Get status from Cloud
                status = self.cloud.getstatus(device_id)
                if status and 'result' in status:
                    # Cloud returns list of dicts: [{'code': 'switch_1', 'value': True}, ...]
                    result_data = {item['code']: item['value'] for item in status['result']}
                    
                    # Map Cloud codes to our format
                    # Note: Codes vary by device. Common: switch_1, cur_power, cur_voltage, cur_current
                    result = {
                        'on': result_data.get('switch_1', False),
                        'power': float(result_data.get('cur_power', 0)) / 10.0,
                        'voltage': float(result_data.get('cur_voltage', 0)) / 10.0,
                        'current': float(result_data.get('cur_current', 0)) / 1000.0,
                        'updated_at': now
                    }
                    self.cache[device_id] = result
                    self.last_update[device_id] = now
                    return result
            except Exception as e:
                logger.error(f"Error getting cloud status for {device_id}: {e}")

        return None

    def turn_on(self, device_id: str) -> bool:
        """Turn plug on"""
        # 1. WiFi
        device = self.devices.get(device_id)
        if device:
            try:
                device.turn_on()
                if device_id in self.last_update: del self.last_update[device_id]
                return True
            except Exception as e:
                logger.error(f"Error turning on {device_id} (Local): {e}")

        # 2. Cloud
        if self.cloud:
            try:
                self.cloud.sendcommand(device_id, {'commands': [{'code': 'switch_1', 'value': True}]})
                if device_id in self.last_update: del self.last_update[device_id]
                return True
            except Exception as e:
                logger.error(f"Error turning on {device_id} (Cloud): {e}")
        
        return False

    def turn_off(self, device_id: str) -> bool:
        """Turn plug off"""
        # 1. WiFi
        device = self.devices.get(device_id)
        if device:
            try:
                device.turn_off()
                if device_id in self.last_update: del self.last_update[device_id]
                return True
            except Exception as e:
                logger.error(f"Error turning off {device_id} (Local): {e}")

        # 2. Cloud
        if self.cloud:
            try:
                self.cloud.sendcommand(device_id, {'commands': [{'code': 'switch_1', 'value': False}]})
                if device_id in self.last_update: del self.last_update[device_id]
                return True
            except Exception as e:
                logger.error(f"Error turning off {device_id} (Cloud): {e}")
        
        return False
