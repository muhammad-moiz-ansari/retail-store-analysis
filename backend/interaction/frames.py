"""PTS-preserving recorded-media decoding; no FPS-derived timestamp fallback."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class MediaError(RuntimeError):
    pass


@dataclass
class Frame:
    image: Any
    seconds: float
    skipped: int = 0


def recording_frames(path, rate=5.0, max_seconds=None):
    import av
    if not math.isfinite(rate) or rate <= 0:
        raise ValueError("Sampling rate must be finite and positive")
    if max_seconds is not None and (not math.isfinite(max_seconds) or max_seconds <= 0):
        raise ValueError("Maximum duration must be finite and positive")
    if not Path(path).is_file():
        raise MediaError("Recording does not exist")
    try:
        with av.open(str(path)) as container:
            if not container.streams.video:
                raise MediaError("No video stream")
            stream = container.streams.video[0]
            origin, previous, next_sample, skipped, count = None, None, 0.0, 0, 0
            for decoded in container.decode(stream):
                if decoded.pts is None or decoded.time_base is None:
                    raise MediaError("Missing source presentation timestamp")
                pts = float(decoded.pts * decoded.time_base)
                if not math.isfinite(pts) or (previous is not None and pts <= previous):
                    raise MediaError("Repeated or backward source presentation timestamp")
                previous = pts
                if origin is None:
                    origin = pts
                elapsed = pts - origin
                if max_seconds is not None and elapsed > max_seconds:
                    break
                if elapsed + 1e-8 < next_sample:
                    skipped += 1
                    continue
                yield Frame(decoded.to_ndarray(format="bgr24"), elapsed, skipped)
                count += 1
                skipped = 0
                next_sample = (math.floor((elapsed + 1e-8) * rate) + 1) / rate
            if not count:
                raise MediaError("Recording contains no decodable sampled frames")
    except MediaError:
        raise
    except (av.FFmpegError, OSError, ValueError) as exc:
        raise MediaError(f"Video decode failed ({type(exc).__name__})") from exc
