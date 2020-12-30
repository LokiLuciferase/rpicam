from typing import List
from time import sleep
from pathlib import Path
from tempfile import TemporaryDirectory
from abc import ABC ,abstractmethod

from picamera import PiCamera

from rpicam.utils.logging import get_logger
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
        callbacks: List[Callback] = None,
        camera_rotation: int = 180,
        # picamera settings
        *args,
        **kwargs,
    ):
        self._callbacks = {}
        for cb in callbacks:
            self._callbacks.setdefault(cb.exec_at, []).append(cb)
        for k, v in self._callbacks.items():
            self._callbacks[k] = sorted(self._callbacks[k], key=lambda x: x.priority, reverse=True)

        self._execute_callbacks(ExecPoint.BEFORE_INIT)
        self.cam = PiCamera(*args, **kwargs)
        self.cam.rotation = camera_rotation
        sleep(2)
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=self.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))

    def __del__(self):
        self.cam.close()

    def _execute_callbacks(self, loc: ExecPoint, *args, **kwargs):
        """
        Run all callbacks associated with loc in order.

        :param loc: The execution point.
        :param args: passed on to Callbacks for the given loc.
        :param kwargs: passed on to Callbacks for the given loc.
        :return:
        """
        if loc in self._callbacks:
            for cb in self._callbacks[loc]:
                cb(*args, **kwargs)

    def _raise_with_callbacks(self, exc: Exception):
        """
        Raise the given exception after passing it through all Callbacks registered to run on error.

        :param exc: The given exception.
        :return:
        """
        self._execute_callbacks(ExecPoint.ON_EXCEPTION, exc=exc)
        raise exc

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
