"""Entity state cache tests."""

from __future__ import annotations

import time

import pytest
import respx
from fastapi.testclient import TestClient

from alpaca_bridge.app.server import create_app
from alpaca_bridge.homeassistant.cache import EntityStateCache
from alpaca_bridge.homeassistant.client import HomeAssistantPool
from alpaca_bridge.homeassistant.models import EntityState
from tests.helpers import mock_ha


def test_cache_returns_entry_within_ttl() -> None:
    cache = EntityStateCache(enabled=True, ttl_seconds=30)
    state = EntityState(entity_id="binary_sensor.test", state="on", attributes={})
    cache.set("local", "binary_sensor.test", state)
    cached = cache.get("local", "binary_sensor.test")
    assert cached is not None
    assert cached.state.state == "on"


def test_cache_expires_after_ttl() -> None:
    cache = EntityStateCache(enabled=True, ttl_seconds=0.01)
    state = EntityState(entity_id="binary_sensor.test", state="on", attributes={})
    cache.set("local", "binary_sensor.test", state)
    time.sleep(0.02)
    assert cache.get("local", "binary_sensor.test") is None


@pytest.mark.asyncio
async def test_client_uses_cache_between_reads(sample_config) -> None:
    cfg = sample_config.model_copy(deep=True)
    cfg.cache.enabled = True
    cfg.cache.ttl_seconds = 60

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, cfg, states={"binary_sensor.weather_safe": "on"})
        pool = HomeAssistantPool.from_config(cfg.home_assistant.instance, cfg.cache)
        client = pool.get()

        first = await client.get_state("binary_sensor.weather_safe")
        second = await client.get_state("binary_sensor.weather_safe")

        assert first.state.state == "on"
        assert second.state.state == "on"
        state_reads = [
            call for call in router.calls if call.request.url.path.startswith("/api/states/")
        ]
        assert len(state_reads) == 1


def test_issafe_uses_cache(sample_config) -> None:
    cfg = sample_config.model_copy(deep=True)
    cfg.cache.enabled = True
    cfg.cache.ttl_seconds = 60

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, cfg, states={"binary_sensor.weather_safe": "on"})
        client = TestClient(create_app(cfg))

        first = client.get("/api/v1/safetymonitor/0/issafe?ClientTransactionID=1").json()
        second = client.get("/api/v1/safetymonitor/0/issafe?ClientTransactionID=2").json()

        assert first["Value"] is True
        assert second["Value"] is True
        state_reads = [
            call for call in router.calls if "binary_sensor.weather_safe" in call.request.url.path
        ]
        assert len(state_reads) == 1
