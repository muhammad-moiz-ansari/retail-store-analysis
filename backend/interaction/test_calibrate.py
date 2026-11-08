"""Few-shot calibration file handling."""

import json

import pytest

from .calibrate import add_references
from .config import InteractionConfig


def test_labelled_tracks_extend_a_camera_config_that_loads(tmp_path) -> None:
    people = [{"track_id": 3, "appearance": [1.0, 0.0]}, {"track_id": 5, "appearance": [0.0, 1.0]}, {"track_id": 6}]
    config = add_references({"staff_zones": [[0, 0, 0.2, 1]], "role_references": {"employee": [[0.9, 0.1]]}},
                            people, {"employee": [3], "customer": [5]})
    assert config["role_references"] == {"employee": [[0.9, 0.1], [1.0, 0.0]], "customer": [[0.0, 1.0]]}
    with pytest.raises(SystemExit):
        add_references({}, people, {"employee": [6]})  # no appearance recorded
    path = tmp_path / "cam.json"
    path.write_text(json.dumps(config))
    loaded = InteractionConfig.from_json(path, device="cpu")
    assert loaded.staff_zones == [[0, 0, 0.2, 1]] and len(loaded.role_references["employee"]) == 2
    with pytest.raises(TypeError):
        InteractionConfig.from_json(path.with_name("bad.json").write_text('{"typo": 1}') and path.with_name("bad.json"))
