#!/usr/bin/env python3

from pathlib import Path
from typing import List
from multiprocessing import Process
from rpicam.utils.callback_handler import CallbackHandler

import ffmpeg
from rpicam.cams.callbacks import ExecPoint, Callback
from rpicam.utils.logging_utils import get_logger


class StackEncoder(Process):
    def __init__(self, callbacks: List[Callback], stack_dir: Path, fps: int, outfile: Path):
        super().__init__()
        self._cbh = CallbackHandler(callbacks)
        self._stack_dir = stack_dir
        self._fps = fps
        self._outfile = outfile
        self._logger = get_logger(initname=self.__class__.__name__)

    def run(self):
        """
        Convert a stack of images to a video file using ffmpeg-python.
        """
        self._cbh.execute_callbacks(loc=ExecPoint.BEFORE_CONVERT, stack_dir=self._stack_dir)
        self._logger.info('Begin video conversion.')
        outfile = Path(str(self._outfile)) if self._outfile is not None else self._stack_dir / 'out.mp4'
        if outfile.is_file():
            outfile.unlink()
        (
            ffmpeg.input(f'{str(self._stack_dir)}/*.png', pattern_type='glob', framerate=self._fps)
            .output(str(outfile), pix_fmt='yuv420p')
            .run(quiet=False)
        )
        if not outfile.is_file():
            self._cbh.raise_with_callbacks(
                RuntimeError('Error during processing: output file not found.')
            )
        for f in self._stack_dir.glob('*.png'):
            f.unlink()
        self._logger.info('Finished video conversion.')
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_CONVERT, outfile=outfile)
