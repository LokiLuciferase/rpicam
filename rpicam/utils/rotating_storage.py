#!/usr/bin/env python3

import shutil
from datetime import datetime
from pathlib import Path

from rpicam.utils.logging_utils import get_logger


class RotatingStorage:
    """
    Provide rotating storage for long running camera jobs. When storage
    crosses threshold, delete oldest file in the job directory.
    """
    def __init__(
        self,
        storage_dir: Path,
        file_prefix: str = 'file',
        file_ext: str = '.mp4',
        rotate_fill_perc: int = 90,
    ):
        self.storage_dir = Path(str(storage_dir))
        self._file_prefix = file_prefix
        self._file_ext = file_ext
        self._rotate_fill_perc = rotate_fill_perc
        self._logger = get_logger(self.__class__.__name__, verb=True)

        if self.storage_dir.is_file():
            raise RuntimeError(f'Storage dir is a file: {storage_dir}')
        self.storage_dir.mkdir(exist_ok=True)

    def _get_disk_fill_perc(self):
        total, used, free = shutil.disk_usage(self.storage_dir)
        return round(used / total * 100, 1)

    def _rotate_oldest_element(self):
        oldest = sorted([x for x in self.storage_dir.glob(f'{self._file_prefix}_*{self._file_ext}')])[0]
        oldest.unlink()
        self._logger.info(f'Rotated out oldest file: {oldest.name}')

    def _get_new_element_name(self):
        unixtime = str(datetime.now().timestamp()).replace('.', '_')
        return str(self.storage_dir / f'{self._file_prefix}_{unixtime}{self._file_ext}')

    def __iter__(self):
        return self

    def __next__(self):
        """
        Iterator to get a new file name in the job storage directory while possibly rotating
        out existing files if storages gets too full.
        """
        while self._get_disk_fill_perc() > self._rotate_fill_perc:
            try:
                self._rotate_oldest_element()
            except IndexError:
                break
        if self._get_disk_fill_perc() > self._rotate_fill_perc:
            still_too_full_msg = 'Could not free up enough storage.'
            self._logger.error(still_too_full_msg)
            raise RuntimeError(still_too_full_msg)
        return self._get_new_element_name()


if __name__ == '__main__':
    import os
    rs = RotatingStorage('/tmp/rotating', file_ext='.txt', rotate_fill_perc=7)
    for i in range(10):
        d = next(rs)
        os.system(f'fallocate --length 100M {d}')
