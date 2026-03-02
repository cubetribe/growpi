"""
GrowPi Multi-Channel Curve Controller

Verwaltet individuelle Lichtkurven pro Kanal und berechnet interpolierte Intensitäten.
Ersetzt die alte sun_curve.py für per-Kanal Kontrolle.

Sunrise Sequence (Standard):
  - Far Red (ch1): Startet zuerst um 05:00
  - Cool White (ch3): Startet 15min später um 05:15
  - Warm White (ch2): Startet 30min später um 05:30
  - UV (ch4): Bleibt immer auf 0

Sunset Sequence (umgekehrt):
  - Warm White fällt zuerst
  - Cool White folgt
  - Far Red fällt zuletzt
"""

import logging
from datetime import datetime, time
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def parse_time(time_str: str) -> time:
    """Parse "HH:MM" String zu time Objekt."""
    hours, minutes = map(int, time_str.split(":"))
    return time(hours, minutes)


def time_to_minutes(t: time) -> int:
    """Konvertiert time zu Minuten seit Mitternacht."""
    return t.hour * 60 + t.minute


def interpolate_curve(curve_points: List[Dict], current_time: Optional[datetime] = None) -> int:
    """
    Berechnet Intensität für aktuelle Zeit basierend auf Kurve.

    Verwendet lineare Interpolation zwischen Kurven-Punkten.
    Unterstützt Mitternachts-Wraparound (23:59 → 00:00).

    Args:
        curve_points: Liste von {time: "HH:MM", intensity: 0-100}
        current_time: Aktuelle Zeit (default: jetzt)

    Returns:
        Interpolierte Intensität (0-100)
    """
    if not curve_points:
        return 0

    if current_time is None:
        current_time = datetime.now()

    # Kurve nach Zeit sortieren
    sorted_curve = sorted(curve_points, key=lambda p: parse_time(p['time']))

    current = current_time.time()
    current_minutes = time_to_minutes(current)

    # Finde umgebende Punkte
    prev_point = sorted_curve[-1]  # Letzter Punkt (für Wraparound)
    next_point = sorted_curve[0]   # Erster Punkt (für Wraparound)

    for i, point in enumerate(sorted_curve):
        point_time = parse_time(point['time'])
        point_minutes = time_to_minutes(point_time)

        if point_minutes > current_minutes:
            next_point = point
            prev_point = sorted_curve[i - 1] if i > 0 else sorted_curve[-1]
            break
    else:
        # Aktuelle Zeit ist nach allen Punkten
        prev_point = sorted_curve[-1]
        next_point = sorted_curve[0]

    # Berechne Interpolation
    prev_minutes = time_to_minutes(parse_time(prev_point['time']))
    next_minutes = time_to_minutes(parse_time(next_point['time']))

    # Handle Mitternachts-Wraparound
    if next_minutes <= prev_minutes:
        next_minutes += 24 * 60
    if current_minutes < prev_minutes:
        current_minutes += 24 * 60

    # Lineare Interpolation
    if next_minutes == prev_minutes:
        return prev_point['intensity']

    ratio = (current_minutes - prev_minutes) / (next_minutes - prev_minutes)
    intensity = prev_point['intensity'] + ratio * (next_point['intensity'] - prev_point['intensity'])

    return int(round(intensity))


class CurveController:
    """
    Multi-Channel Curve Controller.

    Verwaltet individuelle Lichtkurven pro Kanal und berechnet
    interpolierte Intensitäten für alle Kanäle gleichzeitig.

    Usage:
        controller = CurveController(db)
        controller.initialize()

        # Aktuelle Intensitäten abrufen
        intensities = controller.get_current_intensities()
        # {1: 45, 2: 30, 3: 38, 4: 0}

        # Kurve für einen Kanal aktualisieren
        controller.update_curve(1, [
            {"time": "05:00", "intensity": 0},
            {"time": "06:00", "intensity": 50},
        ])
    """

    def __init__(self, db=None):
        """
        Initialize CurveController.

        Args:
            db: Database instance (uses global if None)
        """
        from ..database import get_database
        self.db = db or get_database()
        self._curves: Dict[int, List[Dict]] = {}
        self._enabled: Dict[int, bool] = {}
        self._names: Dict[int, str] = {}
        self._initialized = False

    def initialize(self, channels: Dict[int, str] = None) -> None:
        """
        Initialize curves from database or create defaults.

        Args:
            channels: Dict mapping channel number to name {1: "Far Red", ...}
                     If None, uses default channel names
        """
        if channels is None:
            channels = {
                1: "Far Red",
                2: "Warm White",
                3: "Cool White",
                4: "UV"
            }

        # Initialize default curves in database if not exist
        self.db.initialize_default_curves(channels)

        # Load all curves from database
        self._load_curves()
        self._initialized = True

        logger.info(f"CurveController initialized with {len(self._curves)} channels")

    def _load_curves(self) -> None:
        """Load all curves from database."""
        curves = self.db.get_all_lamp_curves()
        self._curves.clear()
        self._enabled.clear()
        self._names.clear()

        for curve in curves:
            self._curves[curve.channel] = curve.curve
            self._enabled[curve.channel] = curve.enabled
            self._names[curve.channel] = curve.name
            logger.debug(f"Loaded curve for {curve.name} (ch{curve.channel}): {len(curve.curve)} points")

    def get_current_intensities(self, current_time: Optional[datetime] = None) -> Dict[int, int]:
        """
        Calculate current intensity for all channels.

        Args:
            current_time: Time to calculate for (default: now)

        Returns:
            Dict mapping channel to intensity {1: 45, 2: 30, ...}
        """
        if not self._initialized:
            logger.warning("CurveController not initialized, returning zeros")
            return {ch: 0 for ch in range(1, 5)}

        result = {}
        for channel in range(1, 5):
            if channel in self._curves and self._enabled.get(channel, False):
                result[channel] = interpolate_curve(self._curves[channel], current_time)
            else:
                result[channel] = 0

        return result

    def get_intensity(self, channel: int, current_time: Optional[datetime] = None) -> int:
        """
        Calculate current intensity for a specific channel.

        Args:
            channel: Channel number (1-4)
            current_time: Time to calculate for (default: now)

        Returns:
            Intensity (0-100)
        """
        if channel not in self._curves or not self._enabled.get(channel, False):
            return 0
        return interpolate_curve(self._curves[channel], current_time)

    def get_curve(self, channel: int) -> Optional[List[Dict]]:
        """Get curve points for a channel."""
        return self._curves.get(channel)

    def get_all_curves(self) -> Dict[int, List[Dict]]:
        """Get all curves."""
        return self._curves.copy()

    def update_curve(self, channel: int, curve_points: List[Dict], enabled: bool = True) -> bool:
        """
        Update curve for a channel.

        Args:
            channel: Channel number (1-4)
            curve_points: List of {time, intensity} dicts
            enabled: Whether curve is active

        Returns:
            True if successful
        """
        if not 1 <= channel <= 4:
            logger.error(f"Invalid channel: {channel}")
            return False

        # Validate curve points
        for point in curve_points:
            if 'time' not in point or 'intensity' not in point:
                logger.error(f"Invalid curve point: {point}")
                return False
            if not 0 <= point['intensity'] <= 100:
                logger.error(f"Invalid intensity: {point['intensity']}")
                return False

        # Update in database
        result = self.db.update_lamp_curve(channel, curve_points, enabled)
        if result:
            self._curves[channel] = curve_points
            self._enabled[channel] = enabled
            logger.info(f"Updated curve for channel {channel}: {len(curve_points)} points")
            return True

        logger.error(f"Failed to update curve for channel {channel}")
        return False

    def reload_from_database(self) -> None:
        """
        Reload all curves from database.

        Required in split-process mode where curve edits happen in the web
        service process and the controller process must pick up updates.
        """
        self._load_curves()

    def set_enabled(self, channel: int, enabled: bool) -> bool:
        """Enable or disable a channel's curve."""
        if channel not in self._curves:
            return False

        result = self.db.update_lamp_curve(channel, self._curves[channel], enabled)
        if result:
            self._enabled[channel] = enabled
            return True
        return False

    def is_enabled(self, channel: int) -> bool:
        """Check if a channel's curve is enabled."""
        return self._enabled.get(channel, False)

    def get_channel_name(self, channel: int) -> str:
        """Get name for a channel."""
        return self._names.get(channel, f"Channel {channel}")

    def print_preview(self, hours: List[int] = None) -> None:
        """
        Print 24h preview of all channels.

        Args:
            hours: Specific hours to show (default: all 24)
        """
        if hours is None:
            hours = list(range(24))

        print("\n" + "=" * 70)
        print("Kurven-Vorschau - Alle Kanäle")
        print("=" * 70)
        print(f"{'Zeit':<8}", end="")
        for ch in range(1, 5):
            name = self._names.get(ch, f"Ch{ch}")[:10]
            print(f"{name:<15}", end="")
        print()
        print("-" * 70)

        for hour in hours:
            test_time = datetime.now().replace(hour=hour, minute=0, second=0)
            intensities = self.get_current_intensities(test_time)
            print(f"{hour:02d}:00   ", end="")
            for ch in range(1, 5):
                intensity = intensities.get(ch, 0)
                bar = "█" * (intensity // 5) if intensity > 0 else "-"
                print(f"{intensity:3d}% {bar:<10}", end="")
            print()

        print("=" * 70 + "\n")

    def get_status(self) -> Dict:
        """Get controller status for API."""
        return {
            'initialized': self._initialized,
            'channels': {
                ch: {
                    'name': self._names.get(ch, f"Channel {ch}"),
                    'enabled': self._enabled.get(ch, False),
                    'points': len(self._curves.get(ch, [])),
                }
                for ch in range(1, 5)
            }
        }


# Global instance
_controller_instance: Optional[CurveController] = None


def get_curve_controller(db=None) -> CurveController:
    """Get or create global CurveController instance."""
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = CurveController(db)
    return _controller_instance


# Convenience function for quick test
if __name__ == "__main__":
    # Test with mock data
    print("Testing CurveController...")

    # Test interpolation
    test_curve = [
        {"time": "05:00", "intensity": 0},
        {"time": "06:00", "intensity": 50},
        {"time": "20:00", "intensity": 50},
        {"time": "21:00", "intensity": 0},
    ]

    for hour in [4, 5, 6, 12, 20, 21, 22]:
        test_time = datetime.now().replace(hour=hour, minute=0)
        intensity = interpolate_curve(test_curve, test_time)
        print(f"{hour:02d}:00 -> {intensity}%")
