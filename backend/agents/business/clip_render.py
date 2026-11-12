"""Clip Review rendering (Ruhab, team plan C5): cut a 10–20 s alert clip and draw track boxes.

Reads a recording plus the CV run's `<output>.detections.json` (frame, timestamp in seconds from
the recording start, people[] with track_id, bbox, role, role_confidence) and writes a short MP4
with role-coloured boxes. Tracks involved in the event are drawn thicker. Synthetic sources get a
visible banner. OpenCV is imported lazily so the rest of the business package needs no CV stack.

`resolve_video` maps an opaque `video_ref` to a file under one trusted root and refuses anything
that would escape it, so a client can never choose an arbitrary file.
"""
import json
from bisect import bisect_right
from pathlib import Path

from .clip_review import ClipSegment

ROLE_COLORS = {'employee': (0, 180, 255), 'customer': (255, 180, 0), 'unknown': (160, 160, 160)}  # BGR
MAX_DETECTION_GAP_S = 0.75


def resolve_video(video_ref, root, suffixes=('.mp4', '.mov', '.avi', '.mkv')):
    root = Path(root).resolve()
    for suffix in suffixes:
        for candidate in (root / f'{video_ref}{suffix}', root / f'{video_ref}{suffix.upper()}'):
            resolved = candidate.resolve()
            if resolved.parent != root and root not in resolved.parents:
                raise PermissionError('Video reference escapes the recording root')
            if resolved.is_file():
                return resolved
    raise FileNotFoundError(f'No recording for {video_ref}')


def load_detections(path):
    rows = json.loads(Path(path).read_text(encoding='utf-8'))
    return sorted(rows, key=lambda r: r['timestamp'])


def _people_at(detections, times, t):
    index = bisect_right(times, t) - 1
    if index < 0 or t - times[index] > MAX_DETECTION_GAP_S:
        return ()
    return detections[index]['people']


def render_review_clip(video_path, detections, segment: ClipSegment, out_path, *, highlight_tracks=(),
                       title='', synthetic=False):
    """Write the clip and return a summary dict (frames written, fps, frames with boxes)."""
    import cv2  # lazy: only clip rendering needs OpenCV

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        raise FileNotFoundError('Cannot open recording')
    fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    width, height = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    capture.set(cv2.CAP_PROP_POS_MSEC, segment.offset_start_s * 1000)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    writer = cv2.VideoWriter(str(out_path), cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))
    times = [d['timestamp'] for d in detections]
    highlight = set(highlight_tracks)
    written = boxed = 0
    try:
        while True:
            ok, frame = capture.read()
            t = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000 - 1 / fps
            if not ok or t >= segment.offset_end_s:
                break
            people = _people_at(detections, times, t)
            for person in people:
                x1, y1, x2, y2 = map(int, person['bbox'])
                color = ROLE_COLORS.get(person.get('role'), ROLE_COLORS['unknown'])
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 4 if person['track_id'] in highlight else 2)
                label = f"{person.get('role', 'unknown')} #{person['track_id']}"
                if person.get('role_confidence') is not None:
                    label += f" {person['role_confidence']:.0%}"
                cv2.putText(frame, label, (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            boxed += bool(people)
            header = f'{title}  t={t:.1f}s' if title else f't={t:.1f}s'
            cv2.putText(frame, header, (10, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            if synthetic:
                cv2.rectangle(frame, (0, height - 28), (width, height), (0, 0, 160), -1)
                cv2.putText(frame, 'SYNTHETIC FIXTURE - not real store footage', (10, height - 9),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            writer.write(frame)
            written += 1
    finally:
        capture.release()
        writer.release()
    if written == 0:
        out_path.unlink(missing_ok=True)
        raise ValueError('Clip segment produced no frames')
    return {'frames': written, 'fps': fps, 'frames_with_boxes': boxed, 'path': str(out_path)}
