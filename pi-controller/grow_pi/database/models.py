"""
GrowPi Database Models

Dataclasses für Datenbank-Einträge.
Kompatibel mit PostgreSQL-Server Schema für spätere Synchronisation.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
import uuid


def generate_uuid() -> str:
    """Generate UUID v4 string."""
    return str(uuid.uuid4())


def now_iso() -> str:
    """Current timestamp in ISO 8601 format."""
    return datetime.now().isoformat()


@dataclass
class SensorReading:
    """
    Sensor-Messwert (Temperatur, Luftfeuchtigkeit, etc.)

    Kompatibel mit Server-Schema: SensorReading model
    """
    sensor_type: str        # 'temperature', 'humidity', 'soil_moisture', etc.
    value: float            # Messwert
    unit: str               # '°C', '%', 'pH', etc.
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=now_iso)
    synced_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            'id': self.id,
            'sensor_type': self.sensor_type,
            'value': self.value,
            'unit': self.unit,
            'created_at': self.created_at,
            'synced_at': self.synced_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'SensorReading':
        """Create from database row."""
        return cls(
            id=row[0],
            sensor_type=row[1],
            value=row[2],
            unit=row[3],
            created_at=row[4],
            synced_at=row[5],
        )


@dataclass
class LampStateLog:
    """
    Lampen-Zustandsprotokoll

    Protokolliert jeden Lampenzustand mit Quelle und Zeitstempel.
    Kritisch für Analyse der Lichtzyklen (Sonnenauf-/untergang).
    """
    channel: int            # Kanal 1-4
    name: str               # 'Far Red', 'Warm White', etc.
    intensity: int          # 0-100%
    source: str             # 'curve', 'manual', 'api', 'override', 'startup', 'shutdown'
    curve_time: Optional[str] = None  # Geplante Zeit aus Kurve (falls source='curve')
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=now_iso)
    synced_at: Optional[str] = None

    # Gültige Source-Typen
    VALID_SOURCES = {'curve', 'manual', 'api', 'override', 'startup', 'shutdown', 'periodic'}

    def __post_init__(self):
        """Validate source type."""
        if self.source not in self.VALID_SOURCES:
            raise ValueError(f"Invalid source: {self.source}. Must be one of {self.VALID_SOURCES}")
        if not 0 <= self.intensity <= 100:
            raise ValueError(f"Invalid intensity: {self.intensity}. Must be 0-100")
        if not 1 <= self.channel <= 4:
            raise ValueError(f"Invalid channel: {self.channel}. Must be 1-4")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            'id': self.id,
            'channel': self.channel,
            'name': self.name,
            'intensity': self.intensity,
            'source': self.source,
            'curve_time': self.curve_time,
            'created_at': self.created_at,
            'synced_at': self.synced_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'LampStateLog':
        """Create from database row."""
        return cls(
            id=row[0],
            channel=row[1],
            name=row[2],
            intensity=row[3],
            source=row[4],
            curve_time=row[5],
            created_at=row[6],
            synced_at=row[7],
        )


@dataclass
class SystemEvent:
    """
    System-Ereignis für Debugging und Audit.

    Protokolliert Service-Start/Stop, Fehler, Config-Änderungen.
    """
    event_type: str         # 'service_start', 'error', 'config_change', etc.
    severity: str           # 'info', 'warning', 'error', 'critical'
    message: str            # Kurze Beschreibung
    details: Optional[str] = None  # JSON mit zusätzlichen Details
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=now_iso)

    # Gültige Event-Typen
    VALID_EVENT_TYPES = {
        'service_start', 'service_stop', 'config_change',
        'sensor_error', 'pwm_error', 'database_error',
        'sync_start', 'sync_complete', 'sync_error',
        'lamp_change', 'curve_update'
    }

    # Gültige Severity-Level
    VALID_SEVERITIES = {'info', 'warning', 'error', 'critical'}

    def __post_init__(self):
        """Validate event_type and severity."""
        if self.event_type not in self.VALID_EVENT_TYPES:
            raise ValueError(f"Invalid event_type: {self.event_type}")
        if self.severity not in self.VALID_SEVERITIES:
            raise ValueError(f"Invalid severity: {self.severity}")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            'id': self.id,
            'event_type': self.event_type,
            'severity': self.severity,
            'message': self.message,
            'details': self.details,
            'created_at': self.created_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'SystemEvent':
        """Create from database row."""
        return cls(
            id=row[0],
            event_type=row[1],
            severity=row[2],
            message=row[3],
            details=row[4],
            created_at=row[5],
        )


# Sensor-Typen Konstanten (für Konsistenz)
class SensorType:
    """Konstanten für Sensor-Typen."""
    TEMPERATURE = 'temperature'
    HUMIDITY = 'humidity'
    SOIL_MOISTURE = 'soil_moisture'
    SOIL_TEMP = 'soil_temp'
    SOIL_PH = 'soil_ph'
    SOIL_EC = 'soil_ec'
    SOIL_N = 'soil_n'
    SOIL_P = 'soil_p'
    SOIL_K = 'soil_k'


# Einheiten für Sensor-Typen
SENSOR_UNITS = {
    SensorType.TEMPERATURE: '°C',
    SensorType.HUMIDITY: '%',
    SensorType.SOIL_MOISTURE: '%',
    SensorType.SOIL_TEMP: '°C',
    SensorType.SOIL_PH: 'pH',
    SensorType.SOIL_EC: 'mS/cm',
    SensorType.SOIL_N: 'mg/kg',
    SensorType.SOIL_P: 'mg/kg',
    SensorType.SOIL_K: 'mg/kg',
}


@dataclass
class CurvePoint:
    """
    Ein Punkt auf der Lichtkurve.

    Verwendet für per-Kanal Kurven-Definition.
    """
    time: str       # Format: "HH:MM"
    intensity: int  # 0-100%

    def __post_init__(self):
        """Validate time format and intensity."""
        # Validate time format
        try:
            hours, minutes = map(int, self.time.split(":"))
            if not (0 <= hours <= 23 and 0 <= minutes <= 59):
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError(f"Invalid time format: {self.time}. Must be HH:MM")

        # Validate intensity
        if not 0 <= self.intensity <= 100:
            raise ValueError(f"Invalid intensity: {self.intensity}. Must be 0-100")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {'time': self.time, 'intensity': self.intensity}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CurvePoint':
        """Create from dictionary."""
        return cls(time=data['time'], intensity=data['intensity'])


@dataclass
class LampCurve:
    """
    Lichtkurve für einen Lampen-Kanal.

    Jeder Kanal hat seine eigene Kurve für individuelle Sonnenauf-/untergang Sequenzen.
    """
    channel: int                    # Kanal 1-4
    name: str                       # 'Far Red', 'Warm White', etc.
    enabled: bool = True            # Kurve aktiv?
    curve: List[Dict[str, Any]] = field(default_factory=list)  # [{time, intensity}, ...]
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=now_iso)
    updated_at: str = field(default_factory=now_iso)
    synced_at: Optional[str] = None

    def __post_init__(self):
        """Validate channel."""
        if not 1 <= self.channel <= 4:
            raise ValueError(f"Invalid channel: {self.channel}. Must be 1-4")

    def get_curve_points(self) -> List[CurvePoint]:
        """Convert curve list to CurvePoint objects."""
        return [CurvePoint.from_dict(p) for p in self.curve]

    def set_curve_points(self, points: List[CurvePoint]) -> None:
        """Set curve from CurvePoint objects."""
        self.curve = [p.to_dict() for p in points]
        self.updated_at = now_iso()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            'id': self.id,
            'channel': self.channel,
            'name': self.name,
            'enabled': self.enabled,
            'curve': self.curve,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'synced_at': self.synced_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'LampCurve':
        """Create from database row."""
        import json
        curve_data = row[4]
        if isinstance(curve_data, str):
            curve_data = json.loads(curve_data)
        return cls(
            id=row[0],
            channel=row[1],
            name=row[2],
            enabled=bool(row[3]),
            curve=curve_data,
            created_at=row[5],
            updated_at=row[6],
            synced_at=row[7],
        )


@dataclass
class PlugLog:
    """
    Smart Plug Log Entry.
    
    Protokolliert Spannung, Strom und Leistung von Smart Plugs.
    """
    device_id: str
    voltage: float          # V
    current: float          # A
    power: float            # W
    id: str = field(default_factory=generate_uuid)
    created_at: str = field(default_factory=now_iso)
    synced_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database insert."""
        return {
            'id': self.id,
            'device_id': self.device_id,
            'voltage': self.voltage,
            'current': self.current,
            'power': self.power,
            'created_at': self.created_at,
            'synced_at': self.synced_at,
        }

    @classmethod
    def from_row(cls, row: tuple) -> 'PlugLog':
        """Create from database row."""
        return cls(
            id=row[0],
            device_id=row[1],
            voltage=row[2],
            current=row[3],
            power=row[4],
            created_at=row[5],
            synced_at=row[6],
        )
