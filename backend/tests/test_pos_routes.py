"""HTTP tests for /pos/* through the unified backend (written before the C1 merge into main)."""

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend import pos_core, pos_service
from backend.app import app
from backend.tests.test_pos_core import csv_bytes

SECRET = {"x-pos-internal-secret": pos_service.INTERNAL_SECRET}


class PosRouteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        db = Path(self.tmp.name) / "pos.sqlite3"
        patcher = mock.patch.object(pos_service, "connect", lambda: pos_core.connect(db))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.client = TestClient(app)

    def test_health_is_open_and_other_routes_need_the_secret(self):
        self.assertEqual(self.client.get("/pos/health").json(), {"ok": True})
        self.assertEqual(self.client.get("/pos/templates").status_code, 401)
        self.assertEqual(self.client.get("/pos/templates", headers={"x-pos-internal-secret": "wrong"}).status_code, 401)
        self.assertEqual(self.client.get("/pos/templates", headers=SECRET).status_code, 200)

    def test_import_then_analytics_and_query(self):
        transactions = csv_bytes(
            ["line_item_id", "transaction_id", "timestamp", "till_id", "sku_id", "sku_name", "category", "qty", "unit_price", "total_price", "unit_cost", "transaction_type"],
            [["L1", "T1", "2026-09-01T10:00:00+05:00", "A", "S1", "Tea", "Grocery", "2", "100", "200", "60", "sale"]],
        )
        files = [("files", ("transactions.csv", transactions, "text/csv"))]
        form = {"source": "route-test", "coverage_from": "2026-09-01T09:00:00+05:00", "coverage_to": "2026-09-01T21:00:00+05:00", "complete": "true"}
        preview = self.client.post("/pos/import/preview", headers=SECRET, files=files, data=form)
        self.assertEqual(preview.status_code, 200, preview.text)
        commit = self.client.post("/pos/import/commit", headers=SECRET, files=files, data=form)
        self.assertTrue(commit.json()["ok"], commit.text)

        analytics = self.client.get("/pos/analytics", headers=SECRET, params={"from": "2026-09-01", "to": "2026-09-01"})
        self.assertEqual(analytics.status_code, 200, analytics.text)
        self.assertEqual(analytics.json()["kpis"]["distinct_sale_transactions"], 1)
        self.assertEqual(self.client.get("/pos/analytics", headers=SECRET, params={"horizon": 14}).status_code, 400)

        self.assertEqual(self.client.post("/pos/query", headers=SECRET, json={"question": " "}).status_code, 400)
        answer = self.client.post("/pos/query", headers=SECRET, json={"question": "What was revenue?", "filters": {"from": "2026-09-01", "to": "2026-09-01"}})
        self.assertEqual(answer.status_code, 200, answer.text)

    def test_unknown_job_is_404(self):
        self.assertEqual(self.client.get("/pos/jobs/missing", headers=SECRET).status_code, 404)


if __name__ == "__main__":
    unittest.main()
