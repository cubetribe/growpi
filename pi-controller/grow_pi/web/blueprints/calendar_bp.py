#!/usr/bin/env python3
"""
Calendar Blueprint - Grow Calendar API
Provides endpoints for grow cycle tracking, phase management, and daily logs.

Endpoints:
    GET  /api/calendar/grows               - List all grows
    POST /api/calendar/grows               - Create new grow
    GET  /api/calendar/grows/<id>          - Get grow details
    PUT  /api/calendar/grows/<id>          - Update grow
    DELETE /api/calendar/grows/<id>        - Delete grow
    POST /api/calendar/grows/<id>/phase    - Change grow phase
    GET  /api/calendar/grows/<id>/timeline - Get phase timeline
    GET  /api/calendar/grows/<id>/logs     - Get daily logs for grow
    POST /api/calendar/logs                - Create daily log
    GET  /api/calendar/logs/<id>           - Get specific log
    PUT  /api/calendar/logs/<id>           - Update daily log
    DELETE /api/calendar/logs/<id>         - Delete daily log
    GET  /api/calendar/month/<YYYY-MM>     - Get calendar month view
    GET  /api/calendar/milestones          - Get all milestones (optional filter: ?phase=flowering)
    GET  /api/calendar/milestones/for-date - Get milestones for grow + date
    POST /api/calendar/milestones          - Create custom milestone
    PUT  /api/calendar/milestones/<id>     - Update milestone (custom only)
    PATCH /api/calendar/milestones/<id>/toggle - Enable/Disable milestone
    DELETE /api/calendar/milestones/<id>   - Delete milestone (custom only)
"""

from flask import Blueprint, jsonify, request
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

calendar_bp = Blueprint('calendar', __name__)
logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================

def get_db_connection():
    """Get database connection from grow_pi.database"""
    try:
        from grow_pi.database import get_database
        return get_database()
    except Exception as e:
        logger.error(f"Failed to get database connection: {e}")
        return None


def create_response(success: bool, data: dict = None, error: str = None) -> dict:
    """Create standardized API response"""
    response = {"success": success}
    if data:
        response.update(data)
    if error:
        response["error"] = error
    return response


def generate_uuid() -> str:
    """Generate UUID for database records"""
    return str(uuid.uuid4())


def validate_date(date_string: str) -> bool:
    """Validate ISO date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_string, '%Y-%m-%d')
        return True
    except ValueError:
        return False


def validate_datetime(dt_string: str) -> bool:
    """Validate ISO datetime format"""
    try:
        datetime.fromisoformat(dt_string)
        return True
    except ValueError:
        return False


def calculate_duration_days(start: str, end: str) -> int:
    """Calculate duration in days between two datetimes"""
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
        return (end_dt - start_dt).days
    except:
        return 0


# ============================================================================
# API Routes: Grows Management
# ============================================================================

@calendar_bp.route('/api/calendar/grows', methods=['GET'])
def get_grows():
    """Get all grows (active and completed)

    Query Parameters:
        active_only: true/false (default: false)
        limit: max results (default: 100)
    """
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        active_only = request.args.get('active_only', 'false').lower() == 'true'
        limit = int(request.args.get('limit', 100))

        with db.get_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                query = """
                    SELECT id, name, strain, start_date, current_phase,
                           phase_started_at, notes, is_active, created_at, updated_at
                    FROM grows
                    WHERE is_active = 1
                    ORDER BY start_date DESC
                    LIMIT ?
                """
            else:
                query = """
                    SELECT id, name, strain, start_date, current_phase,
                           phase_started_at, notes, is_active, created_at, updated_at
                    FROM grows
                    ORDER BY is_active DESC, start_date DESC
                    LIMIT ?
                """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            grows = []
            for row in rows:
                # Calculate phase_day (current day of phase)
                phase_day = None
                if row[5]:  # phase_started_at
                    try:
                        phase_start = datetime.fromisoformat(row[5])
                        phase_day = (datetime.now() - phase_start).days + 1
                    except Exception as e:
                        logger.warning(f"Failed to calculate phase_day for grow {row[0]}: {e}")

                grows.append({
                    'id': row[0],
                    'name': row[1],
                    'strain': row[2],
                    'start_date': row[3],
                    'current_phase': row[4],
                    'phase_started_at': row[5],
                    'phase_day': phase_day,  # NEW: Current day of phase
                    'notes': row[6],
                    'is_active': bool(row[7]),
                    'created_at': row[8],
                    'updated_at': row[9]
                })

        return jsonify(create_response(True, {'grows': grows, 'count': len(grows)}))

    except Exception as e:
        logger.error(f"Error in get_grows: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/grows', methods=['POST'])
def create_grow():
    """Create new grow cycle

    Body:
        name: string (required)
        strain: string (optional)
        start_date: YYYY-MM-DD (required)
        notes: string (optional)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()

        # Validate required fields
        name = data.get('name')
        start_date = data.get('start_date')

        if not name or not start_date:
            return jsonify(create_response(False, error="name and start_date are required")), 400

        if not validate_date(start_date):
            return jsonify(create_response(False, error="Invalid date format. Use YYYY-MM-DD")), 400

        # Optional fields
        strain = data.get('strain', '')
        notes = data.get('notes', '')

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        # Deactivate other grows if this is meant to be active
        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Deactivate all other grows
            cursor.execute("UPDATE grows SET is_active = 0")

            # Create new grow
            grow_id = generate_uuid()
            now = datetime.now().isoformat()
            phase_started_at = datetime.strptime(start_date, '%Y-%m-%d').isoformat()

            cursor.execute("""
                INSERT INTO grows (id, name, strain, start_date, current_phase,
                                  phase_started_at, notes, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, 'seedling', ?, ?, 1, ?, ?)
            """, (grow_id, name, strain, start_date, phase_started_at, notes, now, now))

            # Create initial phase event
            phase_event_id = generate_uuid()
            cursor.execute("""
                INSERT INTO phase_events (id, grow_id, phase, started_at, created_at)
                VALUES (?, ?, 'seedling', ?, ?)
            """, (phase_event_id, grow_id, phase_started_at, now))

            conn.commit()

        logger.info(f"Created new grow: {grow_id} ({name})")

        return jsonify(create_response(True, {
            'grow_id': grow_id,
            'message': 'Grow created successfully'
        })), 201

    except Exception as e:
        logger.error(f"Error in create_grow: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/grows/<grow_id>', methods=['GET'])
def get_grow(grow_id: str):
    """Get specific grow details"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, strain, start_date, current_phase,
                       phase_started_at, notes, is_active, created_at, updated_at
                FROM grows
                WHERE id = ?
            """, (grow_id,))

            row = cursor.fetchone()
            if not row:
                return jsonify(create_response(False, error="Grow not found")), 404

            # Calculate phase_day (current day of phase)
            phase_day = None
            if row[5]:  # phase_started_at
                try:
                    phase_start = datetime.fromisoformat(row[5])
                    phase_day = (datetime.now() - phase_start).days + 1
                except Exception as e:
                    logger.warning(f"Failed to calculate phase_day for grow {row[0]}: {e}")

            grow = {
                'id': row[0],
                'name': row[1],
                'strain': row[2],
                'start_date': row[3],
                'current_phase': row[4],
                'phase_started_at': row[5],
                'phase_day': phase_day,  # NEW: Current day of phase
                'notes': row[6],
                'is_active': bool(row[7]),
                'created_at': row[8],
                'updated_at': row[9]
            }

        return jsonify(create_response(True, {'grow': grow}))

    except Exception as e:
        logger.error(f"Error in get_grow: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/grows/<grow_id>', methods=['PUT'])
def update_grow(grow_id: str):
    """Update grow details

    Body:
        name: string (optional)
        strain: string (optional)
        notes: string (optional)
        is_active: boolean (optional)
        start_date: YYYY-MM-DD (optional) - cannot be in future
        phase_started_at: ISO datetime (optional) - cannot be in future, updates corresponding phase_event
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        # Build dynamic UPDATE query
        updates = []
        params = []

        if 'name' in data:
            updates.append("name = ?")
            params.append(data['name'])
        if 'strain' in data:
            updates.append("strain = ?")
            params.append(data['strain'])
        if 'notes' in data:
            updates.append("notes = ?")
            params.append(data['notes'])
        if 'is_active' in data:
            updates.append("is_active = ?")
            params.append(1 if data['is_active'] else 0)

        # NEW: Allow editing start_date
        if 'start_date' in data:
            if not validate_date(data['start_date']):
                return jsonify(create_response(False, error="Invalid start_date format. Use YYYY-MM-DD")), 400
            # Validate date is not in the future
            try:
                start_dt = datetime.strptime(data['start_date'], '%Y-%m-%d')
                if start_dt.date() > datetime.now().date():
                    return jsonify(create_response(False, error="start_date cannot be in the future")), 400
            except Exception as e:
                return jsonify(create_response(False, error=f"Invalid start_date: {str(e)}")), 400
            updates.append("start_date = ?")
            params.append(data['start_date'])

        # NEW: Allow editing phase_started_at
        if 'phase_started_at' in data:
            if not validate_datetime(data['phase_started_at']):
                return jsonify(create_response(False, error="Invalid phase_started_at format. Use ISO datetime")), 400
            # Validate datetime is not in the future
            try:
                phase_dt = datetime.fromisoformat(data['phase_started_at'])
                if phase_dt > datetime.now():
                    return jsonify(create_response(False, error="phase_started_at cannot be in the future")), 400
            except Exception as e:
                return jsonify(create_response(False, error=f"Invalid phase_started_at: {str(e)}")), 400
            updates.append("phase_started_at = ?")
            params.append(data['phase_started_at'])

        if not updates:
            return jsonify(create_response(False, error="No fields to update")), 400

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(grow_id)

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # If activating this grow, deactivate others
            if 'is_active' in data and data['is_active']:
                cursor.execute("UPDATE grows SET is_active = 0 WHERE id != ?", (grow_id,))

            # If phase_started_at is being updated, also update the corresponding phase_event
            if 'phase_started_at' in data:
                # Get current phase
                cursor.execute("SELECT current_phase FROM grows WHERE id = ?", (grow_id,))
                phase_row = cursor.fetchone()
                if phase_row:
                    current_phase = phase_row[0]
                    # Update the most recent phase_event for this phase
                    cursor.execute("""
                        UPDATE phase_events
                        SET started_at = ?, updated_at = ?
                        WHERE grow_id = ? AND phase = ? AND ended_at IS NULL
                    """, (data['phase_started_at'], datetime.now().isoformat(), grow_id, current_phase))

            query = f"UPDATE grows SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            if cursor.rowcount == 0:
                return jsonify(create_response(False, error="Grow not found")), 404

            conn.commit()

        logger.info(f"Updated grow: {grow_id}")
        return jsonify(create_response(True, {'message': 'Grow updated successfully'}))

    except Exception as e:
        logger.error(f"Error in update_grow: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/grows/<grow_id>', methods=['DELETE'])
def delete_grow(grow_id: str):
    """Delete grow (CASCADE deletes phase_events and daily_logs)"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM grows WHERE id = ?", (grow_id,))

            if cursor.rowcount == 0:
                return jsonify(create_response(False, error="Grow not found")), 404

            conn.commit()

        logger.info(f"Deleted grow: {grow_id}")
        return jsonify(create_response(True, {'message': 'Grow deleted successfully'}))

    except Exception as e:
        logger.error(f"Error in delete_grow: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# API Routes: Phase Management
# ============================================================================

@calendar_bp.route('/api/calendar/grows/<grow_id>/phase', methods=['POST'])
def change_phase(grow_id: str):
    """Change grow phase

    Body:
        new_phase: seedling|vegetative|flowering|drying|curing (required)
        notes: string (optional)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        new_phase = data.get('new_phase')
        notes = data.get('notes', '')

        valid_phases = ['seedling', 'vegetative', 'flowering', 'drying', 'curing']
        if new_phase not in valid_phases:
            return jsonify(create_response(False, error=f"Invalid phase. Must be one of: {', '.join(valid_phases)}")), 400

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        now = datetime.now().isoformat()

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get current phase
            cursor.execute("SELECT current_phase, phase_started_at FROM grows WHERE id = ?", (grow_id,))
            row = cursor.fetchone()
            if not row:
                return jsonify(create_response(False, error="Grow not found")), 404

            old_phase = row[0]
            old_phase_started = row[1]

            if old_phase == new_phase:
                return jsonify(create_response(False, error="Already in this phase")), 400

            # Calculate duration of old phase
            duration_days = calculate_duration_days(old_phase_started, now)

            # Close old phase event
            cursor.execute("""
                UPDATE phase_events
                SET ended_at = ?, duration_days = ?
                WHERE grow_id = ? AND phase = ? AND ended_at IS NULL
            """, (now, duration_days, grow_id, old_phase))

            # Create new phase event
            phase_event_id = generate_uuid()
            cursor.execute("""
                INSERT INTO phase_events (id, grow_id, phase, started_at, notes, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (phase_event_id, grow_id, new_phase, now, notes, now))

            # Update grow
            cursor.execute("""
                UPDATE grows
                SET current_phase = ?, phase_started_at = ?, updated_at = ?
                WHERE id = ?
            """, (new_phase, now, now, grow_id))

            conn.commit()

        logger.info(f"Changed phase for grow {grow_id}: {old_phase} -> {new_phase}")

        return jsonify(create_response(True, {
            'message': 'Phase changed successfully',
            'old_phase': old_phase,
            'new_phase': new_phase,
            'duration_days': duration_days
        }))

    except Exception as e:
        logger.error(f"Error in change_phase: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/grows/<grow_id>/timeline', methods=['GET'])
def get_timeline(grow_id: str):
    """Get phase timeline for grow"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, phase, started_at, ended_at, duration_days, notes, created_at
                FROM phase_events
                WHERE grow_id = ?
                ORDER BY started_at ASC
            """, (grow_id,))

            rows = cursor.fetchall()

            timeline = []
            for row in rows:
                timeline.append({
                    'id': row[0],
                    'phase': row[1],
                    'started_at': row[2],
                    'ended_at': row[3],
                    'duration_days': row[4],
                    'notes': row[5],
                    'created_at': row[6]
                })

        return jsonify(create_response(True, {'timeline': timeline, 'count': len(timeline)}))

    except Exception as e:
        logger.error(f"Error in get_timeline: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# API Routes: Daily Logs
# ============================================================================

@calendar_bp.route('/api/calendar/grows/<grow_id>/logs', methods=['GET'])
def get_grow_logs(grow_id: str):
    """Get all daily logs for a grow

    Query Parameters:
        limit: max results (default: 100)
        from_date: YYYY-MM-DD (optional)
        to_date: YYYY-MM-DD (optional)
    """
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        limit = int(request.args.get('limit', 100))
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')

        with db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, grow_id, log_date, watered, fertilized, water_amount_ml,
                       fertilizer_type, fertilizer_amount_ml, notes, plant_height_cm,
                       photos, created_at, updated_at
                FROM daily_logs
                WHERE grow_id = ?
            """
            params = [grow_id]

            if from_date:
                query += " AND log_date >= ?"
                params.append(from_date)
            if to_date:
                query += " AND log_date <= ?"
                params.append(to_date)

            query += " ORDER BY log_date DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            rows = cursor.fetchall()

            logs = []
            for row in rows:
                logs.append({
                    'id': row[0],
                    'grow_id': row[1],
                    'log_date': row[2],
                    'watered': bool(row[3]),
                    'fertilized': bool(row[4]),
                    'water_amount_ml': row[5],
                    'fertilizer_type': row[6],
                    'fertilizer_amount_ml': row[7],
                    'notes': row[8],
                    'plant_height_cm': row[9],
                    'photos': row[10],
                    'created_at': row[11],
                    'updated_at': row[12]
                })

        return jsonify(create_response(True, {'logs': logs, 'count': len(logs)}))

    except Exception as e:
        logger.error(f"Error in get_grow_logs: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/logs', methods=['POST'])
def create_log():
    """Create daily log entry

    Body:
        grow_id: string (required)
        log_date: YYYY-MM-DD (required)
        watered: boolean (default: false)
        fertilized: boolean (default: false)
        water_amount_ml: integer (optional)
        fertilizer_type: string (optional)
        fertilizer_amount_ml: integer (optional)
        notes: string (optional)
        plant_height_cm: float (optional)
        photos: JSON array (optional)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()

        # Validate required fields
        grow_id = data.get('grow_id')
        log_date = data.get('log_date')

        if not grow_id or not log_date:
            return jsonify(create_response(False, error="grow_id and log_date are required")), 400

        if not validate_date(log_date):
            return jsonify(create_response(False, error="Invalid date format. Use YYYY-MM-DD")), 400

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if log already exists for this date
            cursor.execute("SELECT id FROM daily_logs WHERE grow_id = ? AND log_date = ?", (grow_id, log_date))
            if cursor.fetchone():
                return jsonify(create_response(False, error="Log already exists for this date. Use PUT to update.")), 409

            log_id = generate_uuid()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO daily_logs (
                    id, grow_id, log_date, watered, fertilized,
                    water_amount_ml, fertilizer_type, fertilizer_amount_ml,
                    notes, plant_height_cm, photos, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                log_id,
                grow_id,
                log_date,
                1 if data.get('watered', False) else 0,
                1 if data.get('fertilized', False) else 0,
                data.get('water_amount_ml'),
                data.get('fertilizer_type'),
                data.get('fertilizer_amount_ml'),
                data.get('notes', ''),
                data.get('plant_height_cm'),
                data.get('photos'),
                now,
                now
            ))

            conn.commit()

        logger.info(f"Created daily log: {log_id} for grow {grow_id} on {log_date}")

        return jsonify(create_response(True, {
            'log_id': log_id,
            'message': 'Log created successfully'
        })), 201

    except Exception as e:
        logger.error(f"Error in create_log: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/logs/<log_id>', methods=['GET'])
def get_log(log_id: str):
    """Get specific daily log"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, grow_id, log_date, watered, fertilized, water_amount_ml,
                       fertilizer_type, fertilizer_amount_ml, notes, plant_height_cm,
                       photos, created_at, updated_at
                FROM daily_logs
                WHERE id = ?
            """, (log_id,))

            row = cursor.fetchone()
            if not row:
                return jsonify(create_response(False, error="Log not found")), 404

            log = {
                'id': row[0],
                'grow_id': row[1],
                'log_date': row[2],
                'watered': bool(row[3]),
                'fertilized': bool(row[4]),
                'water_amount_ml': row[5],
                'fertilizer_type': row[6],
                'fertilizer_amount_ml': row[7],
                'notes': row[8],
                'plant_height_cm': row[9],
                'photos': row[10],
                'created_at': row[11],
                'updated_at': row[12]
            }

        return jsonify(create_response(True, {'log': log}))

    except Exception as e:
        logger.error(f"Error in get_log: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/logs/<log_id>', methods=['PUT'])
def update_log(log_id: str):
    """Update daily log entry"""
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        # Build dynamic UPDATE query
        updates = []
        params = []

        for field in ['watered', 'fertilized']:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(1 if data[field] else 0)

        for field in ['water_amount_ml', 'fertilizer_type', 'fertilizer_amount_ml',
                     'notes', 'plant_height_cm', 'photos']:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])

        if not updates:
            return jsonify(create_response(False, error="No fields to update")), 400

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(log_id)

        with db.get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE daily_logs SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            if cursor.rowcount == 0:
                return jsonify(create_response(False, error="Log not found")), 404

            conn.commit()

        logger.info(f"Updated daily log: {log_id}")
        return jsonify(create_response(True, {'message': 'Log updated successfully'}))

    except Exception as e:
        logger.error(f"Error in update_log: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/logs/<log_id>', methods=['DELETE'])
def delete_log(log_id: str):
    """Delete daily log"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM daily_logs WHERE id = ?", (log_id,))

            if cursor.rowcount == 0:
                return jsonify(create_response(False, error="Log not found")), 404

            conn.commit()

        logger.info(f"Deleted daily log: {log_id}")
        return jsonify(create_response(True, {'message': 'Log deleted successfully'}))

    except Exception as e:
        logger.error(f"Error in delete_log: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# API Routes: Calendar Month View
# ============================================================================

@calendar_bp.route('/api/calendar/month/<month_str>', methods=['GET'])
def get_month_view(month_str: str):
    """Get calendar view for specific month

    Path Parameter:
        month_str: YYYY-MM format

    Returns:
        Dictionary with daily aggregated data for the month
    """
    try:
        # Validate month format
        try:
            year, month = month_str.split('-')
            year = int(year)
            month = int(month)
            if month < 1 or month > 12:
                raise ValueError()
        except:
            return jsonify(create_response(False, error="Invalid month format. Use YYYY-MM")), 400

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        # Calculate date range
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get all logs for the month across all grows
            cursor.execute("""
                SELECT dl.log_date, dl.grow_id, g.name, g.current_phase,
                       dl.watered, dl.fertilized, dl.notes, dl.plant_height_cm
                FROM daily_logs dl
                JOIN grows g ON dl.grow_id = g.id
                WHERE dl.log_date >= ? AND dl.log_date < ?
                ORDER BY dl.log_date ASC
            """, (start_date, end_date))

            rows = cursor.fetchall()

            # Aggregate by date
            calendar = {}
            for row in rows:
                date = row[0]
                if date not in calendar:
                    calendar[date] = {
                        'date': date,
                        'entries': []
                    }

                calendar[date]['entries'].append({
                    'grow_id': row[1],
                    'grow_name': row[2],
                    'phase': row[3],
                    'watered': bool(row[4]),
                    'fertilized': bool(row[5]),
                    'notes': row[6],
                    'plant_height_cm': row[7]
                })

        return jsonify(create_response(True, {
            'month': month_str,
            'calendar': calendar,
            'days_count': len(calendar)
        }))

    except Exception as e:
        logger.error(f"Error in get_month_view: {e}")
        return jsonify(create_response(False, error=str(e))), 500


# ============================================================================
# API Routes: Phase Milestones (Events System)
# ============================================================================

@calendar_bp.route('/api/calendar/milestones', methods=['GET'])
def get_milestones():
    """Get all milestones (system + custom)

    Query Parameters:
        phase: seedling|vegetative|flowering|drying|curing (optional filter)
        category: training|environment|nutrients|observation|harvest (optional)
        enabled_only: true/false (default: true)
    """
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        phase = request.args.get('phase')
        category = request.args.get('category')
        enabled_only = request.args.get('enabled_only', 'true').lower() == 'true'

        with db.get_connection() as conn:
            cursor = conn.cursor()

            query = """
                SELECT id, phase, day_offset_min, day_offset_max, title, title_en,
                       description, icon, category, env_params, is_system, is_enabled,
                       created_at, updated_at
                FROM phase_milestones
                WHERE 1=1
            """
            params = []

            if phase:
                query += " AND phase = ?"
                params.append(phase)

            if category:
                query += " AND category = ?"
                params.append(category)

            if enabled_only:
                query += " AND is_enabled = 1"

            query += " ORDER BY phase, day_offset_min ASC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

            milestones = []
            for row in rows:
                milestones.append({
                    'id': row[0],
                    'phase': row[1],
                    'day_offset_min': row[2],
                    'day_offset_max': row[3],
                    'title': row[4],
                    'title_en': row[5],
                    'description': row[6],
                    'icon': row[7],
                    'category': row[8],
                    'env_params': row[9],
                    'is_system': bool(row[10]),
                    'is_enabled': bool(row[11]),
                    'created_at': row[12],
                    'updated_at': row[13]
                })

        return jsonify(create_response(True, {'milestones': milestones, 'count': len(milestones)}))

    except Exception as e:
        logger.error(f"Error in get_milestones: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/milestones/for-date', methods=['GET'])
def get_milestones_for_date():
    """Get milestones applicable for a specific grow + date

    Query Parameters:
        grow_id: string (required)
        date: YYYY-MM-DD (required)

    Logic:
        1. Get grow's current_phase and phase_started_at
        2. Calculate phase_day = (date - phase_started_at).days + 1
        3. Query milestones where:
           - phase matches grow.current_phase
           - day_offset_min <= phase_day
           - day_offset_max >= phase_day (or NULL)
           - is_enabled = 1
    """
    try:
        grow_id = request.args.get('grow_id')
        date_str = request.args.get('date')

        if not grow_id or not date_str:
            return jsonify(create_response(False, error="grow_id and date are required")), 400

        if not validate_date(date_str):
            return jsonify(create_response(False, error="Invalid date format. Use YYYY-MM-DD")), 400

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Get grow details
            cursor.execute("""
                SELECT current_phase, phase_started_at
                FROM grows
                WHERE id = ?
            """, (grow_id,))

            grow_row = cursor.fetchone()
            if not grow_row:
                return jsonify(create_response(False, error="Grow not found")), 404

            current_phase = grow_row[0]
            phase_started_at = grow_row[1]

            # Calculate phase day
            phase_start_dt = datetime.fromisoformat(phase_started_at)
            target_date_dt = datetime.strptime(date_str, '%Y-%m-%d')
            phase_day = (target_date_dt.date() - phase_start_dt.date()).days + 1

            # Get applicable milestones
            cursor.execute("""
                SELECT id, phase, day_offset_min, day_offset_max, title, title_en,
                       description, icon, category, env_params, is_system, is_enabled,
                       created_at, updated_at
                FROM phase_milestones
                WHERE phase = ?
                  AND day_offset_min <= ?
                  AND (day_offset_max IS NULL OR day_offset_max >= ?)
                  AND is_enabled = 1
                ORDER BY day_offset_min ASC
            """, (current_phase, phase_day, phase_day))

            rows = cursor.fetchall()

            milestones = []
            for row in rows:
                milestones.append({
                    'id': row[0],
                    'phase': row[1],
                    'day_offset_min': row[2],
                    'day_offset_max': row[3],
                    'title': row[4],
                    'title_en': row[5],
                    'description': row[6],
                    'icon': row[7],
                    'category': row[8],
                    'env_params': row[9],
                    'is_system': bool(row[10]),
                    'is_enabled': bool(row[11]),
                    'created_at': row[12],
                    'updated_at': row[13]
                })

        return jsonify(create_response(True, {
            'milestones': milestones,
            'count': len(milestones),
            'context': {
                'grow_id': grow_id,
                'date': date_str,
                'phase': current_phase,
                'phase_day': phase_day
            }
        }))

    except Exception as e:
        logger.error(f"Error in get_milestones_for_date: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/milestones', methods=['POST'])
def create_milestone():
    """Create custom milestone (is_system=0)

    Body:
        phase: seedling|vegetative|flowering|drying|curing (required)
        day_offset_min: integer (required)
        day_offset_max: integer (optional)
        title: string (required)
        title_en: string (optional)
        description: string (optional)
        icon: string (optional)
        category: string (optional)
        env_params: JSON string (optional)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()

        # Validate required fields
        phase = data.get('phase')
        day_offset_min = data.get('day_offset_min')
        title = data.get('title')

        if not phase or day_offset_min is None or not title:
            return jsonify(create_response(False, error="phase, day_offset_min, and title are required")), 400

        valid_phases = ['seedling', 'vegetative', 'flowering', 'drying', 'curing']
        if phase not in valid_phases:
            return jsonify(create_response(False, error=f"Invalid phase. Must be one of: {', '.join(valid_phases)}")), 400

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            milestone_id = generate_uuid()
            now = datetime.now().isoformat()

            cursor.execute("""
                INSERT INTO phase_milestones (
                    id, phase, day_offset_min, day_offset_max, title, title_en,
                    description, icon, category, env_params, is_system, is_enabled,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1, ?, ?)
            """, (
                milestone_id,
                phase,
                day_offset_min,
                data.get('day_offset_max'),
                title,
                data.get('title_en'),
                data.get('description'),
                data.get('icon'),
                data.get('category'),
                data.get('env_params'),
                now,
                now
            ))

            conn.commit()

        logger.info(f"Created custom milestone: {milestone_id} ({title})")

        return jsonify(create_response(True, {
            'milestone_id': milestone_id,
            'message': 'Milestone created successfully'
        })), 201

    except Exception as e:
        logger.error(f"Error in create_milestone: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/milestones/<milestone_id>', methods=['PUT'])
def update_milestone(milestone_id: str):
    """Update milestone (custom only - system milestones cannot be edited)

    Body:
        title: string (optional)
        title_en: string (optional)
        description: string (optional)
        icon: string (optional)
        category: string (optional)
        day_offset_min: integer (optional)
        day_offset_max: integer (optional)
        env_params: JSON string (optional)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if milestone exists and is custom
            cursor.execute("SELECT is_system FROM phase_milestones WHERE id = ?", (milestone_id,))
            row = cursor.fetchone()

            if not row:
                return jsonify(create_response(False, error="Milestone not found")), 404

            if row[0]:  # is_system = 1
                return jsonify(create_response(False, error="Cannot edit system milestones")), 403

            # Build dynamic UPDATE query
            updates = []
            params = []

            for field in ['title', 'title_en', 'description', 'icon', 'category',
                         'day_offset_min', 'day_offset_max', 'env_params']:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])

            if not updates:
                return jsonify(create_response(False, error="No fields to update")), 400

            updates.append("updated_at = ?")
            params.append(datetime.now().isoformat())
            params.append(milestone_id)

            query = f"UPDATE phase_milestones SET {', '.join(updates)} WHERE id = ?"
            cursor.execute(query, params)

            conn.commit()

        logger.info(f"Updated custom milestone: {milestone_id}")
        return jsonify(create_response(True, {'message': 'Milestone updated successfully'}))

    except Exception as e:
        logger.error(f"Error in update_milestone: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/milestones/<milestone_id>/toggle', methods=['PATCH'])
def toggle_milestone(milestone_id: str):
    """Enable/Disable milestone (works for system + custom)

    Body:
        enabled: boolean (required)
    """
    if not request.is_json:
        return jsonify(create_response(False, error="Request must be JSON")), 400

    try:
        data = request.get_json()

        if 'enabled' not in data:
            return jsonify(create_response(False, error="enabled field is required")), 400

        enabled = bool(data['enabled'])

        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE phase_milestones
                SET is_enabled = ?, updated_at = ?
                WHERE id = ?
            """, (1 if enabled else 0, datetime.now().isoformat(), milestone_id))

            if cursor.rowcount == 0:
                return jsonify(create_response(False, error="Milestone not found")), 404

            conn.commit()

        status = "enabled" if enabled else "disabled"
        logger.info(f"Milestone {milestone_id} {status}")

        return jsonify(create_response(True, {
            'message': f'Milestone {status} successfully',
            'enabled': enabled
        }))

    except Exception as e:
        logger.error(f"Error in toggle_milestone: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/milestones/<milestone_id>', methods=['DELETE'])
def delete_milestone(milestone_id: str):
    """Delete milestone (custom only - system milestones return 403)"""
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Check if milestone exists and is custom
            cursor.execute("SELECT is_system FROM phase_milestones WHERE id = ?", (milestone_id,))
            row = cursor.fetchone()

            if not row:
                return jsonify(create_response(False, error="Milestone not found")), 404

            if row[0]:  # is_system = 1
                return jsonify(create_response(False, error="Cannot delete system milestones. Use PATCH /toggle to disable instead.")), 403

            # Delete custom milestone
            cursor.execute("DELETE FROM phase_milestones WHERE id = ?", (milestone_id,))
            conn.commit()

        logger.info(f"Deleted custom milestone: {milestone_id}")
        return jsonify(create_response(True, {'message': 'Milestone deleted successfully'}))

    except Exception as e:
        logger.error(f"Error in delete_milestone: {e}")
        return jsonify(create_response(False, error=str(e))), 500


@calendar_bp.route('/api/calendar/tips/today', methods=['GET'])
def get_today_tips():
    """
    Get context-aware cultivation guidance, active milestones, and environmental
    targets for the currently active grow cycle.
    """
    try:
        db = get_db_connection()
        if not db:
            return jsonify(create_response(False, error="Database not available")), 500

        with db.get_connection() as conn:
            cursor = conn.cursor()

            # Find active grow
            cursor.execute("""
                SELECT id, name, strain, start_date, current_phase, phase_started_at
                FROM grows
                WHERE is_active = 1
                ORDER BY start_date DESC
                LIMIT 1
            """)
            grow_row = cursor.fetchone()
            if not grow_row:
                return jsonify(create_response(True, {
                    'active_grow': None,
                    'tips': [],
                    'message': 'No active grow cycle found'
                }))

            grow_id, name, strain, start_date, current_phase, phase_started_at = grow_row

            # Calculate phase day and total grow day
            now_date = datetime.now().date()
            phase_start = datetime.fromisoformat(phase_started_at).date()
            start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()

            phase_day = max(1, (now_date - phase_start).days + 1)
            total_days = max(1, (now_date - start_dt).days + 1)

            # Query all enabled milestones for current phase
            cursor.execute("""
                SELECT id, day_offset_min, day_offset_max, title, title_en,
                       description, icon, category, env_params
                FROM phase_milestones
                WHERE phase = ? AND is_enabled = 1
                ORDER BY day_offset_min ASC
            """, (current_phase,))

            rows = cursor.fetchall()
            active_tips = []
            upcoming_tips = []
            target_env = None

            for r in rows:
                ms_id, d_min, d_max, title, title_en, desc, icon, cat, env_p = r
                d_max_val = d_max if d_max is not None else d_min

                item = {
                    'id': ms_id,
                    'day_offset_min': d_min,
                    'day_offset_max': d_max,
                    'title': title,
                    'title_en': title_en,
                    'description': desc,
                    'icon': icon,
                    'category': cat,
                    'env_params': env_p
                }

                # Is it active today?
                if d_min <= phase_day <= d_max_val:
                    active_tips.append(item)
                    if env_p and not target_env:
                        target_env = env_p
                # Is it upcoming in next 7 days?
                elif phase_day < d_min <= (phase_day + 7):
                    upcoming_tips.append(item)

            # Highlight tip summary
            primary_tip = None
            if active_tips:
                primary_tip = f"{active_tips[0]['icon']} {active_tips[0]['title']}: {active_tips[0]['description']}"
            elif current_phase == 'flowering':
                primary_tip = f"🌸 Blütetag {phase_day}: Auf gleichmäßige Beleuchtung, 40-50% rLF und stabile Blütendüngung achten."
            elif current_phase == 'vegetative':
                primary_tip = f"🌿 Wachstumstag {phase_day}: Gleichmäßiges Blätterdach formen, LST/Topping und Wachstumsklima (22-26°C, 55-65% rLF) einhalten."
            elif current_phase == 'seedling':
                primary_tip = f"🌱 Keimlingstag {phase_day}: Mäßig gießen, 21-25°C und 65-75% rLF halten."
            elif current_phase == 'drying':
                primary_tip = f"🌾 Trocknungstag {phase_day}: 16-20°C, 55-60% rLF und absolute Dunkelheit mit sanfter Umluft einhalten."
            else:
                primary_tip = f"🏺 Curingtag {phase_day}: Gläser regelmäßig lüften und Feuchtigkeit bei 58-62% rLF stabilisieren."

            return jsonify(create_response(True, {
                'active_grow': {
                    'id': grow_id,
                    'name': name,
                    'strain': strain,
                    'start_date': start_date,
                    'current_phase': current_phase,
                    'phase_day': phase_day,
                    'total_days': total_days
                },
                'primary_tip': primary_tip,
                'active_tips': active_tips,
                'upcoming_tips': upcoming_tips,
                'target_env': target_env
            }))

    except Exception as e:
        logger.error(f"Error in get_today_tips: {e}")
        return jsonify(create_response(False, error=str(e))), 500
