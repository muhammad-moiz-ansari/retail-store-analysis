"""Bounded development-only trace storage; records are lost on process restart."""
from collections import OrderedDict
from math import isfinite
from threading import RLock
from time import monotonic
from typing import Protocol

from .contracts import TrustedAccessScope
from .graph_contracts import GraphRun


class TraceCapacityError(Exception):
    pass


class RunTraceStore(Protocol):
    def put(self, run: GraphRun) -> None: ...
    def get(self, run_id: str, scope: TrustedAccessScope) -> GraphRun: ...


class MemoryTraceStore:
    """FIFO, TTL and byte-bounded traces with full trusted-scope equality checks."""
    def __init__(self, *, max_runs=20, ttl_seconds=1800, max_run_bytes=2097152, clock=monotonic):
        if type(max_runs) is not int or not 1 <= max_runs <= 100:
            raise ValueError('max_runs must be 1--100')
        if not isfinite(ttl_seconds) or not 0 < ttl_seconds <= 86400:
            raise ValueError('TTL must be positive and at most one day')
        if type(max_run_bytes) is not int or not 1024 <= max_run_bytes <= 4194304:
            raise ValueError('Trace size must be 1 KiB--4 MiB')
        self._max_runs, self._ttl, self._max_bytes = max_runs, ttl_seconds, max_run_bytes
        self._clock, self._records, self._lock = clock, OrderedDict(), RLock()

    def _prune(self):
        now = self._clock()
        for key, (_, created, _) in list(self._records.items()):
            if now - created >= self._ttl:
                del self._records[key]

    def put(self, run):
        payload = run.model_dump_json().encode()
        if len(payload) > self._max_bytes:
            raise TraceCapacityError('Trace exceeds the configured retention byte limit')
        with self._lock:
            self._prune()
            if run.run_id in self._records:
                raise ValueError('Run IDs are append-only')
            self._records[run.run_id] = (run.scope, self._clock(), payload)
            while len(self._records) > self._max_runs:
                self._records.popitem(last=False)

    def get(self, run_id, scope):
        with self._lock:
            self._prune()
            record = self._records.get(run_id)
            if record is None or record[0] != scope:
                # Same error for absent/expired/unauthorized runs; do not reveal existence.
                raise KeyError('Analytics run not found')
            return GraphRun.model_validate_json(record[2])
