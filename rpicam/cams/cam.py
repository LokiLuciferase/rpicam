from typing import List
from time import sleep
from pathlib import Path
from tempfile import TemporaryDirectory
from abc import ABC, abstractmethod

from picamera2 import Picamera2 as PiCamera, Preview
from libcamera import Transform

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
    :param hvflip: whether to rotate camera 180 degrees.
    :param args: any positional arguments are passed on to the PiCamera constructor.
    :param kwargs: any keyword arguments are passed on to the PiCamera constructor.
    """

    TMPDIR_PREFIX = 'rpicam-cam-'

    def __init__(
        self,
        verbose: bool = False,
        tmpdir: Path = None,
        callbacks: List[Callback] = (),
        hvflip: bool = False,
        resolution = (1024, 768),
        # picamera settings
        *args,
        **kwargs,
    ):
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        self._cbh = CallbackHandler(callbacks)
        self._cbh.execute_callbacks(ExecPoint.BEFORE_INIT)
        if hvflip:
            transform = Transform(vflip=True, hflip=True)
        else:
            transform = Transform()
        self.cam = PiCamera(*args, **kwargs)
        self.config = self.cam.create_still_configuration(main={'size':resolution}, transform=transform)
        self.cam.configure(self.config)
        self.cam.start()
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=self.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))

    def __del__(self):
        self.cam.stop()

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
