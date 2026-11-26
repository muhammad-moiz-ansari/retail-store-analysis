import numpy as np

from backend.interaction.renderer import draw_result

RESULT = {"people": [], "interactions": [], "employee_count": 0, "customer_count": 0, "interaction_active": False}


def test_the_zone_frames_the_whole_picture_in_its_colour_and_leaves_the_source_alone():
    frame = np.full((640, 640, 3), 100, np.uint8)
    edge = lambda view: draw_result(frame, {**RESULT, "zones": {"view": view}})[320, 5]
    assert (frame == 100).all()
    assert tuple(edge("hot")) == (0, 0, 255)  # red, in BGR
    assert tuple(edge("green")) == (0, 170, 0)
    assert tuple(edge("gray")) == (150, 150, 150)
    assert tuple(edge("inactive")) == (60, 60, 60)
    assert (draw_result(frame, {**RESULT, "zones": {"view": "hot"}})[300:500, 300:500] == 100).all()  # the picture itself is untouched


def test_no_zones_draws_no_frame():
    frame = np.full((640, 640, 3), 100, np.uint8)
    assert (draw_result(frame, {**RESULT, "zones": None})[100:600, 0:20] == 100).all()
