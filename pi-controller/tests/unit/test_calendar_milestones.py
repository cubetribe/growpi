#!/usr/bin/env python3
"""
Unit tests for Calendar cultivation milestones, standard tips, and API endpoints.
"""

import os
import json
import tempfile
import pytest
from datetime import datetime, timedelta
from flask import Flask

from grow_pi.database.db import Database
from grow_pi.web.blueprints.calendar_bp import calendar_bp


@pytest.fixture
def temp_db():
    """Create a temporary database with initialized schema and default milestones."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = Database(path)
    db.initialize()
    yield db
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def app(temp_db, monkeypatch):
    """Create test Flask app with calendar blueprint and mocked get_db_connection."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(calendar_bp)

    import grow_pi.web.blueprints.calendar_bp as c_bp
    monkeypatch.setattr(c_bp, "get_db_connection", lambda: temp_db)

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_default_milestones_initialization(temp_db):
    """Test that default milestones are seeded and contain standard cultivation events."""
    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, phase, title, day_offset_min, day_offset_max, category FROM phase_milestones")
        rows = cursor.fetchall()

    assert len(rows) >= 20, f"Expected at least 20 default milestones, got {len(rows)}"

    ids = [r[0] for r in rows]
    titles = [r[2] for r in rows]
    phases = [r[1] for r in rows]

    # Verify key cultivation milestones are present
    assert "ms-flow-004" in ids  # Day 21 Defoliation
    assert any("Entlaubung" in t or "Schwazze" in t or "Defoliation" in t for t in titles)
    assert any("Topping" in t for t in titles)
    assert any("LST" in t for t in titles)
    assert any("Flush" in t or "Spülen" in t for t in titles)
    assert any("Trichom" in t for t in titles)

    assert "seedling" in phases
    assert "vegetative" in phases
    assert "flowering" in phases
    assert "drying" in phases
    assert "curing" in phases


def test_get_milestones_endpoint(client):
    """Test GET /api/calendar/milestones with phase and category filtering."""
    # All enabled
    res = client.get("/api/calendar/milestones")
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert len(data["milestones"]) >= 20

    # Filter by phase
    res_flow = client.get("/api/calendar/milestones?phase=flowering")
    data_flow = res_flow.get_json()
    assert data_flow["success"] is True
    assert all(m["phase"] == "flowering" for m in data_flow["milestones"])

    # Filter by category
    res_train = client.get("/api/calendar/milestones?category=training")
    data_train = res_train.get_json()
    assert data_train["success"] is True
    assert all(m["category"] == "training" for m in data_train["milestones"])


def test_today_tips_endpoint(client, temp_db):
    """Test GET /api/calendar/tips/today returns context-aware tips based on active grow phase."""
    # When no grow exists
    res_empty = client.get("/api/calendar/tips/today")
    assert res_empty.status_code == 200
    assert res_empty.get_json()["active_grow"] is None

    # Create an active flowering grow at day 21 (critical defoliation day)
    today = datetime.now().date()
    start_date = (today - timedelta(days=50)).isoformat()
    phase_start = (today - timedelta(days=20)).isoformat() + "T00:00:00"  # Day 21 of flower

    with temp_db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO grows (id, name, strain, start_date, current_phase, phase_started_at, is_active)
            VALUES ('test-grow-1', 'Test Flowering Grow', 'Amnesia Haze', ?, 'flowering', ?, 1)
        """, (start_date, phase_start))
        conn.commit()

    res_tips = client.get("/api/calendar/tips/today")
    assert res_tips.status_code == 200
    data_tips = res_tips.get_json()
    assert data_tips["success"] is True
    assert data_tips["active_grow"]["name"] == "Test Flowering Grow"
    assert data_tips["active_grow"]["phase_day"] == 21

    # Active tips should include Day 21 Main Defoliation / Schwazze
    active_titles = [t["title"] for t in data_tips["active_tips"]]
    assert any("Haupt-Entlaubung" in t or "Schwazze" in t or "Defoliation" in t for t in active_titles)


def test_toggle_milestone(client):
    """Test PATCH /api/calendar/milestones/<id>/toggle enables and disables milestones."""
    res_disable = client.patch("/api/calendar/milestones/ms-flow-001/toggle", json={"enabled": False})
    assert res_disable.status_code == 200
    assert res_disable.get_json()["success"] is True

    # Check that it is disabled when enabled_only is true
    res_list = client.get("/api/calendar/milestones?phase=flowering&enabled_only=true")
    ids = [m["id"] for m in res_list.get_json()["milestones"]]
    assert "ms-flow-001" not in ids

    # Re-enable
    res_enable = client.patch("/api/calendar/milestones/ms-flow-001/toggle", json={"enabled": True})
    assert res_enable.status_code == 200

    res_list2 = client.get("/api/calendar/milestones?phase=flowering&enabled_only=true")
    ids2 = [m["id"] for m in res_list2.get_json()["milestones"]]
    assert "ms-flow-001" in ids2
