"""
GrowPi Lamp Control Module

PWM-based LED lamp control for 5 channels.
"""

from .pwm_controller import PWMController, LampChannel

__all__ = ["PWMController", "LampChannel"]
