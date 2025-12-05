"""
GrowPi Sun Curve Interpolation

Berechnet Lampen-Intensität basierend auf Tageszeit.
Emuliert natürlichen Sonnenverlauf mit Auf- und Untergang.

Standard-Kurve:
  05:00 - 08:00  → Sonnenaufgang: 10% → 60%
  08:00 - 20:00  → Tageslicht: 60%
  20:00 - 23:00  → Sonnenuntergang: 60% → 10%
  23:00 - 05:00  → Nacht: 0%
"""

from dataclasses import dataclass
from datetime import datetime, time
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class CurvePoint:
    """Ein Punkt auf der Lichtkurve"""
    time: str       # Format: "HH:MM"
    intensity: int  # 0-100%


def parse_time(time_str: str) -> time:
    """Parse "HH:MM" String zu time Objekt."""
    hours, minutes = map(int, time_str.split(":"))
    return time(hours, minutes)


def time_to_minutes(t: time) -> int:
    """Konvertiert time zu Minuten seit Mitternacht."""
    return t.hour * 60 + t.minute


def interpolate_intensity(curve: List[CurvePoint], current_time: Optional[datetime] = None) -> int:
    """
    Berechnet Lampen-Intensität für aktuelle Zeit basierend auf Kurve.

    Verwendet lineare Interpolation zwischen Kurven-Punkten.
    Unterstützt Mitternachts-Wraparound (23:59 → 00:00).

    Args:
        curve: Liste von CurvePoints, sortiert nach Zeit
        current_time: Aktuelle Zeit (default: jetzt)

    Returns:
        Interpolierte Intensität (0-100)
    """
    if not curve:
        return 0

    if current_time is None:
        current_time = datetime.now()

    # Kurve nach Zeit sortieren
    sorted_curve = sorted(curve, key=lambda p: parse_time(p.time))

    current = current_time.time()
    current_minutes = time_to_minutes(current)

    # Finde umgebende Punkte
    prev_point = sorted_curve[-1]  # Letzter Punkt (für Wraparound)
    next_point = sorted_curve[0]   # Erster Punkt (für Wraparound)

    for i, point in enumerate(sorted_curve):
        point_time = parse_time(point.time)
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
    prev_minutes = time_to_minutes(parse_time(prev_point.time))
    next_minutes = time_to_minutes(parse_time(next_point.time))

    # Handle Mitternachts-Wraparound
    if next_minutes <= prev_minutes:
        next_minutes += 24 * 60
    if current_minutes < prev_minutes:
        current_minutes += 24 * 60

    # Lineare Interpolation
    if next_minutes == prev_minutes:
        return prev_point.intensity

    ratio = (current_minutes - prev_minutes) / (next_minutes - prev_minutes)
    intensity = prev_point.intensity + ratio * (next_point.intensity - prev_point.intensity)

    return int(round(intensity))


def get_default_sun_curve() -> List[CurvePoint]:
    """
    Standard-Sonnenkurve für Gewächshaus.

    05:00 - 08:00  → Sonnenaufgang: 10% → 60%
    08:00 - 20:00  → Tageslicht: 60%
    20:00 - 23:00  → Sonnenuntergang: 60% → 10%
    23:00 - 05:00  → Nacht: 0%

    Returns:
        Liste von CurvePoints
    """
    return [
        CurvePoint(time="05:00", intensity=10),   # Sonnenaufgang Start
        CurvePoint(time="08:00", intensity=60),   # Sonnenaufgang Ende / Tag Start
        CurvePoint(time="20:00", intensity=60),   # Tag Ende / Sonnenuntergang Start
        CurvePoint(time="23:00", intensity=10),   # Sonnenuntergang Ende
        CurvePoint(time="23:01", intensity=0),    # Nacht Start
        CurvePoint(time="04:59", intensity=0),    # Nacht Ende
    ]


def get_intensity_for_time(hour: int, minute: int = 0, curve: Optional[List[CurvePoint]] = None) -> int:
    """
    Hilfsfunktion: Intensität für bestimmte Uhrzeit berechnen.

    Args:
        hour: Stunde (0-23)
        minute: Minute (0-59)
        curve: Optionale Kurve (default: Sonnenkurve)

    Returns:
        Intensität (0-100)
    """
    if curve is None:
        curve = get_default_sun_curve()

    test_time = datetime.now().replace(hour=hour, minute=minute, second=0, microsecond=0)
    return interpolate_intensity(curve, test_time)


def print_curve_preview(curve: Optional[List[CurvePoint]] = None) -> None:
    """
    Zeigt Kurven-Vorschau für 24 Stunden.

    Args:
        curve: Optionale Kurve (default: Sonnenkurve)
    """
    if curve is None:
        curve = get_default_sun_curve()

    print("\n" + "=" * 50)
    print("Sonnenkurve - 24h Vorschau")
    print("=" * 50)

    for hour in range(24):
        intensity = get_intensity_for_time(hour, 0, curve)
        bar = "█" * (intensity // 2)
        print(f"{hour:02d}:00  {intensity:3d}%  {bar}")

    print("=" * 50 + "\n")


# Test wenn direkt ausgeführt
if __name__ == "__main__":
    print_curve_preview()

    # Aktuelle Intensität
    current = interpolate_intensity(get_default_sun_curve())
    now = datetime.now()
    print(f"Aktuelle Zeit: {now.strftime('%H:%M')}")
    print(f"Aktuelle Intensität: {current}%")
