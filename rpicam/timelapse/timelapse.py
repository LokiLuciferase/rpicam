from typing import Optional, Union
from datetime import datetime, timedelta
from time import sleep, time
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory

from picamera import PiCamera, Color
import ffmpeg

from rpicam.utils import get_logger


class TimelapseCam:

    DEFAULT_SLEEP_DUR = 1  # sec
    TMPDIR_PREFIX = 'rpicam-timelapse-'
    DT_OVERLAY_FMT = '%Y-%m-%dT%H:%M%S'

    def __init__(
        self,
        *args,
        verbose: bool = False,
        tmpdir: Path = None,
        capture_failover_strategy: str = 'heal',
        camera_rotation: int = 180,
        dt_overlay: bool = True,
        # picamera settings
        **kwargs,
    ):
        self._cam = PiCamera(*args, **kwargs)
        self._cam.rotation = camera_rotation
        sleep(2)
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        self._capture_failover_strategy = capture_failover_strategy
        self.latest_frame_file: Optional[Path] = None
        self._do_dt_overlay = dt_overlay
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=TimelapseCam.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))

    def __del__(self):
        self._cam.close()

    def _annotate_frame(self, text: str = None):
        """
        Set or unset annotation of camera capture.

        :param text: The text to set. If None, clear annnotations.
        :param return:
        """
        if text is not None:
            self._cam.annotate_background = Color('black')
        else:
            self._cam.annotate_background = None
        self._cam.annotate_text = text

    def _capture_frame(self, stack_dir: Path, *args, **kwargs):
        """
        Captures a single frame for the timelapse stack.

        :param stack_dir: The save directory of the created image.
        :param args: passed to PiCamera().capture()
        :param kwargs: passed to PiCamera().capture()
        :return:
        """
        now = datetime.now()
        file_path = stack_dir / f'{now.timestamp()}.png'
        if self._do_dt_overlay:
            self._annotate_frame(text=now.strftime(TimelapseCam.DT_OVERLAY_FMT))
        self._cam.capture(str(file_path), *args, **kwargs)
        if not file_path.is_file():
            if self._capture_failover_strategy == 'heal' and self.latest_frame_file is not None:
                shutil.copy(self.latest_frame_file, file_path)
            elif self._capture_failover_strategy == 'skip':
                pass
            elif self._capture_failover_strategy == 'raise':
                raise RuntimeError(f'Could not capture frame: {file_path}')

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
        if duration is not None and t_end is not None:
            self._logger.warn('Ignoring `t_end` as `duration` was also supplied.')
        elif duration is None and t_end is None:
            missing_arg = 'Must supply either `duration` or `t_end` must be supplied.'
            self._logger.error(missing_arg)
            raise RuntimeError(missing_arg)
        if duration is not None:
            t_end = t_start + duration

        self._logger.info('Setting up timelapse imaging.')
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
                raise RuntimeError(
                    f'Cannot capture: sec_per_frame={sec_per_frame} '
                    f'but processing frame took {capture_dur}!'
                )
            sleep(sleeptime)
            now = datetime.now()
        self._logger.info('Finished timelapse imaging.')
        return stack_dir

    def _convert_stack_to_video(self, stack_dir: Path, fps: int, outfile: Path = None) -> Path:
        """
        Convert a stack of images to a video file using ffmpeg-python.

        :param stack_dir: The directory containing images in sorted order.
        :param fps: The frames per second of the to be created video.
        :param outfile: The path at which to create the video. Optional, else created in stack_dir.
        :return: The path of the created video file.
        """
        self._logger.info('Begin video conversion.')
        outfile = Path(str(outfile)) if outfile is not None else stack_dir / 'out.mp4'
        (
            ffmpeg.input(f'{str(stack_dir)}/*.png', pattern_type='glob', framerate=fps)
            .output(str(outfile), pix_fmt='yuv420p')
            .run(capture_stdout=False, capture_stderr=False)
        )
        if not outfile.is_file():
            raise RuntimeError('Error during processing: output file not found.')
        for f in stack_dir.glob('*.png'):
            f.unlink()
        self._logger.info('Finished video conversion.')
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
    ):
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
        stack_dir = self._record_stack(
            sec_per_frame=sec_per_frame,
            t_start=t_start,
            duration=duration,
            t_end=t_end,
            *args,
            **kwargs,
        )
        return self._convert_stack_to_video(stack_dir=stack_dir, fps=fps, outfile=outfile)


if __name__ == '__main__':
    tc = TimelapseCam()
    tc.record(fps=10, duration=timedelta(seconds=120), sec_per_frame=2, outfile='/home/pi/test.mp4')
