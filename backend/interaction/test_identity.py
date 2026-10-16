import tempfile
import unittest
from pathlib import Path

from .identity import IdentityRegistry
from .schemas import CameraConfig, CustomerEntryRule
from .storage import Store


class IdentityRegistryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "identity.sqlite3"
        self.registry = IdentityRegistry(Store(self.db_path))

    def tearDown(self):
        self.temp.cleanup()

    def test_unknown_employee_registration_and_confirmed_reid_preserve_role(self):
        first = self.registry.resolve_track("store", "session", "cam1", "7")
        self.assertEqual(first["role"], "unknown")

        employee = self.registry.register_employee(
            "store", first["global_person_id"], "manager-1", "Shift initialization"
        )
        linked = self.registry.resolve_track(
            "store", "session", "cam2", "22", employee["global_person_id"]
        )
        self.assertEqual(linked["global_person_id"], employee["global_person_id"])
        self.assertEqual(linked["role"], "employee")

        reopened = IdentityRegistry(Store(self.db_path))
        persisted = reopened.resolve_track("store", "session", "cam2", "22")
        self.assertEqual(persisted["global_person_id"], employee["global_person_id"])
        self.assertEqual(persisted["role"], "employee")

        rule = CustomerEntryRule(
            name="public-door",
            camera_id="cam2",
            event="boundary_crossing",
            boundary="left",
            direction="left",
        )
        unchanged = self.registry.apply_customer_entry(
            "store",
            linked["global_person_id"],
            {"camera_id": "cam2", "event": "boundary_crossing", "boundary": "left", "direction": "left"},
            [rule],
        )
        self.assertEqual(unchanged["role"], "employee")

    def test_customer_requires_matching_configured_entry_rule(self):
        person = self.registry.resolve_track("store", "session", "cam1", "8")
        rule = CustomerEntryRule(
            name="public-door",
            camera_id="cam1",
            event="first_seen",
            zone="Entrance",
        )
        unresolved = self.registry.apply_customer_entry(
            "store",
            person["global_person_id"],
            {"camera_id": "cam1", "event": "first_seen", "zone": "Aisle"},
            [rule],
        )
        self.assertEqual(unresolved["role"], "unknown")

        customer = self.registry.apply_customer_entry(
            "store",
            person["global_person_id"],
            {"camera_id": "cam1", "event": "first_seen", "zone": "Entrance"},
            [rule],
        )
        self.assertEqual(customer["role"], "customer")
        self.assertEqual(customer["role_source"], "customer_entry_rule:public-door")

    def test_local_track_binding_is_store_and_session_scoped(self):
        first = self.registry.resolve_track("store-a", "session-1", "cam1", "1")
        same = self.registry.resolve_track("store-a", "session-1", "cam1", "1")
        other_session = self.registry.resolve_track("store-a", "session-2", "cam1", "1")
        other_store = self.registry.resolve_track("store-b", "session-1", "cam1", "1")
        self.assertEqual(first["global_person_id"], same["global_person_id"])
        self.assertNotEqual(first["global_person_id"], other_session["global_person_id"])
        self.assertNotEqual(first["global_person_id"], other_store["global_person_id"])

    def test_camera_config_parses_entry_rules(self):
        config = CameraConfig(camera_id="entrance", customer_entry_rules=[{
            "name": "public-zone",
            "camera_id": "entrance",
            "event": "first_seen",
            "zone": "Customer Entrance",
        }])
        self.assertEqual(config.customer_entry_rules[0].name, "public-zone")


if __name__ == "__main__":
    unittest.main()
