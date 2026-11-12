"""Clip rendering on a generated SYNTHETIC video. Skipped where OpenCV is not installed."""
import pytest

from .clip_render import load_detections, render_review_clip, resolve_video
from .clip_review import ClipSegment

cv2 = pytest.importorskip('cv2')
np = pytest.importorskip('numpy')


def make_video(path, seconds=30, fps=10, size=(160, 120)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*'mp4v'), fps, size)
    for _ in range(seconds * fps):
        writer.write(np.zeros((size[1], size[0], 3), dtype=np.uint8))
    writer.release()


def test_renders_a_bounded_clip_with_boxes(tmp_path):
    video = tmp_path / 'fixture-clip-01.mp4'
    make_video(video)
    detections = [{'frame': i, 'timestamp': i / 10, 'people': [
        {'track_id': 7, 'bbox': [20, 20, 60, 100], 'role': 'employee', 'role_confidence': 0.9},
        {'track_id': 9, 'bbox': [90, 20, 130, 100], 'role': 'customer', 'role_confidence': 0.8}]}
        for i in range(100, 160)]  # detections only for 10–16 s
    (tmp_path / 'run.detections.json').write_text(__import__('json').dumps(detections), encoding='utf-8')
    out = tmp_path / 'out' / 'review.mp4'
    summary = render_review_clip(resolve_video('fixture-clip-01', tmp_path), load_detections(tmp_path / 'run.detections.json'),
                                 ClipSegment(video_ref='fixture-clip-01', offset_start_s=8, offset_end_s=20), out,
                                 highlight_tracks=(7,), title='i1', synthetic=True)
    assert 115 <= summary['frames'] <= 125            # 12 s at 10 fps
    assert 55 <= summary['frames_with_boxes'] <= 70   # boxes only while detections exist (+ short hold)
    capture = cv2.VideoCapture(str(out))
    capture.set(cv2.CAP_PROP_POS_FRAMES, 40)          # about t=12 s, inside the detection span
    ok, frame = capture.read()
    capture.release()
    assert ok
    b, g, r = frame[60, 20].astype(int)               # left edge of the employee box
    assert b < 80 and g > 120 and r > 180             # orange-ish employee colour (BGR 0,180,255)
    assert frame[110, 80].astype(int)[2] > 100        # red synthetic banner along the bottom


def test_video_refs_cannot_escape_the_root(tmp_path):
    (tmp_path / 'inside').mkdir()
    make_video(tmp_path / 'secret.mp4', seconds=1)
    with pytest.raises((PermissionError, FileNotFoundError)):
        resolve_video('../secret', tmp_path / 'inside')
    with pytest.raises(FileNotFoundError):
        resolve_video('missing', tmp_path)
