"""Callable analytics service; no unverified HTTP auth/store adapter is exposed."""
from .graph import run_analytics
from .tools.registry import ScopedToolRegistry
from .traces import MemoryTraceStore


class AnalyticsService:
    def __init__(self, tools, *, router=None, specialists=None, traces=None, limits=None):
        self._tools, self._router, self._specialists, self._limits = tools, router, specialists, limits
        self._traces = MemoryTraceStore() if traces is None else traces

    def ask(self, request, *, scope):
        registry = ScopedToolRegistry(self._tools, scope)
        run = run_analytics(request, registry, router=self._router, specialists=self._specialists, limits=self._limits)
        retained = run.model_copy(update={'trace_retained':True})
        try:
            self._traces.put(retained)
        except Exception:
            return run.model_copy(update={'errors':run.errors+('trace_not_retained',),
                'limitations':(run.limitations+('Development trace could not be retained; retrieval is unavailable',))[-50:]})
        return retained.model_copy(deep=True)

    def get_run(self, run_id, *, scope):
        run = self._traces.get(run_id, scope)
        if run.scope != scope or run.run_id != run_id:
            raise KeyError('Analytics run not found')
        return run.model_copy(deep=True)
