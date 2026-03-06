from grow_pi.utils.power_monitor import parse_throttled_response


def test_parse_throttled_response_detects_current_and_historical_undervoltage():
    parsed = parse_throttled_response("throttled=0x50005")

    assert parsed["under_voltage_now"] is True
    assert parsed["currently_throttled"] is True
    assert parsed["under_voltage_occurred"] is True
    assert parsed["throttling_occurred"] is True
    assert parsed["healthy"] is False


def test_parse_throttled_response_reports_clean_state():
    parsed = parse_throttled_response("0x0")

    assert parsed["issues_now"] == []
    assert parsed["issues_occurred"] == []
    assert parsed["healthy"] is True
