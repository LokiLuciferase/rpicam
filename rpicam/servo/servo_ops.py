from typing import NamedTuple


class ServoOp(NamedTuple):
    """
    Encapsulates a Servo operation.

    :param angle: The angle - absolute if no sense supplied, else relative to existing angle.
                  If not supplied, assume "all the way" in the supplied sense.
    :param sense: The sense to use for changing the existing angle - 'CW' or 'CCW'.
                  If not supplied, assume absolute angle.
    :param sleep: How many seconds to sleep after executing the op.
    """

    angle: int = None
    sense: str = None
    sleep: float = 0.0


cw = ServoOp(30, 'CW')
ccw = ServoOp(30, 'CCW')
full_cw = ServoOp(sense='CW')
full_ccw = ServoOp(sense='CCW')
noon = ServoOp(90)
pause = ServoOp(sleep=1)
