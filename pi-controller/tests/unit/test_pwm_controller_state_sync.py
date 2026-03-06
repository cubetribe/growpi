from types import SimpleNamespace

import grow_pi.lamps.pwm_controller as pwm_module
from grow_pi.lamps.pwm_controller import PWMController, LampChannel


class DummyPi:
    def __init__(self, duty_map):
        self.connected = True
        self._duty_map = dict(duty_map)
        self.set_frequency_calls = []
        self.set_range_calls = []
        self.set_duty_calls = []

    def get_PWM_dutycycle(self, gpio_pin: int) -> int:
        value = self._duty_map[gpio_pin]
        if isinstance(value, Exception):
            raise value
        return value

    def set_PWM_frequency(self, gpio_pin: int, frequency: int) -> None:
        self.set_frequency_calls.append((gpio_pin, frequency))

    def set_PWM_range(self, gpio_pin: int, pwm_range: int) -> None:
        self.set_range_calls.append((gpio_pin, pwm_range))

    def set_PWM_dutycycle(self, gpio_pin: int, duty_cycle: int) -> None:
        self.set_duty_calls.append((gpio_pin, duty_cycle))
        self._duty_map[gpio_pin] = duty_cycle


def build_controller(duty_map):
    ctrl = PWMController()
    ctrl.simulation_mode = False
    ctrl._initialized = True
    ctrl.pi = DummyPi(duty_map)
    ctrl.channels = {
        1: LampChannel(channel=1, name="Far Red", gpio_pin=16, pwm_frequency=1000, software_pwm=False),
        2: LampChannel(channel=2, name="Warm White", gpio_pin=13, pwm_frequency=1000, software_pwm=False),
        3: LampChannel(channel=3, name="Cool White", gpio_pin=18, pwm_frequency=1000, software_pwm=False),
        4: LampChannel(channel=4, name="UV", gpio_pin=12, pwm_frequency=1000, software_pwm=False),
    }
    return ctrl


def test_get_current_state_reads_hardware_dutycycle():
    ctrl = build_controller({16: 93, 13: 16, 18: 18, 12: 0})
    state = ctrl.get_current_state()
    assert state == {1: 93, 2: 16, 3: 18, 4: 0}


def test_get_current_state_preserves_cached_value_on_read_error():
    ctrl = build_controller({16: 50, 13: RuntimeError("read failed"), 18: 20, 12: 0})
    ctrl.channels[2].current_intensity = 7

    state = ctrl.get_current_state()
    assert state[1] == 50
    assert state[2] == 7
    assert state[3] == 20
    assert state[4] == 0


def test_initialize_with_skip_zero_init_syncs_existing_hardware_state(monkeypatch):
    dummy_pi = DummyPi({16: 93, 13: 16, 18: 18, 12: 0})

    class DummyPigpioModule:
        @staticmethod
        def pi():
            return dummy_pi

    monkeypatch.setattr(pwm_module, "pigpio", DummyPigpioModule, raising=False)

    ctrl = PWMController()
    ctrl.simulation_mode = False

    channels = [
        SimpleNamespace(channel=1, name="Far Red", gpio_pin=16, pwm_frequency=1000, software_pwm=False),
        SimpleNamespace(channel=2, name="Warm White", gpio_pin=13, pwm_frequency=1000, software_pwm=False),
        SimpleNamespace(channel=3, name="Cool White", gpio_pin=18, pwm_frequency=1000, software_pwm=False),
        SimpleNamespace(channel=4, name="UV", gpio_pin=12, pwm_frequency=1000, software_pwm=False),
    ]

    ok = ctrl.initialize(channels, skip_zero_init=True)

    assert ok is True
    assert dummy_pi.set_duty_calls == []
    assert ctrl.get_current_state() == {1: 93, 2: 16, 3: 18, 4: 0}
