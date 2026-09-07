import unittest

from compare_people import build_ratio_verdict
from handoff_core import HandoffConfig, boundary_side, crossing_direction, match_handoff_events


class HandoffCoreTests(unittest.TestCase):
    def test_boundary_and_direction(self):
        self.assertEqual(boundary_side(0.2, 0.5), "left")
        self.assertEqual(crossing_direction(0.8, 0.9, 0.85), "right")
        self.assertEqual(crossing_direction(0.1, 0.2, 0.15), "right")
        self.assertIsNone(crossing_direction(0.2, 0.3, 0.5))

    def test_matching_is_one_to_one_and_directional(self):
        config = HandoffConfig()
        exits = [{"event_id": "out-1", "camera_id": "cam1", "direction": "right", "timestamp_seconds": 10, "local_track_id": "1", "appearance": [1, 0]}]
        entries = [
            {"event_id": "in-left", "camera_id": "cam2", "direction": "left", "timestamp_seconds": 30, "local_track_id": "2", "appearance": [1, 0]},
            {"event_id": "in-right", "camera_id": "cam2", "direction": "right", "timestamp_seconds": 30, "local_track_id": "3", "appearance": [1, 0]},
        ]
        matches = match_handoff_events(exits, entries, config)
        confirmed = [match for match in matches if match["status"] == "confirmed"]
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0]["target_event_id"], "in-left")
        self.assertEqual(confirmed[0]["master_id"], "master-001")
        self.assertTrue(any(match["target_event_id"] == "in-right" and match["status"] == "unmatched" for match in matches))

    def test_out_of_window_is_unmatched(self):
        config = HandoffConfig(max_gap_seconds=10)
        matches = match_handoff_events(
            [{"event_id": "out", "camera_id": "cam1", "direction": "right", "timestamp_seconds": 0, "appearance": [1]}],
            [{"event_id": "in", "camera_id": "cam2", "direction": "left", "timestamp_seconds": 20, "appearance": [1]}],
            config,
        )
        self.assertEqual(matches[0]["status"], "unmatched")

    def test_ratio_verdict_prefers_ratio_not_raw_difference(self):
        self.assertIn("V2", build_ratio_verdict(3, 6))
        self.assertIn("V1", build_ratio_verdict(6, 3))
        self.assertIn("Balanced", build_ratio_verdict(2, 2))


if __name__ == "__main__":
    unittest.main()