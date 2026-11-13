import csv
import io
import tempfile
import unittest
from pathlib import Path

from backend.pos_core import commit_import, connect, latest_analytics, preview_import


def csv_bytes(headers, rows):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return buffer.getvalue().encode("utf-8")


class PosCoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = connect(Path(self.tmp.name) / "pos.sqlite3")

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_import_metrics_conversion_and_recommendation(self):
        files = [
            (
                "transactions.csv",
                csv_bytes(
                    ["line_item_id", "transaction_id", "timestamp", "till_id", "sku_id", "sku_name", "category", "qty", "unit_price", "total_price", "unit_cost", "transaction_type"],
                    [
                        ["L1", "T1", "2026-09-01T10:00:00+05:00", "A", "S1", "Tea", "Grocery", "2", "100", "200", "60", "sale"],
                        ["L2", "T2", "2026-09-01T11:00:00+05:00", "A", "S1", "Tea", "Grocery", "1", "100", "100", "60", "sale"],
                        ["L3", "T3", "2026-09-01T12:00:00+05:00", "A", "S1", "Tea", "Grocery", "1", "100", "100", "60", "refund"],
                    ],
                ),
            ),
            (
                "inventory.csv",
                csv_bytes(
                    ["snapshot_at", "sku_id", "on_hand", "on_order", "receipt_due_at", "lead_time_days", "safety_stock_units"],
                    [["2026-09-01T09:00:00+05:00", "S1", "2", "0", "", "7", "1"]],
                ),
            ),
            (
                "footfall.csv",
                csv_bytes(
                    ["event_id", "timestamp", "direction", "camera_id"],
                    [["E1", "2026-09-01T09:55:00+05:00", "in", "ENT"], ["E2", "2026-09-01T10:30:00+05:00", "in", "ENT"]],
                ),
            ),
            ("calendar.csv", csv_bytes(["date", "is_open"], [["2026-09-01", "true"]])),
        ]
        result = commit_import(self.conn, files, {"source": "unit", "coverage_from": "2026-09-01T09:00:00+05:00", "coverage_to": "2026-09-01T21:00:00+05:00", "complete": True})
        self.assertTrue(result["ok"], result)
        analytics = latest_analytics(self.conn, "2026-09-01", "2026-09-01", 7)
        self.assertEqual(analytics["kpis"]["distinct_sale_transactions"], 2)
        self.assertEqual(analytics["kpis"]["refunds"], 100)
        self.assertEqual(analytics["conversion"]["conversion"], 1.0)
        self.assertEqual(analytics["products"][0]["sku_id"], "S1")
        self.assertEqual(analytics["recommendations"][0]["status"], "MONITOR")

    def test_preview_rejects_timestamp_only_footfall_ids(self):
        files = [("footfall.csv", csv_bytes(["timestamp", "direction", "camera_id"], [["2026-09-01T10:00:00+05:00", "in", "ENT"]]))]
        preview = preview_import(files, {"source": "unit"})
        self.assertFalse(preview["ok"])
        self.assertIn("event_id is required", preview["errors"][0]["errors"][0])


if __name__ == "__main__":
    unittest.main()
