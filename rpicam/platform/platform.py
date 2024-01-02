from typing import Dict, Tuple
from queue import Queue, Empty
from threading import Thread
from time import sleep

from rpicam.cams.pi_cam import Cam
from rpicam.servo.servo import Servo
from rpicam.utils.logging_utils import get_logger


class Platform:

    CAM_RES_POLL_TIMEOUT = 2

    def __init__(
        self, cam: Cam, servos: Dict[Tuple[str, str], Servo] = None, verbose: bool = False
    ):
        self.cam = cam
        self.servos = servos if servos is not None else {}
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        self._cam_in_q = Queue()
        self._cam_out_q = Queue()
        self._servo_in_qs = {k: Queue() for k in self.servos.keys()}
        self._cam_thread = Thread(target=self._cam_worker, name='cam_worker', daemon=False)
        self._servo_threads = [
            Thread(target=self._servo_worker, kwargs=dict(servo_name=sn), daemon=True)
            for sn in self.servos.keys()
        ]

        self._cam_thread.start()
        sleep(Platform.CAM_RES_POLL_TIMEOUT)  # initial sleep for cam setup before servos start

        for st in self._servo_threads:
            st.start()

    def __del__(self):
        self._cam_in_q.join()
        self._cam_out_q.join()

    def _cam_worker(self):
        keep_alive = True
        while keep_alive:
            args, kwargs, keep_alive = self._cam_in_q.get()
            self._logger.info(f'Starting recording: args={args}, kwargs={kwargs}')
            res = self.cam.record(*args, **kwargs)
            self._logger.info('Recording done.')
            self._cam_in_q.task_done()
            self._cam_out_q.put(res)

    def _servo_worker(self, servo_name: Tuple[str, str]):
        while True:
            args, kwargs = self._servo_in_qs[servo_name].get()
            self.servos[servo_name].execute_sequence(*args, **kwargs)
            self._servo_in_qs[servo_name].task_done()

    def poll_cam_result(self):
        while True:
            try:
                return self._cam_out_q.get(timeout=self.CAM_RES_POLL_TIMEOUT)
            except Empty:
                pass

    def start_recording(self, keep_alive: bool = False, *args, **kwargs):
        """
        Start recording on `self.cam` with the given arguments.

        :param keep_alive: Whether to keep the camera thread alive after this
                           recording concludes. This prevents the main thread
                           from exiting.
        :param args: arguments passed on to `self.cam.record()`
        :param kwargs: keyword arguments passed on to `self.cam.record()`
        """
        self._cam_in_q.put((args, kwargs, keep_alive))

    def submit_servo_sequence(self, servo_name: Tuple[str, str], *args, **kwargs):
        """
        Submit a servo operation sequence to the servo with name `servo_name`.
        Execution will terminate after the cam worker thread is ended.

        :param servo_name: The name of the servo as given in `self.servos`.
        :param args: arguments passed on to the `execute_sequence` function of the requested servo.
        :param kwargs: keyword arguments passed on the the `execute_sequence` function of the requested servo.
        """
        self._servo_in_qs[servo_name].put((args, kwargs))
