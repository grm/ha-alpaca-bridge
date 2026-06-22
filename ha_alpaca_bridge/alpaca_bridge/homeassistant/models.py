"""Home Assistant entity models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntityState:
    entity_id: str
    state: str
    attributes: dict[str, Any]


class HomeAssistantError(Exception):
    """Base error for Home Assistant communication."""


class HomeAssistantConnectionError(HomeAssistantError):
    """Home Assistant instance is unreachable or returned an auth error."""


class HomeAssistantEntityNotFoundError(HomeAssistantError):
    """Requested entity does not exist."""
