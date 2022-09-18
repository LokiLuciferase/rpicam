from typing import Optional, Union, List
from datetime import datetime, timedelta
from time import sleep, time
from pathlib import Path
import shutil

import ffmpeg

from rpicam.cams.cam import Cam
from rpicam.utils.stack_encoder import StackEncoder
from rpicam.cams.callbacks import ExecPoint, Callback


class TimelapseCam(Cam):

    DEFAULT_SLEEP_DUR = 1  # sec
    MAX_CONSEQ_OVERTIME_TIL_ERR = 3
    TMPDIR_PREFIX = 'rpicam-timelapse-'

    def __init__(
        self,
        verbose: bool = False,
        tmpdir: Path = None,
        capture_failover_strategy: str = 'skip',
        hvflip: bool = False,
        callbacks: List[Callback] = (),
        # picamera settings
        *args,
        **kwargs,
    ):
        super().__init__(
            verbose=verbose,
            tmpdir=tmpdir,
            hvflip=hvflip,
            callbacks=callbacks,
            *args,
            **kwargs,
        )
        self._capture_failover_strategy = capture_failover_strategy
        self._latest_frame_file: Optional[Path] = None
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_INIT)
        self._conseq_overtime_count = 0

    def _capture_frame(self, stack_dir: Path, *args, **kwargs):
        """
        Captures a single frame for the timelapse stack.

        :param stack_dir: The save directory of the created image.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return:
        """
        self._cbh.execute_callbacks(loc=ExecPoint.BEFORE_FRAME_CAPTURE, cam=self.cam)
        file_path = stack_dir / f'{datetime.now().timestamp()}.png'
        self.cam.capture_file(str(file_path), *args, **kwargs)
        if not file_path.is_file():
            if self._capture_failover_strategy == 'heal' and self._latest_frame_file is not None:
                shutil.copy(self._latest_frame_file, file_path)
            elif self._capture_failover_strategy == 'skip':
                pass
            elif self._capture_failover_strategy == 'raise':
                self._cbh.raise_with_callbacks(RuntimeError(f'Could not capture frame: {file_path}'))
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_FRAME_CAPTURE, cam=self.cam)

    def _record_stack(
        self,
        t_start: datetime,
        sec_per_frame: int,
        duration: timedelta = None,
        t_end: datetime = None,
        *args,
        **kwargs,
    ) -> Path:
        """
        Captures a stack of images to be concatenated into a timelapse video.

        :param t_start: Start time. Will sleep until this time to record the stack.
        :param sec_per_frame: Number of seconds between captured images
        :param duration: Duration of timelapse. Create new images until this time passes.
        :param t_end: Alternatively, pass end time directly.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return:
        """
        self._cbh.execute_callbacks(loc=ExecPoint.BEFORE_STACK_CAPTURE)
        self._logger.info('Setting up timelapse imaging.')
        if duration is not None and t_end is not None:
            self._logger.warn('Ignoring `t_end` as `duration` was also supplied.')
        elif duration is None and t_end is None:
            missing_arg = 'Must supply either `duration` or `t_end` must be supplied.'
            self._logger.error(missing_arg)
            self._cbh.raise_with_callbacks(RuntimeError(missing_arg))
        if duration is not None:
            t_end = t_start + duration

        # sleep until starting
        while t_start > datetime.now():
            sleep(TimelapseCam.DEFAULT_SLEEP_DUR)

        # create individual images in tmp_dir/stack_dir_name
        stack_dir_name = str(t_start.timestamp())
        stack_dir = self._tmpdir / stack_dir_name
        stack_dir.mkdir()
        now = datetime.now()
        self._logger.info(f'Begin timelapse imaging.')
        while t_end > now:
            t0 = time()
            self._capture_frame(stack_dir=stack_dir, *args, **kwargs)
            t1 = time()
            capture_dur = t1 - t0
            sleeptime = sec_per_frame - capture_dur
            if sleeptime < 0:
                overtime_err = (
                    f'sec_per_frame={sec_per_frame} but frame took {round(capture_dur, 2)} sec.'
                )

                if self._conseq_overtime_count >= TimelapseCam.MAX_CONSEQ_OVERTIME_TIL_ERR:
                    self._cbh.raise_with_callbacks(RuntimeError(overtime_err))
                else:
                    self._logger.warning(overtime_err)
                    self._conseq_overtime_count += 1
            else:
                self._conseq_overtime_count = 0
                sleep(sleeptime)
            now = datetime.now()
        self._logger.info('Finished timelapse imaging.')
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_STACK_CAPTURE)
        return stack_dir

    def record(
        self,
        outfile: Path,
        fps: int = 24,
        sec_per_frame: int = 10,
        t_start: datetime = None,
        duration: timedelta = None,
        t_end: datetime = None,
        wait_for_encoder: bool = True,
        *args,
        **kwargs,
    ) -> Path:
        """
        Records a timelapse video using picamera and ffmpeg.

        :param outfile: The path at which to create the video. Optional, else created in tmpdir.
        :param fps: The frames per second of the to be created video.
        :param sec_per_frame: Number of seconds between captured images
        :param t_start: Start time - if given, sleep until this time
        :param duration: Duration of timelapse. Create new images until this time passes.
        :param t_end: Alternatively, pass end time directly.
        :param wait_for_encoder: Whether to wait after capture for the video to be encoded. 
                                 Else, immediately return the Path at which it will be created.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return: The path to the created video file.
        """
        self._cbh.execute_callbacks(loc=ExecPoint.BEFORE_RECORD)
        if t_start is None:
            t_start = datetime.now()
        elif t_start < datetime.now():
            raise RuntimeError('Recording start datetime is in the past.')
        else:
            pass
        stack_dir = self._record_stack(
            sec_per_frame=sec_per_frame,
            t_start=t_start,
            duration=duration,
            t_end=t_end,
            *args,
            **kwargs,
        )
        encoder = StackEncoder(callbacks=self._cbh.get_callbacks(exec_at=ExecPoint.AFTER_CONVERT), stack_dir=stack_dir, fps=fps, outfile=outfile)
        encoder.start()
        if wait_for_encoder:
            self._logger.info('Waiting for encoder to finish.')
            encoder.join()
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_RECORD)
        return outfile
