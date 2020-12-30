from datetime import datetime
from enum import Enum, auto

from picamera import PiCamera, Color

from rpicam.utils.logging import get_logger




class ExecPoint(Enum):
    BEFORE_INIT = auto()
    AFTER_INIT = auto()
    BEFORE_RECORD = auto()
    BEFORE_STACK_CAPTURE = auto()
    BEFORE_FRAME_CAPTURE = auto()
    AFTER_FRAME_CAPTURE = auto()
    AFTER_STACK_CAPTURE = auto()
    AFTER_RECORD = auto()
    BEFORE_CONVERT = auto()
    AFTER_CONVERT = auto()
    ON_EXCEPTION = auto()


class Callback:
    def __init__(self, exec_at: ExecPoint, priority: int = -1, verb: bool = False):
        self.exec_at = exec_at
        self.priority = priority
        self._logger = get_logger(self.__class__.__name__, verb=verb)

    def __call__(self, *args, **kwargs):
        pass


class EchoCallback(Callback):
    def __init__(self):
        super().__init__(exec_at=ExecPoint.BEFORE_INIT, priority=999, verb=True)

    def __call__(self, *args, **kwargs):
        self._logger.warn(
            f'Running callback at {self.exec_at} with priority {self.priority}'
            f' (args={args}, kwargs={kwargs})'
        )


class AnnotateFrameWithDt(Callback):
    """
    Annotates the captured PiCamera frame with the datetime in the given format.
    """

    def __init__(self, fmt: str = '%Y-%m-%dT%H:%M%S'):
        super().__init__(exec_at=ExecPoint.BEFORE_FRAME_CAPTURE, priority=-999)
        self._fmt = fmt

    def __call__(self, cam: PiCamera, *args, **kwargs):
        if self._fmt is not None:
            cam.annotate_background = Color('black')
            cam.annotate_text = datetime.now().strftime(self._fmt)
        else:
            cam.annotate_background = None
            cam.annotate_text = None
