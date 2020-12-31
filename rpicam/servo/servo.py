from typing import List
import time
import RPi.GPIO as GPIO

from rpicam.servo.servo_ops import ServoOp, full_cw, full_ccw, noon, pause
from rpicam.utils.logging_utils import get_logger


GPIO.setmode(GPIO.BOARD)


class Servo:

    PRECISION_THRESHOLD_ANGLE = 20

    def __init__(
        self, board_pin: int, freq: float = 50, verbose: bool = False, hacked: bool = False
    ):
        self.pin = board_pin
        self.angle = None
        self.hacked = hacked
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        GPIO.setup(self.pin, GPIO.OUT)
        self._pwm = GPIO.PWM(self.pin, freq)
        self._initialize_servo_pos()

    def __del__(self):
        self._pwm.stop()
        GPIO.cleanup()

    def _initialize_servo_pos(self):
        """Move servo to starting position: 0°"""

        self._logger.info('Move: ??° ==> 0°')
        self._pwm.start(12.5)
        time.sleep(0.5)
        self._pwm.ChangeDutyCycle(12.5)
        time.sleep(0.5)
        self._pwm.ChangeDutyCycle(0)
        time.sleep(0.5)
        self.angle = 0

    @staticmethod
    def _angle_to_duty_cycle(angle: int) -> float:
        return ((180 - angle) / 18.0) + 2.5

    def _calculate_new_angle(self, sense: str, angle: int) -> int:
        if self.angle is None:
            raise RuntimeError('Servo position is not initialized.')
        if sense == 'CW':
            new_angle = self.angle + angle
        elif sense == 'CCW':
            new_angle = self.angle - angle
        else:
            raise RuntimeError(f'Invalid sense supplied: {sense}')
        return new_angle

    def _run_servo_op(
        self,
        angle: int = None,
        sense: str = None,
        sleep: float = None,
    ):
        """
        Run a servo operation.

        :param angle: The angle - absolute if no sense supplied, else relative to existing angle.
                      If not supplied, assume "all the way" in the supplied sense.
        :param sense: The sense to use for changing the existing angle - 'CW' or 'CCW'.
                      If not supplied, assume absolute angle.
        :param sleep: How many seconds to sleep after executing the op.
        :return: None
        """
        if all(x is None for x in (angle, sense, sleep)):
            return  # no-op
        if angle is None and sense is None:
            time.sleep(sleep)
            return
        if sense is None:
            new_angle = angle
        elif angle is None:
            new_angle = 0 if sense == 'CCW' else 180
        else:
            new_angle = self._calculate_new_angle(sense, angle)
        if not self.hacked and not 0 <= new_angle <= 180:
            raise RuntimeError('Invalid angle supplied.')
        if self.angle == new_angle:
            return
        if abs(self.angle - new_angle) < Servo.PRECISION_THRESHOLD_ANGLE:
            self._logger.warning('Operation under precision threshold.')
        new_duty_cycle = self._angle_to_duty_cycle(new_angle)
        self._logger.info(f'Move: {self.angle}° ==> {new_angle}°')
        self._pwm.ChangeDutyCycle(new_duty_cycle)
        time.sleep(0.7)  # mandatory to allow operation
        self._pwm.ChangeDutyCycle(0)
        self.angle = new_angle % 181
        if sleep:
            time.sleep(sleep)

    def run_servo_op(self, servo_op: ServoOp):
        self._run_servo_op(*servo_op)

    def execute_sequence(self, sequence: List[ServoOp], cycle: bool = False):
        """
        Execute a sequence of `ServoOp`s.

        :param sequence: A list of `ServoOp`s to execute.
        :param cycle: Whether to run the given sequence in a cycle
                      until recieving a KeyboardInterupt.
                      If so, returns to starting angle each time.
        :return:
        """
        try:
            starting_angle = self.angle
            while True:
                for tup in sequence:
                    self.run_servo_op(tup)
                if cycle:
                    self._run_servo_op(starting_angle)
                else:
                    break
        except KeyboardInterrupt:
            pass


if __name__ == '__main__':
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
