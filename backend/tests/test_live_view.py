"""The live run's zone state of the view served to the Interactions page."""

import json

import pytest
from fastapi import HTTPException

from backend import app as app_module
from backend.events.live_zones import LiveZone


def test_view_state_reads_the_runs_view_file_and_tolerates_its_absence(tmp_path, monkeypatch):
    output = tmp_path / "live.mp4"
    monkeypatch.setattr(app_module, "_live_runs", {"job1": output})
    assert app_module.live_view("job1") == {"view": None}  # no processed frame yet
    zone = LiveZone(hold_s=1.0)
    for t in range(4):
        state = zone.update([{"role": "customer"}, {"role": "employee"}], float(t))
    output.with_suffix(".view.json").write_text(json.dumps({**state, "timestamp": 3.0, "timeline": [{"view": "gray", "from": 1.0, "to": 3.0}]}), encoding="utf-8")
    assert app_module.live_view("job1") == {"view": "gray", "employees": 1, "customers": 1, "timestamp": 3.0,
                                            "view_seconds": {"hot": 0.0, "gray": 3.0, "green": 0.0, "inactive": 0.0},
                                            "timeline": [{"view": "gray", "from": 1.0, "to": 3.0}]}
    output.with_suffix(".view.json").write_text("{", encoding="utf-8")  # caught mid-replace
    assert app_module.live_view("job1") == {"view": None}
    with pytest.raises(HTTPException) as missing:
        app_module.live_view("nope")
    assert missing.value.status_code == 404


def test_web_video_makes_a_browser_playable_copy_at_the_same_length(tmp_path):
    cv2, av, np = pytest.importorskip("cv2"), pytest.importorskip("av"), pytest.importorskip("numpy")
    output = tmp_path / "run.mp4"
    writer = cv2.VideoWriter(str(output), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 48))
    for shade in range(30):
        writer.write(np.full((48, 64, 3), shade * 8, np.uint8))
    writer.release()
    copy = app_module.web_video(output)
    with av.open(str(copy)) as video:
        stream = video.streams.video[0]
        assert (stream.codec_context.name, stream.pix_fmt, stream.frames) == ("h264", "yuv420p", 30)
        assert abs(float(video.duration) / 1e6 - 3.0) < 0.2
    assert app_module.web_video(tmp_path / "missing.mp4") is None  # a failed copy never fails the run
    assert not (tmp_path / "missing.web.mp4").exists()
