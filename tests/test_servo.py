import pytest

from rpicam.servo import Servo, full_ccw, full_cw, noon, pause


def test_execute_sequence():
    s = Servo(7, verbose=True)
    s.execute_sequence(
        [
            full_cw,
            noon,
            pause,
            full_ccw,
            pause,
            noon,
            pause,
        ]
    )
