#!/usr/bin/env python3

from typing import List, Optional
from rpicam.cams.callbacks import Callback, ExecPoint


class CallbackHandler:
    def __init__(self, callbacks: List[Callback] = None):
        self._callbacks = {}
        callbacks = callbacks if callbacks is not None else []
        for cb in callbacks:
            self._callbacks.setdefault(cb.exec_at, []).append(cb)
        self._sort_callbacks()

    def _sort_callbacks(self):
        for k in self._callbacks.keys():
            self._callbacks[k] = sorted(self._callbacks[k], key=lambda x: x.priority, reverse=True)

    def add_callback(self, cb: Callback):
        self._callbacks.setdefault(cb.exec_at, []).append(cb)
        self._sort_callbacks()

    def get_callbacks(self, exec_at: ExecPoint) -> Optional[List[Callback]]:
        return self._callbacks.get(exec_at)

    def execute_callbacks(self, loc: ExecPoint, *args, **kwargs):
        """
        Run all callbacks associated with loc in order.

        :param loc: The execution point.
        :param args: passed on to Callbacks for the given loc.
        :param kwargs: passed on to Callbacks for the given loc.
        :return:
        """
        if loc in self._callbacks:
            for cb in self._callbacks[loc]:
                cb(*args, **kwargs)

    def raise_with_callbacks(self, exc: Exception):
        """
        Raise the given exception after passing it through all Callbacks registered to run on error.

        :param exc: The given exception.
        :return:
        """
        self.execute_callbacks(ExecPoint.ON_EXCEPTION, exc=exc)
        raise exc

