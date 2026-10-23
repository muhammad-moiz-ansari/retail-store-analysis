"""Checks for the laptop/phone live camera switch."""

import numpy as np

from . import cli


class FakeCapture:
    def __init__(self, source, opens=True):
        self.source, self.opens, self.released = source, opens, False

    def isOpened(self):
        return self.opens

    def read(self):
        return True, self.source

    def release(self):
        self.released = True


def _switch(monkeypatch, keys, dead=()):
    pressed = iter(keys)
    monkeypatch.setattr(cli.cv2, "VideoCapture", lambda source: FakeCapture(source, source not in dead))
    monkeypatch.setattr(cli.cv2, "waitKey", lambda _: next(pressed))
    return cli.CameraSwitch({"laptop": "0", "phone": "http://phone:4747/video"}, "laptop")


def test_s_switches_camera_and_q_stops(monkeypatch):
    cam = _switch(monkeypatch, [-1, ord("s"), ord("s"), ord("q")])
    laptop, laptop_reader = cam.cap, cam.reader
    assert cam.read() == (True, 0)  # digit sources open as camera indices
    assert cam.read() == (True, "http://phone:4747/video")
    laptop_reader.join(1)
    assert laptop.released
    assert cam.read() == (True, 0)
    assert cam.read() == (False, None)


def test_unreachable_phone_keeps_laptop_feed(monkeypatch):
    cam = _switch(monkeypatch, [ord("s")], dead={"http://phone:4747/video"})
    assert cam.read() == (True, 0)
    assert cam.name == "laptop" and not cam.cap.released


def test_reader_drains_stream_and_releases_on_stop(monkeypatch):
    cam = _switch(monkeypatch, [-1])
    reader, laptop = cam.reader, cam.cap
    assert cam.read() == (True, 0)
    cam.release()
    reader.join(1)
    assert laptop.released and not reader.is_alive()


def test_raw_feed_records_every_camera_frame(monkeypatch, tmp_path):
    frame = np.zeros((48, 64, 3), np.uint8)
    monkeypatch.setattr(FakeCapture, "read", lambda self: (True, frame))
    monkeypatch.setattr(FakeCapture, "get", lambda self, prop: 0, raising=False)
    monkeypatch.setattr(cli.cv2, "VideoCapture", lambda source: FakeCapture(source))
    monkeypatch.setattr(cli.cv2, "waitKey", lambda _: -1)
    cam = cli.CameraSwitch({"laptop": "0", "phone": "1"}, "laptop", tmp_path / "live.raw.mp4")
    cam.read()
    cam.release()
    cam.reader.join(1)
    assert (tmp_path / "live.raw.mp4").stat().st_size > 0
