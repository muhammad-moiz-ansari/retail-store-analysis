"""Acquisition only: Track B authorizes capacity and persists these lifecycle signals."""

import queue
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse

from .cv_contracts import Signal
from .frames import Frame


@dataclass
class LiveFrame:
    session_id: str
    anchor: datetime
    frame: Frame


def rtsp_frames(source):
    import av
    # Decoder interrupt timeout bounds stop/reconnect latency, including failed reads.
    with av.open(source, options={"rtsp_transport": "tcp"}, timeout=(5.0, 5.0)) as container:
        if not container.streams.video:
            raise ValueError("RTSP source contains no video")
        for decoded in container.decode(container.streams.video[0]):
            yield decoded.to_ndarray(format="bgr24")


class LiveSource:
    def __init__(self, camera_id, source, reader=rtsp_frames, clock=time.monotonic):
        if urlparse(source).scheme not in {"rtsp", "rtsps"}:
            raise ValueError("Live sources must be configured RTSP URLs")
        self.camera_id, self.source, self.reader, self.clock = camera_id, source, reader, clock
        self.latest = queue.Queue(maxsize=1)
        self.signals = queue.Queue()
        self.stop_event = threading.Event()
        self.thread = None

    def start(self):
        if self.thread is not None:
            raise RuntimeError("Source already started")
        self.thread = threading.Thread(target=self._acquire, name=f"interaction-{self.camera_id}", daemon=True)
        self.thread.start()

    def _acquire(self):
        attempt = 0
        while not self.stop_event.is_set():
            session = uuid.uuid4().hex
            anchor = datetime.now(timezone.utc)
            origin = self.clock()
            started, seconds, dropped = False, None, 0
            try:
                for image in self.reader(self.source):
                    if self.stop_event.is_set():
                        break
                    seconds = self.clock() - origin
                    if not started:
                        self.signals.put(Signal(kind="session_started", camera_id=self.camera_id,
                                                session_id=session, utc_time=anchor))
                        started = True
                    packet = LiveFrame(session, anchor, Frame(image, seconds, dropped))
                    try:
                        old = self.latest.get_nowait()
                        dropped = old.frame.skipped + 1
                        packet.frame.skipped = dropped
                    except queue.Empty:
                        dropped = 0
                    self.latest.put_nowait(packet)
                    if seconds >= 30:
                        attempt = 0
            except Exception:
                # Never include an RTSP URL or credentials in health/error output.
                self.signals.put(Signal(kind="acquisition_error", camera_id=self.camera_id,
                                        session_id=session, reason="connection_or_decode_failed",
                                        utc_time=datetime.now(timezone.utc)))
            finally:
                if started:
                    self.signals.put(Signal(kind="session_ended", camera_id=self.camera_id,
                        session_id=session, source_seconds=seconds,
                        reason="shutdown" if self.stop_event.is_set() else "disconnect",
                        utc_time=datetime.now(timezone.utc)))
            delay = min(30, 2 ** min(attempt, 5))
            attempt += 1
            self.stop_event.wait(delay)

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=11)
            if self.thread.is_alive():
                raise RuntimeError("Acquisition reader failed to respect its timeout")


def round_robin(sources, processor_factory, stop_event, rate=5.0):
    """One inference consumer. Caller starts sources after B's admission checks."""
    if rate <= 0:
        raise ValueError("Rate must be positive")
    processors, eligible = {}, {}
    while not stop_event.is_set():
        worked = False
        for source in sources:
            while True:
                try:
                    signal = source.signals.get_nowait()
                except queue.Empty:
                    break
                yield signal
                if signal.kind == "session_started":
                    eligible[source.camera_id] = signal.session_id
                elif signal.kind == "session_ended":
                    eligible.pop(source.camera_id, None)
                    processors.pop(source.camera_id, None)
            try:
                packet = source.latest.get_nowait()
            except queue.Empty:
                continue
            if eligible.get(source.camera_id) != packet.session_id:
                continue
            processor = processors.get(source.camera_id)
            if processor is None or processor.session_id != packet.session_id:
                processor = processor_factory(source.camera_id, packet.session_id, packet.anchor)
                processors[source.camera_id] = processor
            if processor.last_time is not None and packet.frame.seconds - processor.last_time < 1 / rate - 1e-8:
                continue
            worked = True
            yield processor.process(packet.frame)
        if not worked:
            stop_event.wait(0.01)
    for camera, processor in processors.items():
        yield Signal(kind="session_ended", camera_id=camera, session_id=processor.session_id,
                     source_seconds=processor.last_time, reason="shutdown")
