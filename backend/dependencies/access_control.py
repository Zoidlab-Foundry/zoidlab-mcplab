"""dependencies.access_control — the Foundry Pro access-control FastAPI dependencies.

These are the named dependencies from the RAG Builder spec. The implementation lives
in the top-level ``auth`` module (flat, so uvicorn and siblings can import it directly);
this module exposes it under the structured ``dependencies.access_control`` path:

    from dependencies.access_control import require_pro, require_owner

- ``require_pro``  — 403s unless the caller holds an active Nyquest Pro (Foundry) entitlement.
- ``require_owner``— returns the Nyquest user id (``owner_of``) for scoping reads/writes.
- ``entitlement`` / ``session`` — the underlying helpers.
"""
from auth import require_pro, owner_of as require_owner, entitlement, session  # noqa: F401

__all__ = ["require_pro", "require_owner", "entitlement", "session"]
