#!/usr/bin/env python3

import os
import json
from pprint import pformat
from pathlib import Path
from typing import Union, List, Hashable, Optional, Any, Dict
from multiprocessing import Lock

from rpicam.utils.logging_utils import get_logger


class State:

    STATE_FILE_NAME = 'rpicam-state.json'

    def __init__(self, lock: Lock = None):
        tmpdir = os.getenv('TMPDIR', '/tmp')
        self.sfp = Path(tmpdir) / self.STATE_FILE_NAME
        self._logger = get_logger(self.__class__.__name__, verb=True)
        if not self.sfp.is_file():
            with open(self.sfp, 'w') as fout:
                json.dump({}, fout)
            self.sfp.touch(exist_ok=True)
        self.lock = lock

    def __repr__(self):
        return pformat(json.loads(self.sfp.read_text()))

    def __getitem__(self, k: Union[Hashable, List[Hashable]]) -> Optional[Any]:
        """
        Get from the State with one or multiple keys. If the latter, attempt to
        find in nested dictionary. If key is not found (but structure is correct), return
        None.

        :param k: the list of keys or single key.
        :returns: the values at the given key(s).
        """
        d = json.loads(self.sfp.read_text())
        if isinstance(k, str):
            k = [k]
        k = [str(x) for x in k]
        prev_k = None
        while len(k):
            if not isinstance(d, dict):
                structure_err = f'Faulty structure: Value of "{prev_k}" is not a dict.'
                self._logger.error(structure_err)
                raise KeyError(structure_err)
            d = d.get(k[0], {})
            prev_k = k.pop(0)
        if d == {}:
            d = None
        return d

    def __setitem__(self, k: Union[Hashable, List[Hashable]], v):
        """
        Attempt to set the given value in a (possibly nested) key.
        If any of the given keys but the rightmost does not point
        to a dictionary, either create the dictionary or, if it
        points to a non-dictionary, raise an error.

        :param k: the list of keys or single key.
        :param v: the value to set at the given key(s).
        """
        if self.lock is not None:
            self.lock.acquire()

        d = json.loads(self.sfp.read_text())
        if isinstance(k, str):
            k = [k]
        k = [str(x) for x in k]

        subd = d
        for key in k[:-1]:
            new_subd = subd.setdefault(key, {})
            if not isinstance(new_subd, dict):
                self._logger.warning(f'Overwriting State structure when writing keys!')
                subd[key] = {}
            else:
                subd[key] = new_subd
            subd = subd[key]
        subd[k[-1]] = v

        with open(self.sfp, 'w') as fout:
            json.dump(d, fout, indent=2)

        if self.lock is not None:
            self.lock.release()


if __name__ == '__main__':
    s = State()
    s['uuu'] = 2
    s[1, 2, 3, 4, 5] = 6
    print(s)
