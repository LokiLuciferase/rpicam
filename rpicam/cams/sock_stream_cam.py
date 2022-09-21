#!/usr/bin/env python3
import time
import socket

from picamera2.encoders import H264Encoder
from picamera2.outputs import FfmpegOutput

from rpicam.cams.cam import VideoCam
from rpicam.cams.callbacks import ExecPoint


class SockStreamCam(VideoCam):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._encoder = H264Encoder(1000000)
        self.cam.encoder = self._encoder

    def _record_to_udp_sock(self, addr: str, port: int):
        self._logger.info(f"Starting recording to UDP socket udp://{addr}:{port} - hit Ctrl-C to stop.")
        self.cam.start_recording(self._encoder, FfmpegOutput(f'-loglevel error -f mpegts udp://{addr}:{port}'))
        while True:
            try:
                time.sleep(1)
            except KeyboardInterrupt:
                break
        self.cam.stop_recording()
        self._logger.info("Recording finished.")

    def record(self, addr: str = '232.255.23.23', port: int = 10001):
        self._cbh.execute_callbacks(loc=ExecPoint.BEFORE_RECORD)
        self._record_to_udp_sock(addr=addr, port=port)
        self._cbh.execute_callbacks(loc=ExecPoint.AFTER_RECORD)
