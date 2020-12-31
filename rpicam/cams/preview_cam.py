from threading import Thread, Event
from queue import Queue
from io import BytesIO

from PIL import Image

from rpicam.cams.cam import Cam
from rpicam.cams.callbacks import ExecPoint
from rpicam.utils.viewer import Viewer


class LivePreviewCam(Cam):
    """
    Cam for producing a live stream in a GUI window.
    """
    def __init__(self, camera_rotation: int = 0, *args, **kwargs):
        super().__init__(camera_rotation=camera_rotation, *args, **kwargs)
        self._viewer = Viewer()
        self._img_queue = Queue()
        self._execute_callbacks(loc=ExecPoint.AFTER_INIT)

    def _create_frame(self, *args, **kwargs) -> Image:
        self._execute_callbacks(loc=ExecPoint.BEFORE_FRAME_CAPTURE, cam=self.cam)
        stream = BytesIO()
        self.cam.capture(stream, format='jpeg', *args, **kwargs)
        stream.seek(0)
        img = Image.open(stream)
        self._execute_callbacks(loc=ExecPoint.AFTER_FRAME_CAPTURE, cam=self.cam)
        return img

    def _frame_producer(self, event: Event, *args, **kwargs):
        while not event.is_set():
            new_frame = self._create_frame(*args, **kwargs)
            self._img_queue.put(new_frame)

    def record(
        self,
        *args,
        **kwargs,
    ):
        """
        Starts the live preview in a GUI window. Ends when GUI window is closed.

        :param args: any positional arguments passed on to PiCamera.capture()
        :param kwargs: any keyword arguments passed on to PiCamera.capture()
        :return: None
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_RECORD)
        event = Event()
        frame_producer = Thread(
            target=self._frame_producer,
            args=args,
            kwargs={'event': event, **kwargs},
            daemon=True
        ).start()
        self._viewer.view_image_queue(self._img_queue)
        event.set()
        self._execute_callbacks(loc=ExecPoint.AFTER_RECORD)
