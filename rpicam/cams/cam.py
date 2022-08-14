from typing import List
from time import sleep
from pathlib import Path
from tempfile import TemporaryDirectory
from abc import ABC, abstractmethod

from picamera import PiCamera

from rpicam.utils.logging_utils import get_logger
from rpicam.utils.callback_handler import CallbackHandler
from rpicam.cams.callbacks import ExecPoint, Callback


class Cam(ABC):

    """
    Cam base class to be extended with different functionalities. Comes with tmpdir and Callback
    functionality.

    :param verbose: whether to write info logs to stderr.
    :param tmpdir: The location to save any temporary files produced by the Cam.
    :param callbacks: a list of callbacks to be applied in the Cam.
    :param camera_rotation: The rotation of the camera image.
    :param args: any positional arguments are passed on to the PiCamera constructor.
    :param kwargs: any keyword arguments are passed on to the PiCamera constructor.
    """

    TMPDIR_PREFIX = 'rpicam-cam-'

    def __init__(
        self,
        verbose: bool = False,
        tmpdir: Path = None,
        callbacks: List[Callback] = (),
        camera_rotation: int = 180,
        preview: bool = False,
        # picamera settings
        *args,
        **kwargs,
    ):
        self._cbh = CallbackHandler(callbacks)
        self._cbh.execute_callbacks(ExecPoint.BEFORE_INIT)
        self._preview = preview
        self.cam = PiCamera(*args, **kwargs)
        self.cam.rotation = camera_rotation
        if self._preview:
            self.cam.start_preview()
            sleep(2)
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=self.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))

    def __del__(self):
        if self._preview:
            self.stop_preview()
        self.cam.close()

    @abstractmethod
    def record(
        self,
        *args,
        **kwargs,
    ):
        """
        Perform the requested camera operation.
        """
        pass
