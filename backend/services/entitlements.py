"""services.entitlements — packaged entrypoint for the Foundry entitlement layer.

The reusable Nyquest Pro access logic lives in the top-level ``entitlements`` module
(kept flat so uvicorn's ``main:app`` and every sibling module can ``import entitlements``
without a package prefix). This module re-exports it under the ``services.*`` namespace
described in the RAG Builder spec, so callers that want the structured import path get it:

    from services.entitlements import entitlement_from_session, has_access
"""
from entitlements import (  # noqa: F401
    REQUIRED_PLAN,
    GATE_ENABLED,
    MOCK_PRO_USER,
    PRO_PLANS,
    ALL_PACKAGES,
    entitlement_from_session,
    has_access,
    _mock,
    _mock_session,
    _live_entitlement,
)

__all__ = [
    "REQUIRED_PLAN", "GATE_ENABLED", "MOCK_PRO_USER", "PRO_PLANS", "ALL_PACKAGES",
    "entitlement_from_session", "has_access", "_mock", "_mock_session", "_live_entitlement",
]
