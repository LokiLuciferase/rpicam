from typing import List, Tuple
from time import sleep
from pathlib import Path
from tempfile import TemporaryDirectory
from abc import ABC, abstractmethod

from picamera2 import Picamera2 as PiCamera, Preview
from libcamera import Transform, controls

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
    ):
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=self.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        self._cbh = CallbackHandler(callbacks)
        self._cbh.execute_callbacks(ExecPoint.BEFORE_INIT)
        if hvflip:
            self._transform = Transform(vflip=True, hflip=True)
        else:
            self._transform = Transform()
        self.cam = PiCamera()
        self.cam.set_controls({'AwbMode': controls.AwbModeEnum.Indoor})

    def __del__(self):
        try:
            self.cam.stop()
            self.cam.stop_encoder()
        except Exception:
            pass
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


class StillCam(Cam):
    def __init__(self, resolution: Tuple[int, int] = (1024, 768), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = self.cam.create_still_configuration(
            main={'size': resolution}, transform=self._transform
        )
        self.cam.align_configuration(self.config)
        self.cam.configure(self.config)
        self.cam.start()


class VideoCam(Cam):
    def __init__(
        self,
        main_resolution: Tuple[int, int] = (1024, 768),
        lores_resolution: Tuple[int, int] = (320, 240),
        encode_stream: str = 'lores',
        do_start: bool = False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.config = self.cam.create_video_configuration(
            main={'size': main_resolution},
            lores={'size': lores_resolution},
            transform=self._transform,
            encode=encode_stream
        )
        self.cam.align_configuration(self.config)
        self.cam.configure(self.config)
        if do_start:
            self.cam.start()
