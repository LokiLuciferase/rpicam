from typing import NamedTuple
import re


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


def parse_servo_op(s: str) -> ServoOp:
    ops_map = {'pause': pause, 'noon': noon, 'full_cw': full_cw, 'full_ccw': full_ccw, 'cw': cw, 'ccw': ccw}
    if s in ops_map:
        return ops_map[s]
    elif re.match('\w+\(\d+\)', s):
        match_obj = re.search('(\w+)\((\d+)\)', s)
        smatch = match_obj.group(1)
        imatch = int(match_obj.group(2))
        if smatch == 'cw':
            return ServoOp(angle=imatch, sense='CW')
        elif smatch == 'ccw':
            return ServoOp(angle=imatch, sense='CCW')
        elif smatch == 'pause':
            return ServoOp(sleep=imatch)
        else:
            raise RuntimeError(f'Unknown parametrized ServoOp name: {smatch}')
    else:
        raise RuntimeError(f'Could not parse ServoOp: {s}')


cw = ServoOp(30, 'CW')
ccw = ServoOp(30, 'CCW')
full_cw = ServoOp(sense='CW')
full_ccw = ServoOp(sense='CCW')
noon = ServoOp(90)
pause = ServoOp(sleep=1)

