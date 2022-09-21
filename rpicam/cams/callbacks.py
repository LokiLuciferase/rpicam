from typing import Union
from pathlib import Path
from datetime import datetime
from enum import Enum, auto
import time
from time import sleep

from picamera2 import Picamera2 as PiCamera, MappedArray
import cv2

from rpicam.utils.logging_utils import get_logger
from rpicam.utils.telegram_poster import TelegramPoster


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
    def __init__(self, exec_at: ExecPoint, priority: int = -1):
        self.exec_at = exec_at
        self.priority = priority

    def __call__(self, *args, **kwargs):
        pass


class AnnotateFrameWithDt(Callback):
    """
    Annotates the captured PiCamera frame with the datetime in the given format.
    """

    def __init__(self, fmt: str = '%Y-%m-%dT%H:%M%S'):
        super().__init__(exec_at=ExecPoint.BEFORE_FRAME_CAPTURE, priority=-999)
        self._fmt = fmt
        self._color = (0, 255, 0)
        self._origin = (10, 30)
        self._font = cv2.FONT_HERSHEY_SIMPLEX
        self._scale = 1
        self._thickness = 2

    def _apply_timestamp(self, request):
        timestamp = time.strftime(self._fmt)
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, timestamp, self._origin, self._font, self._scale, self._color, self._thickness)

    def __call__(self, cam: PiCamera, *args, **kwargs):
        if self._fmt is not None:
            cam.pre_callback = self._apply_timestamp


class PostToTg(Callback):
    """
    Posts the created file to Telegram using credentials stored in environment.
    """
    def __init__(self):
        super().__init__(exec_at=ExecPoint.AFTER_CONVERT, priority=999)
        self._poster = TelegramPoster()

    def __call__(self, outfile: Union[str, Path], *args, **kwargs):
        try:
            self._poster.send_video(outfile)
        except Exception:
            pass


class SendExceptionToTg(Callback):
    """
    Posts the exception to Telegram using credentials stored in environment.
    """
    def __init__(self):
        super().__init__(exec_at=ExecPoint.ON_EXCEPTION, priority=999)
        self._poster = TelegramPoster()

    def __call__(self, exc: Exception, *args, **kwargs):
        try:
            self._poster.send_text(f'rpicam has stopped: {exc}')
        except Exception:
            pass


class ExecutionTimeout(Callback):
    """
    Delays Execution until self.blocked is False.
    """

    MESSAGE_ABOVE = 20

    def __init__(self, exec_at: ExecPoint, timeout: float = 0.5, verbose: bool = False):
        super().__init__(exec_at=exec_at, priority=1000)
        self.timeout = timeout
        self.blocked = False
        self._logger = get_logger(self.__class__.__name__, verb=verbose)

    def __call__(self, *args, **kwargs):
        while self.blocked:
            if self.timeout >= self.MESSAGE_ABOVE:
                self._logger.info(f'Execution blocked for {self.timeout} sec at {self.exec_at}.')
            sleep(self.timeout)
