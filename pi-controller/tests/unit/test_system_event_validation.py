import sys
import types

if "tinytuya" not in sys.modules:
    sys.modules["tinytuya"] = types.SimpleNamespace(OutletDevice=object, Cloud=object)
if "dotenv" not in sys.modules:
    sys.modules["dotenv"] = types.SimpleNamespace(load_dotenv=lambda *args, **kwargs: None)

from grow_pi.database.models import SystemEvent


def test_system_event_accepts_dynamic_event_types():
    event = SystemEvent(
        event_type="mode_change",
        severity="info",
        message="Mode changed",
    )
    assert event.event_type == "mode_change"


def test_system_event_rejects_empty_event_type():
    try:
        SystemEvent(event_type="", severity="info", message="x")
        assert False, "Expected ValueError for empty event_type"
    except ValueError as exc:
        assert "event_type" in str(exc)


def test_system_event_rejects_overlong_event_type():
    overlong = "x" * 65
    try:
        SystemEvent(event_type=overlong, severity="info", message="x")
        assert False, "Expected ValueError for overlong event_type"
    except ValueError as exc:
        assert "too long" in str(exc)
