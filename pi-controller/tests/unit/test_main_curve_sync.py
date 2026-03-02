from grow_pi.main import GrowPiController


class DummyCurveController:
    def __init__(self, intensities, reload_error=None):
        self.intensities = dict(intensities)
        self.reload_error = reload_error
        self.reload_calls = 0

    def reload_from_database(self):
        self.reload_calls += 1
        if self.reload_error:
            raise self.reload_error

    def get_current_intensities(self, _now=None):
        return dict(self.intensities)


class DummyPWMController:
    def __init__(self, fail_channels=None):
        self.fail_channels = set(fail_channels or [])
        self.calls = []

    def set_intensity(self, channel, intensity):
        self.calls.append((channel, intensity))
        return channel not in self.fail_channels


def _build_controller(curve_controller, pwm_controller, last_intensities=None):
    ctrl = GrowPiController.__new__(GrowPiController)
    ctrl.curve_controller = curve_controller
    ctrl.pwm_controller = pwm_controller
    ctrl.last_intensities = dict(last_intensities or {})
    return ctrl


def test_update_intensity_from_curve_reloads_database_before_apply():
    curve = DummyCurveController({1: 12, 2: 34, 3: 5, 4: 0})
    pwm = DummyPWMController()
    ctrl = _build_controller(curve, pwm)

    changed = GrowPiController._update_intensity_from_curve(ctrl)

    assert changed is True
    assert curve.reload_calls == 1
    assert pwm.calls == [(1, 12), (2, 34), (3, 5), (4, 0)]
    assert ctrl.last_intensities == {1: 12, 2: 34, 3: 5, 4: 0}


def test_update_intensity_from_curve_keeps_cache_when_pwm_write_fails():
    curve = DummyCurveController({3: 15})
    pwm = DummyPWMController(fail_channels={3})
    ctrl = _build_controller(curve, pwm, last_intensities={3: 5})

    changed = GrowPiController._update_intensity_from_curve(ctrl)

    assert changed is False
    assert curve.reload_calls == 1
    assert pwm.calls == [(3, 15)]
    assert ctrl.last_intensities[3] == 5


def test_update_intensity_from_curve_continues_when_reload_fails():
    curve = DummyCurveController({2: 20}, reload_error=RuntimeError("db unavailable"))
    pwm = DummyPWMController()
    ctrl = _build_controller(curve, pwm)

    changed = GrowPiController._update_intensity_from_curve(ctrl)

    assert changed is True
    assert curve.reload_calls == 1
    assert pwm.calls == [(2, 20)]
    assert ctrl.last_intensities[2] == 20
