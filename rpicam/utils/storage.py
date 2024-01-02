#!/usr/bin/env python3
from typing import List
from pathlib import Path
from tempfile import TemporaryDirectory
from abc import ABC

from rpicam.utils.logging_utils import get_logger
from rpicam.utils.callback_handler import CallbackHandler
from rpicam.cams.callbacks import ExecPoint, Callback


class CameraStorageMixin(ABC):
    def __init__(
        self,
        verbose: bool = False,
        tmpdir: Path = None,
        callbacks: List[Callback] = (),
    ) -> None:
        if tmpdir is None:
            self._tmpdir_holder = TemporaryDirectory(prefix=self.TMPDIR_PREFIX)
            self._tmpdir = Path(str(self._tmpdir_holder.name))
        else:
            self._tmpdir = Path(str(tmpdir))
        self._logger = get_logger(self.__class__.__name__, verb=verbose)
        self._cbh = CallbackHandler(callbacks)
        self._cbh.execute_callbacks(ExecPoint.BEFORE_INIT)
