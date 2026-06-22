"""In-memory cache for Home Assistant entity states."""

from __future__ import annotations

import time
from dataclasses import dataclass

from alpaca_bridge.homeassistant.models import EntityState


@dataclass(frozen=True)
class CachedEntityState:
    state: EntityState
    fetched_at: float

    @property
    def age_seconds(self) -> float:
        return max(0.0, time.monotonic() - self.fetched_at)


class EntityStateCache:
    """TTL cache keyed by Home Assistant instance id and entity id."""

    def __init__(self, *, enabled: bool, ttl_seconds: float) -> None:
        self._enabled = enabled
        self._ttl_seconds = ttl_seconds
        self._entries: dict[tuple[str, str], CachedEntityState] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def ttl_seconds(self) -> float:
        return self._ttl_seconds

    def get(self, instance_id: str, entity_id: str) -> CachedEntityState | None:
        if not self._enabled:
            return None
        entry = self._entries.get((instance_id, entity_id))
        if entry is None:
            return None
        if entry.age_seconds > self._ttl_seconds:
            self._entries.pop((instance_id, entity_id), None)
            return None
        return entry

    def set(self, instance_id: str, entity_id: str, state: EntityState) -> CachedEntityState:
        entry = CachedEntityState(state=state, fetched_at=time.monotonic())
        self._entries[(instance_id, entity_id)] = entry
        return entry

    def invalidate(self, instance_id: str, entity_id: str) -> None:
        self._entries.pop((instance_id, entity_id), None)

    def invalidate_many(self, instance_id: str, entity_ids: set[str]) -> None:
        for entity_id in entity_ids:
            self.invalidate(instance_id, entity_id)

    def clear(self) -> None:
        self._entries.clear()
