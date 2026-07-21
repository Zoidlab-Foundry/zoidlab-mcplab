"""Thin shim over foundry-common — the shared platform layer. App-specific
behavior, if ever needed, belongs here on top of the shared base."""
from foundry_common.llm import *  # noqa: F401,F403
