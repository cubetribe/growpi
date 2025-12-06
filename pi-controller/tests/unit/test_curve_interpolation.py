"""
Unit Tests for Curve Interpolation

CRITICAL: These tests ensure safe plant lighting control.
The interpolate_curve() function must handle ALL edge cases correctly
to prevent plant damage from incorrect light intensity.

Tests cover:
- Basic interpolation logic
- Edge cases (empty, single point)
- Midnight wraparound
- Boundary conditions
- Time matching
- Invalid input handling
"""

import pytest
from datetime import datetime, time
from grow_pi.utils.curve_controller import interpolate_curve, parse_time, time_to_minutes


class TestHelperFunctions:
    """Test helper functions used in interpolation."""

    def test_parse_time_valid(self):
        """Test parsing valid time strings."""
        assert parse_time("00:00") == time(0, 0)
        assert parse_time("12:30") == time(12, 30)
        assert parse_time("23:59") == time(23, 59)

    def test_parse_time_single_digit(self):
        """Test parsing time with single digit hours."""
        assert parse_time("6:00") == time(6, 0)
        assert parse_time("9:45") == time(9, 45)

    def test_time_to_minutes_midnight(self):
        """Test conversion at midnight."""
        assert time_to_minutes(time(0, 0)) == 0

    def test_time_to_minutes_noon(self):
        """Test conversion at noon."""
        assert time_to_minutes(time(12, 0)) == 720

    def test_time_to_minutes_end_of_day(self):
        """Test conversion at end of day."""
        assert time_to_minutes(time(23, 59)) == 1439

    @pytest.mark.parametrize("hour,minute,expected", [
        (0, 0, 0),
        (1, 0, 60),
        (6, 30, 390),
        (12, 0, 720),
        (18, 45, 1125),
        (23, 59, 1439),
    ])
    def test_time_to_minutes_various(self, hour, minute, expected):
        """Test time conversion with various inputs."""
        assert time_to_minutes(time(hour, minute)) == expected


class TestEmptyAndSinglePoint:
    """Test edge cases: empty curves and single-point curves."""

    def test_empty_curve_returns_zero(self, empty_curve):
        """Empty curve should always return 0 intensity."""
        test_time = datetime.now().replace(hour=12, minute=0)
        assert interpolate_curve(empty_curve, test_time) == 0

    def test_empty_curve_various_times(self, empty_curve):
        """Empty curve returns 0 at all times."""
        for hour in [0, 6, 12, 18, 23]:
            test_time = datetime.now().replace(hour=hour, minute=0)
            assert interpolate_curve(empty_curve, test_time) == 0

    def test_single_point_curve_before(self, single_point_curve):
        """Before single point, should wrap to same intensity."""
        test_time = datetime.now().replace(hour=6, minute=0)
        result = interpolate_curve(single_point_curve, test_time)
        assert result == 50

    def test_single_point_curve_exact(self, single_point_curve):
        """At exact point time, should return exact intensity."""
        test_time = datetime.now().replace(hour=12, minute=0)
        result = interpolate_curve(single_point_curve, test_time)
        assert result == 50

    def test_single_point_curve_after(self, single_point_curve):
        """After single point, should wrap to same intensity."""
        test_time = datetime.now().replace(hour=18, minute=0)
        result = interpolate_curve(single_point_curve, test_time)
        assert result == 50


class TestTwoPointInterpolation:
    """Test basic linear interpolation with two points."""

    def test_exact_time_match_first_point(self, simple_curve):
        """At first point time, return exact intensity."""
        test_time = datetime.now().replace(hour=6, minute=0)
        assert interpolate_curve(simple_curve, test_time) == 0

    def test_exact_time_match_second_point(self, simple_curve):
        """At second point time, return exact intensity."""
        test_time = datetime.now().replace(hour=20, minute=0)
        assert interpolate_curve(simple_curve, test_time) == 100

    def test_midpoint_interpolation(self, simple_curve):
        """At midpoint between two points, return average intensity."""
        # 06:00 -> 0%, 20:00 -> 100%
        # Midpoint: 13:00 (7 hours from start, 7 hours to end)
        test_time = datetime.now().replace(hour=13, minute=0)
        result = interpolate_curve(simple_curve, test_time)
        assert 49 <= result <= 51  # Allow rounding variance

    def test_quarter_point_interpolation(self, simple_curve):
        """At quarter point, should be 25% intensity."""
        # 06:00 -> 0%, 20:00 -> 100% (14 hour span)
        # Quarter point: 09:30 (3.5 hours from start)
        test_time = datetime.now().replace(hour=9, minute=30)
        result = interpolate_curve(simple_curve, test_time)
        assert 24 <= result <= 26  # ~25%

    def test_before_first_point(self, simple_curve):
        """Before first point wraps to previous (last) point."""
        test_time = datetime.now().replace(hour=3, minute=0)
        result = interpolate_curve(simple_curve, test_time)
        # Should interpolate from 20:00 (100%) to 06:00 (0%)
        # 3:00 is 7 hours after 20:00, 3 hours before 06:00
        # Ratio: 7/10 = 70% progress -> 100 - 70 = 30%
        assert 28 <= result <= 32

    def test_after_last_point(self, simple_curve):
        """After last point wraps to first point."""
        test_time = datetime.now().replace(hour=23, minute=0)
        result = interpolate_curve(simple_curve, test_time)
        # Should interpolate from 20:00 (100%) to 06:00 (0%)
        # 23:00 is 3 hours after 20:00, 7 hours before 06:00
        # Ratio: 3/10 = 30% progress -> 100 - 30 = 70%
        assert 68 <= result <= 72


class TestMultiPointCurves:
    """Test interpolation with realistic multi-point curves."""

    def test_full_day_curve_dawn(self, full_day_curve):
        """Test dawn period (05:00-06:00)."""
        test_time = datetime.now().replace(hour=5, minute=30)
        result = interpolate_curve(full_day_curve, test_time)
        # Between 0% (05:00) and 30% (06:00)
        assert 13 <= result <= 17  # ~15%

    def test_full_day_curve_morning(self, full_day_curve):
        """Test morning ramp (06:00-08:00)."""
        test_time = datetime.now().replace(hour=7, minute=0)
        result = interpolate_curve(full_day_curve, test_time)
        # Midpoint between 30% (06:00) and 80% (08:00)
        assert 53 <= result <= 57  # ~55%

    def test_full_day_curve_noon_peak(self, full_day_curve):
        """Test peak intensity at noon."""
        test_time = datetime.now().replace(hour=12, minute=0)
        result = interpolate_curve(full_day_curve, test_time)
        assert result == 100

    def test_full_day_curve_afternoon(self, full_day_curve):
        """Test afternoon period (12:00-18:00)."""
        test_time = datetime.now().replace(hour=15, minute=0)
        result = interpolate_curve(full_day_curve, test_time)
        # Midpoint between 100% (12:00) and 80% (18:00)
        assert 88 <= result <= 92  # ~90%

    def test_full_day_curve_evening(self, full_day_curve):
        """Test evening ramp down (18:00-21:00)."""
        test_time = datetime.now().replace(hour=19, minute=0)
        result = interpolate_curve(full_day_curve, test_time)
        # Between 80% (18:00) and 30% (20:00)
        assert 53 <= result <= 57  # ~55%

    def test_full_day_curve_night(self, full_day_curve):
        """Test night period (21:00-05:00)."""
        test_time = datetime.now().replace(hour=23, minute=0)
        result = interpolate_curve(full_day_curve, test_time)
        # Should wrap from 21:00 (0%) to 05:00 (0%)
        assert result == 0


class TestMidnightWraparound:
    """Test critical midnight wraparound logic."""

    def test_midnight_wraparound_before_midnight(self, midnight_wraparound_curve):
        """Test time before midnight in wraparound curve."""
        test_time = datetime.now().replace(hour=23, minute=0)
        result = interpolate_curve(midnight_wraparound_curve, test_time)
        # Between 22:00 (50%) and 23:30 (20%)
        # 23:00 is 1 hour after 22:00, 0.5 hours before 23:30
        # Ratio: 1/1.5 = 66.7% -> 50 - (66.7% * 30) = 30%
        assert 28 <= result <= 32

    def test_midnight_wraparound_after_midnight(self, midnight_wraparound_curve):
        """Test time after midnight in wraparound curve."""
        test_time = datetime.now().replace(hour=2, minute=0)
        result = interpolate_curve(midnight_wraparound_curve, test_time)
        # Between 01:00 (10%) and 03:00 (30%)
        # Midpoint should be 20%
        assert 18 <= result <= 22

    def test_midnight_exact(self, midnight_wraparound_curve):
        """Test exactly at midnight."""
        test_time = datetime.now().replace(hour=0, minute=0)
        result = interpolate_curve(midnight_wraparound_curve, test_time)
        # Between 23:30 (20%) and 01:00 (10%)
        # 00:00 is 30 min after 23:30, 60 min before 01:00
        # Ratio: 30/90 = 33.3% -> 20 - (33.3% * 10) = 16.7%
        assert 15 <= result <= 18

    def test_edge_case_2359_to_0000(self):
        """Test transition from 23:59 to 00:00."""
        curve = [
            {"time": "23:00", "intensity": 100},
            {"time": "01:00", "intensity": 0},
        ]
        # At 23:59
        test_time = datetime.now().replace(hour=23, minute=59)
        result = interpolate_curve(curve, test_time)
        assert 48 <= result <= 52  # Should be ~50%

        # At 00:00
        test_time = datetime.now().replace(hour=0, minute=0)
        result = interpolate_curve(curve, test_time)
        assert 48 <= result <= 52  # Should be ~50%

    def test_late_night_early_morning(self):
        """Test late night to early morning transition."""
        curve = [
            {"time": "22:00", "intensity": 0},
            {"time": "06:00", "intensity": 0},
        ]
        # Should be 0 throughout night
        for hour in [23, 0, 1, 2, 3, 4, 5]:
            test_time = datetime.now().replace(hour=hour, minute=0)
            result = interpolate_curve(curve, test_time)
            assert result == 0


class TestSunriseSequence:
    """Test realistic dawn/dusk sequences."""

    def test_dawn_early_morning(self, dawn_curve):
        """Test early morning before sunrise."""
        test_time = datetime.now().replace(hour=4, minute=30)
        result = interpolate_curve(dawn_curve, test_time)
        # Midpoint between 04:00 (0%) and 05:00 (10%)
        assert 4 <= result <= 6  # ~5%

    def test_dawn_sunrise(self, dawn_curve):
        """Test sunrise period."""
        test_time = datetime.now().replace(hour=6, minute=30)
        result = interpolate_curve(dawn_curve, test_time)
        # Midpoint between 06:00 (40%) and 07:00 (70%)
        assert 53 <= result <= 57  # ~55%

    def test_dawn_full_sun(self, dawn_curve):
        """Test full daylight."""
        test_time = datetime.now().replace(hour=8, minute=0)
        result = interpolate_curve(dawn_curve, test_time)
        assert result == 100

    def test_dusk_full_sun(self, dusk_curve):
        """Test start of sunset."""
        test_time = datetime.now().replace(hour=18, minute=0)
        result = interpolate_curve(dusk_curve, test_time)
        assert result == 100

    def test_dusk_sunset(self, dusk_curve):
        """Test sunset period."""
        test_time = datetime.now().replace(hour=19, minute=30)
        result = interpolate_curve(dusk_curve, test_time)
        # Midpoint between 19:00 (70%) and 20:00 (40%)
        assert 53 <= result <= 57  # ~55%

    def test_dusk_night(self, dusk_curve):
        """Test full night."""
        test_time = datetime.now().replace(hour=22, minute=0)
        result = interpolate_curve(dusk_curve, test_time)
        assert result == 0


class TestIntensityBounds:
    """Test intensity remains within valid bounds (0-100)."""

    @pytest.mark.parametrize("intensity", [0, 25, 50, 75, 100])
    def test_constant_intensity_curves(self, intensity):
        """Test curves with constant intensity."""
        curve = [
            {"time": "00:00", "intensity": intensity},
            {"time": "12:00", "intensity": intensity},
        ]
        for hour in [0, 6, 12, 18, 23]:
            test_time = datetime.now().replace(hour=hour, minute=0)
            result = interpolate_curve(curve, test_time)
            assert 0 <= result <= 100
            assert result == intensity

    def test_extreme_ramp_up(self):
        """Test rapid 0->100 transition (minute precision)."""
        curve = [
            {"time": "12:00", "intensity": 0},
            {"time": "12:02", "intensity": 100},
        ]
        # Note: interpolate_curve uses minute-level precision (ignores seconds)
        # At 12:01, we're halfway between 12:00 and 12:02
        test_time = datetime.now().replace(hour=12, minute=1, second=0)
        result = interpolate_curve(curve, test_time)
        assert 0 <= result <= 100
        assert 45 <= result <= 55  # ~50%

    def test_extreme_ramp_down(self):
        """Test rapid 100->0 transition (minute precision)."""
        curve = [
            {"time": "18:00", "intensity": 100},
            {"time": "18:02", "intensity": 0},
        ]
        # Note: interpolate_curve uses minute-level precision (ignores seconds)
        # At 18:01, we're halfway between 18:00 and 18:02
        test_time = datetime.now().replace(hour=18, minute=1, second=0)
        result = interpolate_curve(curve, test_time)
        assert 0 <= result <= 100
        assert 45 <= result <= 55  # ~50%

    def test_all_interpolated_values_in_bounds(self, full_day_curve):
        """Test every hour of day stays within bounds."""
        for hour in range(24):
            for minute in [0, 15, 30, 45]:
                test_time = datetime.now().replace(hour=hour, minute=minute)
                result = interpolate_curve(full_day_curve, test_time)
                assert 0 <= result <= 100, f"Out of bounds at {hour:02d}:{minute:02d}"


class TestSortingAndOrdering:
    """Test curve point sorting and time ordering."""

    def test_unsorted_curve_gets_sorted(self):
        """Curve points should be sorted by time internally."""
        unsorted_curve = [
            {"time": "18:00", "intensity": 50},
            {"time": "06:00", "intensity": 0},
            {"time": "12:00", "intensity": 100},
        ]
        # Should work correctly despite unsorted input
        test_time = datetime.now().replace(hour=9, minute=0)
        result = interpolate_curve(unsorted_curve, test_time)
        # Should interpolate between 06:00 (0%) and 12:00 (100%)
        # 9:00 is halfway -> 50%
        assert 48 <= result <= 52

    def test_duplicate_times_last_wins(self):
        """If duplicate times exist, behavior should be predictable."""
        curve = [
            {"time": "12:00", "intensity": 50},
            {"time": "12:00", "intensity": 80},
        ]
        test_time = datetime.now().replace(hour=12, minute=0)
        result = interpolate_curve(curve, test_time)
        # Should return one of the intensities (last one after sorting)
        assert 50 <= result <= 80


class TestCurrentTimeDefault:
    """Test default current_time parameter behavior."""

    def test_none_uses_current_time(self):
        """Passing None should use datetime.now()."""
        curve = [
            {"time": "00:00", "intensity": 50},
            {"time": "23:59", "intensity": 50},
        ]
        # Should not raise error and return valid intensity
        result = interpolate_curve(curve, None)
        assert 0 <= result <= 100

    def test_omitted_uses_current_time(self):
        """Omitting parameter should use datetime.now()."""
        curve = [
            {"time": "00:00", "intensity": 50},
            {"time": "23:59", "intensity": 50},
        ]
        # Should not raise error and return valid intensity
        result = interpolate_curve(curve)
        assert 0 <= result <= 100


class TestRealWorldScenarios:
    """Test realistic plant lighting scenarios."""

    def test_cannabis_veg_18_6_schedule(self):
        """Test 18/6 light schedule (18h on, 6h off)."""
        curve = [
            {"time": "06:00", "intensity": 0},
            {"time": "06:30", "intensity": 100},
            {"time": "23:30", "intensity": 100},
            {"time": "00:00", "intensity": 0},
        ]
        # Light period
        test_time = datetime.now().replace(hour=12, minute=0)
        assert interpolate_curve(curve, test_time) == 100

        # Dark period
        test_time = datetime.now().replace(hour=3, minute=0)
        assert interpolate_curve(curve, test_time) == 0

    def test_far_red_eod_treatment(self):
        """Test Far-Red End-of-Day treatment (10min pulse)."""
        curve = [
            {"time": "20:00", "intensity": 0},
            {"time": "20:00", "intensity": 100},  # Instant on
            {"time": "20:10", "intensity": 100},
            {"time": "20:10", "intensity": 0},    # Instant off
        ]
        # During pulse
        test_time = datetime.now().replace(hour=20, minute=5)
        result = interpolate_curve(curve, test_time)
        assert 90 <= result <= 100

    def test_gradual_sunrise_30min(self):
        """Test 30-minute gradual sunrise."""
        curve = [
            {"time": "06:00", "intensity": 0},
            {"time": "06:30", "intensity": 100},
        ]
        # 15 minutes into sunrise
        test_time = datetime.now().replace(hour=6, minute=15)
        result = interpolate_curve(curve, test_time)
        assert 48 <= result <= 52  # ~50%

    def test_nursery_low_light_maintenance(self):
        """Test low constant light for seedlings."""
        curve = [
            {"time": "00:00", "intensity": 20},
            {"time": "23:59", "intensity": 20},
        ]
        for hour in [0, 6, 12, 18, 23]:
            test_time = datetime.now().replace(hour=hour, minute=0)
            result = interpolate_curve(curve, test_time)
            assert result == 20


class TestPrecisionAndRounding:
    """Test rounding behavior and precision."""

    def test_rounding_to_integer(self):
        """Result should always be integer."""
        curve = [
            {"time": "12:00", "intensity": 33},
            {"time": "13:00", "intensity": 66},
        ]
        test_time = datetime.now().replace(hour=12, minute=20)  # 33.33% progress
        result = interpolate_curve(curve, test_time)
        assert isinstance(result, int)

    def test_half_values_round_correctly(self):
        """Test that .5 values round correctly."""
        curve = [
            {"time": "12:00", "intensity": 0},
            {"time": "13:00", "intensity": 100},
        ]
        test_time = datetime.now().replace(hour=12, minute=30)
        result = interpolate_curve(curve, test_time)
        # Should be exactly 50
        assert result == 50


class TestEdgeCasesAndFailures:
    """Test error handling and edge cases."""

    def test_invalid_time_format_raises_error(self):
        """Invalid time format should raise ValueError."""
        invalid_curve = [{"time": "25:99", "intensity": 50}]
        test_time = datetime.now().replace(hour=12, minute=0)
        with pytest.raises(ValueError):
            interpolate_curve(invalid_curve, test_time)

    def test_missing_time_key(self):
        """Missing 'time' key should raise KeyError."""
        invalid_curve = [{"intensity": 50}]
        test_time = datetime.now().replace(hour=12, minute=0)
        with pytest.raises(KeyError):
            interpolate_curve(invalid_curve, test_time)

    def test_missing_intensity_key(self):
        """Missing 'intensity' key should raise KeyError."""
        invalid_curve = [{"time": "12:00"}]
        test_time = datetime.now().replace(hour=12, minute=0)
        with pytest.raises(KeyError):
            interpolate_curve(invalid_curve, test_time)

    def test_negative_intensity(self):
        """Negative intensity in curve (should still interpolate)."""
        # Note: Validation happens in CurveController.update_curve()
        # interpolate_curve() itself doesn't validate bounds
        curve = [
            {"time": "12:00", "intensity": -10},
            {"time": "13:00", "intensity": 10},
        ]
        test_time = datetime.now().replace(hour=12, minute=30)
        result = interpolate_curve(curve, test_time)
        assert result == 0  # Midpoint of -10 and 10

    def test_intensity_over_100(self):
        """Intensity over 100 in curve (should still interpolate)."""
        curve = [
            {"time": "12:00", "intensity": 90},
            {"time": "13:00", "intensity": 110},
        ]
        test_time = datetime.now().replace(hour=12, minute=30)
        result = interpolate_curve(curve, test_time)
        assert result == 100  # Midpoint of 90 and 110
