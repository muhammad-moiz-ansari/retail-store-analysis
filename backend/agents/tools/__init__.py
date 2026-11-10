"""Published read-tool interfaces; concrete readers are a Phase 2 deliverable."""
from typing import Protocol

from ..contracts import (CoverageRequest, CoverageResult, FootfallRequest, FootfallResult,
                         InteractionsRequest, InteractionsResult, TrustedAccessScope,
                         UnattendedRequest, UnattendedResult, ZoneDwellRequest, ZoneDwellResult)


class AnalyticsTools(Protocol):
    """Trusted scope is injected separately from untrusted validated tool arguments.

    Implementations must intersect every query with the scope, including its allowlists
    when optional request filters are omitted. This Protocol is not an implementation.
    """

    def get_footfall(self, *, scope: TrustedAccessScope, request: FootfallRequest) -> FootfallResult: ...

    def get_zone_dwell(self, *, scope: TrustedAccessScope, request: ZoneDwellRequest) -> ZoneDwellResult: ...

    def get_interactions(self, *, scope: TrustedAccessScope, request: InteractionsRequest) -> InteractionsResult: ...

    def get_unattended(self, *, scope: TrustedAccessScope, request: UnattendedRequest) -> UnattendedResult: ...

    def get_coverage(self, *, scope: TrustedAccessScope, request: CoverageRequest) -> CoverageResult: ...
