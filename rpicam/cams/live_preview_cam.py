from threading import Thread, Event
from queue import Queue
from io import BytesIO
import time

from PIL import Image

from rpicam.cams.cam import Cam
from rpicam.cams.callbacks import ExecPoint
from rpicam.gui.viewer import Viewer


class LivePreviewCam(Cam):
    """
    Cam for producing a live stream in a GUI window.
    """

    def __init__(self, hvflip: bool = False, *args, **kwargs):
        super().__init__(hvflip=hvflip, *args, **kwargs)
        self._viewer = Viewer()
        self._img_queue = Queue()
        self._event = Event()
        self._execute_callbacks(loc=ExecPoint.AFTER_INIT)

    def _create_frame(self, *args, **kwargs) -> Image:
        self._execute_callbacks(loc=ExecPoint.BEFORE_FRAME_CAPTURE, cam=self.cam)
        stream = BytesIO()
        t0 = time.time()
        self.cam.capture(stream, format='jpeg', use_video_port=True, *args, **kwargs)
        t1 = time.time()
        self._logger.debug(f'Capturing took {t1 - t0} sec')
        stream.seek(0)
        img = Image.open(stream)
        self._execute_callbacks(loc=ExecPoint.AFTER_FRAME_CAPTURE, cam=self.cam)
        return img

    def _frame_producer(self, spf: int, *args, **kwargs):
        t0 = time.time()
        while not self._event.is_set():
            new_frame = self._create_frame(*args, **kwargs)
            self._img_queue.put(new_frame)
            t1 = time.time()
            to_sleep = spf - (t1 - t0)
            t0 = t1
            if to_sleep > 0:
                time.sleep(to_sleep)

    def record(
        self,
        spf: int = 5,
        *args,
        **kwargs,
    ):
        """
        Starts the live preview in a GUI window. Ends when GUI window is closed.

        :param spf: Seconds to wait between recording frames.
        :param args: any positional arguments passed on to PiCamera.capture()
        :param kwargs: any keyword arguments passed on to PiCamera.capture()
        :return: None
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_RECORD)
        self._event.clear()
        frame_producer = Thread(
            target=self._frame_producer,
            args=args,
            kwargs={'spf': spf, **kwargs},
            daemon=True,
        ).start()
        self._viewer.view_image_queue(self._img_queue)
        self._event.set()
        self._execute_callbacks(loc=ExecPoint.AFTER_RECORD)
