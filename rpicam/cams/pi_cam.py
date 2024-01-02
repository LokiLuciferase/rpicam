from typing import Tuple
from pathlib import Path
from abc import ABC, abstractmethod

from picamera2 import Picamera2 as PiCamera
from libcamera import Transform, controls

from rpicam.utils.storage import CameraStorageMixin


class PiCameraMixin(ABC):

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

    def __init__(self, hvflip: bool = False):
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


class StillCam(CameraStorageMixin, PiCameraMixin):
    def __init__(self, resolution: Tuple[int, int] = (1024, 768), *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = self.cam.create_still_configuration(
            main={'size': resolution}, transform=self._transform
        )
        self.cam.align_configuration(self.config)
        self.cam.configure(self.config)
        self.cam.start()


class VideoCam(CameraStorageMixin, PiCameraMixin):
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

    def capture_single_frame(self, file_path: Path):
        req = self.cam.capture_request()
        req.save('main', str(file_path))
        req.release()


class TermuxVideoCam(CameraStorageMixin):
    def capture_single_frame(self, file_path: Path):
        pass
