"""Anonymous global-person identity and authoritative role persistence.

Appearance embeddings may associate local tracks with a global person, but
they never decide that person's role. Roles come from explicit employee
registration or configured customer-entry rules; unresolved people remain
``unknown``.
"""

from __future__ import annotations

import threading
import uuid
from typing import Any

from .storage import Store, now


ROLES = {"unknown", "employee", "customer"}


class IdentityRegistry:
    """Store-scoped global IDs, local-track bindings, and role provenance."""

    def __init__(self, store: Store):
        self.store = store
        self._lock = threading.RLock()

    @staticmethod
    def _binding_id(session_id: str, camera_id: str, local_track_id: str) -> str:
        value = f"{session_id}\x1f{camera_id}\x1f{local_track_id}"
        return uuid.uuid5(uuid.NAMESPACE_URL, value).hex

    def _new_person(self, store_id: str) -> dict[str, Any]:
        created = now()
        person = {
            "schema_version": 1,
            "store_id": store_id,
            "global_person_id": "person-" + uuid.uuid4().hex,
            "role": "unknown",
            "role_source": "unresolved",
            "role_updated_at": created,
            "created_at": created,
        }
        return self.store.put("global_person", store_id, person["global_person_id"], person)

    def get_person(self, store_id: str, global_person_id: str) -> dict[str, Any]:
        return self.store.get("global_person", store_id, global_person_id)

    def list_people(self, store_id: str) -> list[dict[str, Any]]:
        return self.store.list("global_person", store_id)

    def resolve_track(
        self,
        store_id: str,
        session_id: str,
        camera_id: str,
        local_track_id: str,
        matched_global_person_id: str | None = None,
    ) -> dict[str, Any]:
        """Resolve one session-local track, optionally from a confirmed Re-ID match."""
        binding_id = self._binding_id(session_id, camera_id, str(local_track_id))
        with self._lock:
            try:
                binding = self.store.get("track_binding", store_id, binding_id)
                bound_id = binding["global_person_id"]
                if matched_global_person_id is not None and bound_id != matched_global_person_id:
                    raise ValueError("Track is already bound to another global person")
                return self.get_person(store_id, bound_id)
            except KeyError:
                pass

            if matched_global_person_id is None:
                person = self._new_person(store_id)
            else:
                person = self.get_person(store_id, matched_global_person_id)
            self.store.put("track_binding", store_id, binding_id, {
                "schema_version": 1,
                "store_id": store_id,
                "session_id": session_id,
                "camera_id": camera_id,
                "local_track_id": str(local_track_id),
                "global_person_id": person["global_person_id"],
                "bound_at": now(),
                "binding_source": "confirmed_reid" if matched_global_person_id else "new_track",
            })
            return person

    def assign_role(
        self,
        store_id: str,
        global_person_id: str,
        role: str,
        source: str,
        assigned_by: str | None = None,
        reason: str | None = None,
    ) -> dict[str, Any]:
        if role not in ROLES:
            raise ValueError(f"Unsupported role: {role}")
        with self._lock:
            person = self.get_person(store_id, global_person_id)
            person = {**person, "role": role, "role_source": source, "role_updated_at": now()}
            self.store.put("global_person", store_id, global_person_id, person)
            audit_id = uuid.uuid4().hex
            self.store.put("role_assignment", store_id, audit_id, {
                "schema_version": 1,
                "id": audit_id,
                "store_id": store_id,
                "global_person_id": global_person_id,
                "role": role,
                "source": source,
                "assigned_by": assigned_by,
                "reason": reason,
                "assigned_at": person["role_updated_at"],
            })
            return person

    def register_employee(
        self,
        store_id: str,
        global_person_id: str,
        assigned_by: str,
        reason: str | None = None,
    ) -> dict[str, Any]:
        return self.assign_role(
            store_id, global_person_id, "employee", "manager_registration", assigned_by, reason
        )

    def apply_customer_entry(
        self,
        store_id: str,
        global_person_id: str,
        context: dict[str, Any],
        rules: list[Any],
    ) -> dict[str, Any]:
        """Promote UNKNOWN to CUSTOMER only when an explicit rule matches."""
        person = self.get_person(store_id, global_person_id)
        if person["role"] != "unknown":
            return person
        for rule in rules:
            if rule.matches(context):
                return self.assign_role(
                    store_id,
                    global_person_id,
                    "customer",
                    f"customer_entry_rule:{rule.name}",
                    reason="Configured customer-entry/context rule matched",
                )
        return person


class _MemoryStore:
    def __init__(self):
        self.documents: dict[tuple[str, str, str], dict[str, Any]] = {}

    def put(self, kind, store_id, identifier, data):
        self.documents[(kind, store_id, identifier)] = dict(data)
        return data

    def get(self, kind, store_id, identifier):
        try:
            return dict(self.documents[(kind, store_id, identifier)])
        except KeyError as exc:
            raise KeyError(identifier) from exc

    def list(self, kind, store_id):
        return [dict(value) for (item_kind, item_store, _), value in self.documents.items()
                if item_kind == kind and item_store == store_id]


class EphemeralIdentityRegistry(IdentityRegistry):
    """Per-process fallback used by direct CV callers that do not supply storage."""

    def __init__(self):
        super().__init__(_MemoryStore())
