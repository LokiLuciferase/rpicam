from typing import Optional, Union, List
from datetime import datetime, timedelta
from time import sleep, time
from pathlib import Path
import shutil

import ffmpeg

from rpicam.cams.cam import Cam
from rpicam.cams.callbacks import ExecPoint, Callback


class TimelapseCam(Cam):

    DEFAULT_SLEEP_DUR = 1  # sec
    TMPDIR_PREFIX = 'rpicam-timelapse-'

    def __init__(
        self,
        verbose: bool = False,
        tmpdir: Path = None,
        capture_failover_strategy: str = 'skip',
        camera_rotation: int = 0,
        callbacks: List[Callback] = (),
        # picamera settings
        *args,
        **kwargs,
    ):
        super().__init__(
            verbose=verbose,
            tmpdir=tmpdir,
            camera_rotation=camera_rotation,
            callbacks=callbacks,
            *args,
            **kwargs,
        )
        self._capture_failover_strategy = capture_failover_strategy
        self._latest_frame_file: Optional[Path] = None
        self._execute_callbacks(loc=ExecPoint.AFTER_INIT)

    def _capture_frame(self, stack_dir: Path, *args, **kwargs):
        """
        Captures a single frame for the timelapse stack.

        :param stack_dir: The save directory of the created image.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return:
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_FRAME_CAPTURE, cam=self.cam)
        file_path = stack_dir / f'{datetime.now().timestamp()}.png'
        self.cam.capture(str(file_path), *args, **kwargs)
        if not file_path.is_file():
            if self._capture_failover_strategy == 'heal' and self._latest_frame_file is not None:
                shutil.copy(self._latest_frame_file, file_path)
            elif self._capture_failover_strategy == 'skip':
                pass
            elif self._capture_failover_strategy == 'raise':
                self._raise_with_callbacks(RuntimeError(f'Could not capture frame: {file_path}'))
        self._execute_callbacks(loc=ExecPoint.AFTER_FRAME_CAPTURE, cam=self.cam)

    def _record_stack(
        self,
        sec_per_frame: int = 10,
        t_start: datetime = datetime.now(),
        duration: timedelta = None,
        t_end: datetime = None,
        *args,
        **kwargs,
    ) -> Path:
        """
        Captures a stack of images to be concatenated into a timelapse video.

        :param sec_per_frame: Number of seconds between captured images
        :param t_start: Start time - if given, sleep until this time
        :param duration: Duration of timelapse. Create new images until this time passes.
        :param t_end: Alternatively, pass end time directly.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return:
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_STACK_CAPTURE)
        self._logger.info('Setting up timelapse imaging.')
        if duration is not None and t_end is not None:
            self._logger.warn('Ignoring `t_end` as `duration` was also supplied.')
        elif duration is None and t_end is None:
            missing_arg = 'Must supply either `duration` or `t_end` must be supplied.'
            self._logger.error(missing_arg)
            self._raise_with_callbacks(RuntimeError(missing_arg))
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
                self._raise_with_callbacks(
                    RuntimeError(
                        f'Cannot capture: sec_per_frame={sec_per_frame} '
                        f'but processing frame took {round(capture_dur, 5)} sec.'
                    )
                )
            sleep(sleeptime)
            now = datetime.now()
        self._logger.info('Finished timelapse imaging.')
        self._execute_callbacks(loc=ExecPoint.AFTER_STACK_CAPTURE)
        return stack_dir

    def _convert_stack_to_video(self, stack_dir: Path, fps: int, outfile: Path = None) -> Path:
        """
        Convert a stack of images to a video file using ffmpeg-python.

        :param stack_dir: The directory containing images in sorted order.
        :param fps: The frames per second of the to be created video.
        :param outfile: The path at which to create the video. Optional, else created in stack_dir.
        :return: The path of the created video file.
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_CONVERT, stack_dir=stack_dir)
        self._logger.info('Begin video conversion.')
        outfile = Path(str(outfile)) if outfile is not None else stack_dir / 'out.mp4'
        if outfile.is_file():
            outfile.unlink()
        (
            ffmpeg.input(f'{str(stack_dir)}/*.png', pattern_type='glob', framerate=fps)
            .output(str(outfile), pix_fmt='yuv420p')
            .run(quiet=True)
        )
        if not outfile.is_file():
            self._raise_with_callbacks(
                RuntimeError('Error during processing: output file not found.')
            )
        for f in stack_dir.glob('*.png'):
            f.unlink()
        self._logger.info('Finished video conversion.')
        self._execute_callbacks(loc=ExecPoint.AFTER_CONVERT, outfile=outfile)
        return outfile

    def record(
        self,
        fps: int = 24,
        sec_per_frame: int = 10,
        t_start: datetime = datetime.now(),
        duration: timedelta = None,
        t_end: datetime = None,
        outfile: Union[Path, str] = None,
        *args,
        **kwargs,
    ) -> Path:
        """
        Records a timelapse video using picamera and ffmpeg.

        :param fps: The frames per second of the to be created video.
        :param sec_per_frame: Number of seconds between captured images
        :param t_start: Start time - if given, sleep until this time
        :param duration: Duration of timelapse. Create new images until this time passes.
        :param t_end: Alternatively, pass end time directly.
        :param outfile: The path at which to create the video. Optional, else created in tmpdir.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return: The path to the created video file.
        """
        self._execute_callbacks(loc=ExecPoint.BEFORE_RECORD)
        stack_dir = self._record_stack(
            sec_per_frame=sec_per_frame,
            t_start=t_start,
            duration=duration,
            t_end=t_end,
            *args,
            **kwargs,
        )
        ret = self._convert_stack_to_video(stack_dir=stack_dir, fps=fps, outfile=outfile)
        self._execute_callbacks(loc=ExecPoint.AFTER_RECORD, ret=ret)
        return ret

