"""Shared-secret lookup that fails closed (SECURITY_REVIEW S1).

The fixed local default is accepted only when RETAILPULSE_DEV_DEFAULTS=1 (set by `npm run dev` and the tests).
Anywhere else a missing or default secret stops the backend from starting.
"""

import hmac
import os

DEV_DEFAULT = "local-dev-pos-secret"


def internal_secret(*names: str) -> str:
    value = next((os.environ[n] for n in names if os.environ.get(n)), None)
    if os.getenv("RETAILPULSE_DEV_DEFAULTS") == "1":
        return value or DEV_DEFAULT
    if not value or value == DEV_DEFAULT:
        raise RuntimeError(f"Set {' or '.join(names)} to a long random value (or RETAILPULSE_DEV_DEFAULTS=1 for local development)")
    return value


def matches(given: str | None, expected: str) -> bool:
    """Constant-time comparison (S2)."""
    return hmac.compare_digest((given or "").encode(), expected.encode())
