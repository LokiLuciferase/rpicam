from pathlib import Path
from subprocess import call

from rpicam.utils.storage import CameraStorageMixin


class FakeCam:
    def __init__(self) -> None:
        self.pre_callback = None


class TermuxVideoCam(CameraStorageMixin):
    def __init__(self, hvflip: bool = False, resolution = False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cam = FakeCam()
    def capture_single_frame(self, file_path: Path):
        rslt = call(['termux-camera-photo', '-c', '0', str(file_path)])
