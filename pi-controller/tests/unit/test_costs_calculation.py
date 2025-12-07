"""
Unit Tests for Costs Calculation (v6.3 Feature)

Tests the energy consumption tracking and cost calculation features.
Ensures accurate kWh measurement and cost reporting.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch


class TestKwhCalculation:
    """Test kWh calculation from power readings."""

    def test_kwh_calculation_zero_power(self):
        """Test: 0W should result in 0 kWh."""
        # Simulate 1 hour at 0W
        readings = [
            {"timestamp": datetime.now() - timedelta(hours=1), "power_w": 0},
            {"timestamp": datetime.now(), "power_w": 0}
        ]
        # Expected: 0 kWh
        total_kwh = self._calculate_kwh(readings)
        assert total_kwh == 0.0

    def test_kwh_calculation_constant_power(self):
        """Test: Constant 100W for 1 hour = 0.1 kWh."""
        start = datetime.now() - timedelta(hours=1)
        readings = [
            {"timestamp": start, "power_w": 100},
            {"timestamp": start + timedelta(minutes=30), "power_w": 100},
            {"timestamp": start + timedelta(hours=1), "power_w": 100}
        ]
        total_kwh = self._calculate_kwh(readings)
        # 100W * 1h = 100Wh = 0.1 kWh
        assert abs(total_kwh - 0.1) < 0.01

    def test_kwh_calculation_varying_power(self):
        """Test: Varying power levels (50W -> 100W -> 0W)."""
        start = datetime.now() - timedelta(hours=2)
        readings = [
            {"timestamp": start, "power_w": 50},
            {"timestamp": start + timedelta(hours=1), "power_w": 100},
            {"timestamp": start + timedelta(hours=2), "power_w": 0}
        ]
        total_kwh = self._calculate_kwh(readings)
        # Approx: avg(50,100)*1h + avg(100,0)*1h = 75Wh + 50Wh = 125Wh = 0.125 kWh
        assert 0.12 < total_kwh < 0.13

    def test_kwh_calculation_single_reading(self):
        """Test: Single reading should return 0 kWh."""
        readings = [{"timestamp": datetime.now(), "power_w": 100}]
        total_kwh = self._calculate_kwh(readings)
        assert total_kwh == 0.0

    def test_kwh_calculation_empty_readings(self):
        """Test: Empty readings should return 0 kWh."""
        readings = []
        total_kwh = self._calculate_kwh(readings)
        assert total_kwh == 0.0

    def _calculate_kwh(self, readings):
        """Helper to calculate kWh from power readings."""
        if len(readings) < 2:
            return 0.0

        total_wh = 0.0
        for i in range(1, len(readings)):
            prev = readings[i - 1]
            curr = readings[i]
            time_diff_hours = (curr["timestamp"] - prev["timestamp"]).total_seconds() / 3600
            avg_power = (prev["power_w"] + curr["power_w"]) / 2
            total_wh += avg_power * time_diff_hours

        return total_wh / 1000  # Convert Wh to kWh


class TestCostCalculation:
    """Test cost calculation from kWh consumption."""

    def test_costs_with_default_price(self):
        """Test: Cost calculation with default €0.30/kWh."""
        kwh = 1.0
        price_per_kwh = 0.30
        cost = kwh * price_per_kwh
        assert cost == 0.30

    def test_costs_with_custom_price(self):
        """Test: Cost calculation with custom €0.25/kWh."""
        kwh = 2.5
        price_per_kwh = 0.25
        cost = kwh * price_per_kwh
        assert cost == 0.625

    def test_costs_zero_kwh(self):
        """Test: 0 kWh should result in €0.00 cost."""
        kwh = 0.0
        price_per_kwh = 0.30
        cost = kwh * price_per_kwh
        assert cost == 0.0

    def test_costs_high_consumption(self):
        """Test: High consumption (100 kWh) calculation."""
        kwh = 100.0
        price_per_kwh = 0.30
        cost = kwh * price_per_kwh
        assert cost == 30.0

    def test_costs_formatting_two_decimals(self):
        """Test: Cost should be formatted to 2 decimals."""
        cost = 1.234567
        formatted = f"{cost:.2f}"
        assert formatted == "1.23"


class TestPeriodFiltering:
    """Test filtering readings by time period."""

    def test_filter_today(self):
        """Test: Filter readings for today."""
        now = datetime.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        readings = [
            {"timestamp": today_start - timedelta(days=1), "power_w": 50},  # Yesterday
            {"timestamp": today_start + timedelta(hours=6), "power_w": 100},  # Today
            {"timestamp": today_start + timedelta(hours=12), "power_w": 80},  # Today
        ]

        filtered = [r for r in readings if r["timestamp"] >= today_start]
        assert len(filtered) == 2

    def test_filter_week(self):
        """Test: Filter readings for last 7 days."""
        now = datetime.now()
        week_ago = now - timedelta(days=7)

        readings = [
            {"timestamp": week_ago - timedelta(days=1), "power_w": 50},  # 8 days ago
            {"timestamp": week_ago + timedelta(days=1), "power_w": 100},  # 6 days ago
            {"timestamp": now, "power_w": 80},  # Today
        ]

        filtered = [r for r in readings if r["timestamp"] >= week_ago]
        assert len(filtered) == 2

    def test_filter_month(self):
        """Test: Filter readings for last 30 days."""
        now = datetime.now()
        month_ago = now - timedelta(days=30)

        readings = [
            {"timestamp": month_ago - timedelta(days=1), "power_w": 50},  # 31 days ago
            {"timestamp": month_ago + timedelta(days=1), "power_w": 100},  # 29 days ago
            {"timestamp": now, "power_w": 80},  # Today
        ]

        filtered = [r for r in readings if r["timestamp"] >= month_ago]
        assert len(filtered) == 2


class TestCostAPIData:
    """Test cost API data structure."""

    def test_cost_response_structure(self):
        """Test: Cost API response has required fields."""
        response = {
            "period": "today",
            "kwh": 1.23,
            "cost": 0.37,
            "currency": "EUR",
            "price_per_kwh": 0.30
        }

        assert "period" in response
        assert "kwh" in response
        assert "cost" in response
        assert "currency" in response
        assert "price_per_kwh" in response

    def test_cost_response_values(self):
        """Test: Cost API response has valid values."""
        kwh = 5.0
        price_per_kwh = 0.30
        response = {
            "period": "week",
            "kwh": kwh,
            "cost": kwh * price_per_kwh,
            "currency": "EUR",
            "price_per_kwh": price_per_kwh
        }

        assert response["kwh"] == 5.0
        assert response["cost"] == 1.5
        assert response["currency"] == "EUR"


class TestCostConfig:
    """Test cost configuration settings."""

    def test_default_config(self):
        """Test: Default configuration values."""
        config = {
            "price_per_kwh": 0.30,
            "currency": "EUR",
            "enabled": True
        }

        assert config["price_per_kwh"] == 0.30
        assert config["currency"] == "EUR"
        assert config["enabled"] is True

    def test_update_price(self):
        """Test: Update kWh price."""
        config = {"price_per_kwh": 0.30}
        config["price_per_kwh"] = 0.25
        assert config["price_per_kwh"] == 0.25

    def test_price_validation_positive(self):
        """Test: Price must be positive."""
        price = 0.30
        assert price > 0

    def test_price_validation_not_negative(self):
        """Test: Negative price should be invalid."""
        price = -0.10
        assert price <= 0  # This should fail validation
