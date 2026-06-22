"""Home Assistant REST API client."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from alpaca_bridge.config import (
    CacheConfig,
    HomeAssistantInstanceConfig,
    LOCAL_HA_INSTANCE_ID,
    ServiceCallConfig,
)
from alpaca_bridge.homeassistant.cache import CachedEntityState, EntityStateCache
from alpaca_bridge.homeassistant.models import (
    EntityState,
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
    HomeAssistantError,
)

logger = logging.getLogger(__name__)


def entity_ids_from_service(service: ServiceCallConfig) -> set[str]:
    """Return entity ids targeted by a Home Assistant service call."""
    if service.target is None:
        return set()
    entity_id = service.target.entity_id
    if isinstance(entity_id, list):
        return set(entity_id)
    return {entity_id}


class HomeAssistantClient:
    """Async client for the local Home Assistant instance."""

    def __init__(
        self,
        config: HomeAssistantInstanceConfig,
        cache: EntityStateCache | None = None,
    ) -> None:
        self.config = config
        self._cache = cache
        self._headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }

    @property
    def instance_id(self) -> str:
        return LOCAL_HA_INSTANCE_ID

    async def ping(self) -> bool:
        """Return True if Home Assistant is reachable and authenticated."""
        try:
            await self._request("GET", "/api/")
            return True
        except HomeAssistantError:
            return False

    async def get_state(
        self,
        entity_id: str,
        *,
        force_refresh: bool = False,
    ) -> CachedEntityState:
        if self._cache is not None and not force_refresh:
            cached = self._cache.get(self.instance_id, entity_id)
            if cached is not None:
                return cached

        try:
            data = await self._request("GET", f"/api/states/{entity_id}")
        except HomeAssistantConnectionError:
            raise
        except HomeAssistantError as exc:
            if "404" in str(exc):
                raise HomeAssistantEntityNotFoundError(
                    f"Entity '{entity_id}' not found"
                ) from exc
            raise

        if not isinstance(data, dict):
            raise HomeAssistantError(f"Unexpected state response for {entity_id}")

        state = EntityState(
            entity_id=data.get("entity_id", entity_id),
            state=str(data.get("state", "unknown")),
            attributes=data.get("attributes", {}) or {},
        )
        if self._cache is not None:
            return self._cache.set(self.instance_id, entity_id, state)
        return CachedEntityState(state=state, fetched_at=time.monotonic())

    async def call_service(self, service: ServiceCallConfig) -> None:
        payload: dict[str, Any] = {}
        if service.target is not None:
            payload["target"] = service.target.model_dump()
        if service.data:
            payload.update(service.data)

        await self._request(
            "POST",
            f"/api/services/{service.domain}/{service.service}",
            json=payload,
        )

        if self._cache is not None:
            self._cache.invalidate_many(self.instance_id, entity_ids_from_service(service))

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self.config.url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.request(
                    method,
                    url,
                    headers=self._headers,
                    json=json,
                )
        except httpx.RequestError as exc:
            logger.warning("Home Assistant request failed: %s", exc)
            raise HomeAssistantConnectionError("Cannot reach Home Assistant") from exc

        if response.status_code in (401, 403):
            raise HomeAssistantConnectionError("Home Assistant authentication failed")

        if response.status_code == 404:
            raise HomeAssistantEntityNotFoundError("Resource not found on Home Assistant")

        if response.status_code >= 400:
            raise HomeAssistantError(
                f"Home Assistant returned HTTP {response.status_code} for {path}"
            )

        if response.status_code == 204 or not response.content:
            return None

        return response.json()


class HomeAssistantPool:
    """Access to the local Home Assistant client."""

    def __init__(self, client: HomeAssistantClient) -> None:
        self._client = client

    def get(self, instance_id: str = LOCAL_HA_INSTANCE_ID) -> HomeAssistantClient:
        if instance_id != LOCAL_HA_INSTANCE_ID:
            raise KeyError(f"Unknown Home Assistant instance '{instance_id}'")
        return self._client

    @classmethod
    def from_config(
        cls,
        instance: HomeAssistantInstanceConfig,
        cache_config: CacheConfig | None = None,
    ) -> HomeAssistantPool:
        cache = None
        if cache_config is not None:
            cache = EntityStateCache(
                enabled=cache_config.enabled,
                ttl_seconds=cache_config.ttl_seconds,
            )
        return cls(HomeAssistantClient(instance, cache=cache))
