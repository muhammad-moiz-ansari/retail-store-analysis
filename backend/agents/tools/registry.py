"""Five fixed manager analytics calls, bound to trusted server scope."""
from dataclasses import dataclass

from ..contracts import (CoverageRequest, FootfallRequest, InteractionsRequest,
                         TrustedAccessScope, UnattendedRequest, ZoneDwellRequest)
from . import AnalyticsTools

REQUEST_TYPES = {
    'get_footfall': FootfallRequest,
    'get_zone_dwell': ZoneDwellRequest,
    'get_interactions': InteractionsRequest,
    'get_unattended': UnattendedRequest,
    'get_coverage': CoverageRequest,
}


@dataclass(frozen=True)
class ScopedToolRegistry:
    """Construct in trusted server code; this is not an authentication endpoint.

    Scope, database path and observation context are never tool arguments. There
    is no arbitrary SQL, provider, operational-dispatch or dynamic-tool surface.
    """
    tools: AnalyticsTools
    scope: TrustedAccessScope

    def __post_init__(self):
        if not isinstance(self.scope, TrustedAccessScope) or self.scope.role != 'manager':
            raise PermissionError('Registry requires a trusted manager scope')

    def invoke(self, name: str, arguments: dict):
        if name not in REQUEST_TYPES:
            raise ValueError('Unknown analytics tool')
        request = REQUEST_TYPES[name].model_validate(arguments)
        self.scope.validate_filters(request.filters)
        return getattr(self.tools, name)(scope=self.scope, request=request)

    @staticmethod
    def input_schemas():
        return {name: model.model_json_schema() for name, model in REQUEST_TYPES.items()}
