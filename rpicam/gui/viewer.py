from typing import Union
from pathlib import Path
from queue import Queue
from threading import Thread
import tkinter as tk

from PIL import ImageTk, Image


class Viewer:

    TITLE = 'RPiCam Viewer'

    def __init__(self):
        self._root = None
        self._live_view_panel = None

    @staticmethod
    def view_image(path: Union[str, Path]):
        """
        Display a single still image using a Tk GUI.

        :param path: the path to the image to display.
        :returns: None
        """
        root = tk.Tk()
        root.title(Viewer.TITLE)
        img = Image.open(path)
        # width, height = img.size
        img = ImageTk.PhotoImage(img)
        label = tk.Label(image=img)
        label.pack(side='left')
        # canvas = tk.Canvas(root, width=width, height=height)
        # canvas.pack()
        # canvas.create_image(0, 0, anchor=tk.NW, image=img)
        root.mainloop()

    def _image_queue_consumer(self, queue: Queue):
        if self._root is None:
            raise RuntimeError('An active Tk root is required.')
        while True:
            img = queue.get()
            img = ImageTk.PhotoImage(img)
            if self._live_view_panel is None:
                self._live_view_panel = tk.Label(image=img)
                self._live_view_panel.pack(side='left')
            else:
                self._live_view_panel.configure(image=img)
                self._live_view_panel.image = img
            queue.task_done()

    def view_image_queue(self, queue: Queue):
        """
        Display Images from the given queue in a Tk GUI window.

        :param queue: A Queue containing PIL images.
        :return: None
        """
        self._root = tk.Tk()
        self._root.title(Viewer.TITLE)
        Thread(target=self._image_queue_consumer, args=(queue,), daemon=True).start()
        self._root.mainloop()
