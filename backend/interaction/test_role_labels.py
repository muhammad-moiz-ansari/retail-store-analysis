from .role_labels import box_at, track_roles


def test_box_at_interpolates_and_respects_outside():
    keys = [[0, 0, 0, 0, 10, 10], [10, 0, 10, 0, 20, 10], [20, 1, 10, 0, 20, 10], [30, 0, 50, 0, 60, 10]]
    assert box_at(keys, 5) == [5, 0, 15, 10]
    assert box_at(keys, 25) is None  # outside from frame 20 until the next keyframe
    assert box_at(keys, 40) == [50, 0, 60, 10]  # last keyframe holds to the end
    assert box_at(keys, -1) is None


def test_track_takes_role_of_the_person_it_overlaps():
    persons = [{"role": "employee", "keyframes": [[0, 0, 0, 0, 10, 10]]},
               {"role": "customer", "keyframes": [[0, 0, 100, 0, 110, 10]]}]
    frames = [{"frame": f, "people": [{"track_id": 1, "bbox": [0, 0, 10, 10]}, {"track_id": 2, "bbox": [101, 0, 111, 10]},
                                      {"track_id": 3, "bbox": [50, 0, 60, 10]}]} for f in range(4)]
    assert track_roles(frames, persons) == {"1": "employee", "2": "customer"}  # track 3 overlaps nobody
