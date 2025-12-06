#!/usr/bin/env python3
"""
Costs Blueprint - Electricity Costs API
Provides endpoints for power consumption cost calculation.

Endpoints:
    GET  /api/costs        - Get costs summary for all devices (period-based)
    GET  /api/costs/config - Get kWh price configuration
    POST /api/costs/config - Update kWh price configuration
"""

from flask import Blueprint, jsonify, request
import logging
import os
import json
from datetime import datetime, timedelta

costs_bp = Blueprint('costs', __name__)
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def _get_config_path():
    """Get absolute path to room_config.json"""
    config_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..', '..', 'config', 'room_config.json'
    )
    return os.path.abspath(config_file)


def _load_costs_config():
    """Load costs config from room_config.json"""
    config_file = _get_config_path()
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)
                devices = data.get('devices', {})
                return {
                    'kwh_price': data.get('costs', {}).get('kwh_price', 0.30),
                    'currency': data.get('costs', {}).get('currency', 'EUR'),
                    'devices': devices
                }
        else:
            logger.warning(f"Costs config file not found at: {config_file}")
    except Exception as e:
        logger.error(f"Error loading costs config from {config_file}: {e}")
    return {'kwh_price': 0.30, 'currency': 'EUR', 'devices': {}}


def _save_costs_config(kwh_price: float):
    """Save kWh price to config"""
    config_file = _get_config_path()
    try:
        data = {}
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                data = json.load(f)

        if 'costs' not in data:
            data['costs'] = {}
        data['costs']['kwh_price'] = kwh_price

        with open(config_file, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving costs config: {e}")
        return False


def create_response(success: bool, data: dict = None, error: str = None) -> dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


# ============================================================================
# API Routes
# ============================================================================

@costs_bp.route('/api/costs', methods=['GET'])
def get_costs():
    """Get power costs summary for all devices

    Query Parameters:
        period: today, week, month, year, this_month, this_year, custom
        from: Start date (YYYY-MM-DD) for custom range
        to: End date (YYYY-MM-DD) for custom range
    """
    try:
        # Get time range from query params
        period = request.args.get('period', 'today')
        date_from = request.args.get('from')
        date_to = request.args.get('to')

        # Calculate time range
        now = datetime.now()
        start_time = None
        end_time = now
        period_label = period

        if date_from and date_to:
            # Custom date range
            try:
                start_time = datetime.strptime(date_from, '%Y-%m-%d')
                end_time = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                period_label = f"{date_from} bis {date_to}"
            except ValueError:
                return jsonify(create_response(False, error="Invalid date format. Use YYYY-MM-DD")), 400
        elif period == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == 'week':
            start_time = now - timedelta(days=7)
        elif period == 'month':
            start_time = now - timedelta(days=30)
        elif period == 'this_month':
            # First day of current month
            start_time = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            period_label = f"Dieser Monat ({start_time.strftime('%B %Y')})"
        elif period == 'this_year':
            # First day of current year
            start_time = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            period_label = f"Dieses Jahr ({now.year})"
        elif period == 'year':
            start_time = now - timedelta(days=365)
        else:
            start_time = now - timedelta(days=1)

        # Calculate hours for database query
        hours = int((end_time - start_time).total_seconds() / 3600) + 1

        # Load config
        config = _load_costs_config()
        kwh_price = config['kwh_price']
        device_names = config['devices']

        # Get plug logs from database
        # Import here to avoid circular dependency
        try:
            from grow_pi.database import get_database
            db = get_database()
            logs = db.get_plug_logs(hours=int(hours), limit=100000)
        except Exception as e:
            logger.warning(f"Database not available: {e}")
            logs = []

        # Calculate costs per device
        # Group logs by device_id
        device_power = {}  # device_id -> list of power readings
        for log in logs:
            device_id = log.device_id
            if device_id not in device_power:
                device_power[device_id] = []
            device_power[device_id].append(log.power or 0)

        # Calculate kWh and costs for each device
        # Assuming 60 second intervals between readings
        interval_hours = 60 / 3600  # 60 seconds in hours
        devices = []
        total_kwh = 0
        total_cost = 0

        for device_id, power_readings in device_power.items():
            # Sum up energy consumption
            # kWh = sum(Watt * hours)
            kwh = sum(p * interval_hours for p in power_readings) / 1000
            cost = kwh * kwh_price

            total_kwh += kwh
            total_cost += cost

            # Get current power (latest reading)
            current_power = power_readings[0] if power_readings else 0

            devices.append({
                'device_id': device_id,
                'name': device_names.get(device_id, device_id[:8] + '...'),
                'current_power': current_power,
                'kwh': round(kwh, 4),
                'cost': round(cost, 4),
                'readings_count': len(power_readings)
            })

        # Sort by cost (highest first)
        devices.sort(key=lambda x: x['cost'], reverse=True)

        return jsonify(create_response(True, {
            'period': period,
            'period_label': period_label,
            'date_from': start_time.strftime('%Y-%m-%d') if start_time else None,
            'date_to': end_time.strftime('%Y-%m-%d'),
            'kwh_price': kwh_price,
            'currency': config['currency'],
            'devices': devices,
            'total_kwh': round(total_kwh, 4),
            'total_cost': round(total_cost, 4),
            'timestamp': now.isoformat()
        }))

    except Exception as e:
        logger.error(f"Error in get_costs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@costs_bp.route('/api/costs/config', methods=['GET'])
def get_costs_config():
    """Get costs configuration (kWh price)"""
    try:
        config = _load_costs_config()
        return jsonify(create_response(True, {
            'kwh_price': config['kwh_price'],
            'currency': config['currency'],
            'devices': config['devices']
        }))
    except Exception as e:
        logger.error(f"Error in get_costs_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@costs_bp.route('/api/costs/config', methods=['POST'])
def update_costs_config():
    """Update kWh price"""
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        kwh_price = data.get('kwh_price')

        if kwh_price is None:
            return jsonify(create_response(False, error="kwh_price is required")), 400

        kwh_price = float(kwh_price)
        if kwh_price < 0:
            return jsonify(create_response(False, error="kwh_price must be positive")), 400

        if _save_costs_config(kwh_price):
            logger.info(f"kWh price updated to {kwh_price}")
            return jsonify(create_response(True, {
                'kwh_price': kwh_price,
                'message': 'Configuration saved'
            }))
        else:
            return jsonify(create_response(False, error="Failed to save configuration")), 500

    except Exception as e:
        logger.error(f"Error in update_costs_config: {e}")
        return jsonify(create_response(False, error=str(e))), 500
