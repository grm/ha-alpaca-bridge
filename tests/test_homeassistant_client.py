"""Home Assistant client tests."""

from __future__ import annotations

import httpx
import pytest
import respx

from alpaca_bridge.config import HomeAssistantInstanceConfig
from alpaca_bridge.homeassistant.client import HomeAssistantClient
from alpaca_bridge.homeassistant.models import HomeAssistantEntityNotFoundError
from tests.helpers import mock_ha


@pytest.fixture
def instance_config() -> HomeAssistantInstanceConfig:
    return HomeAssistantInstanceConfig(
        id="main",
        url="http://ha.test:8123",
        token="token",
        timeout_seconds=2,
    )


@pytest.mark.asyncio
async def test_ping_success(instance_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, instance_config)
        client = HomeAssistantClient(instance_config)
        assert await client.ping() is True


@pytest.mark.asyncio
async def test_ping_unreachable(instance_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, instance_config, reachable=False)
        client = HomeAssistantClient(instance_config)
        assert await client.ping() is False


@pytest.mark.asyncio
async def test_get_state(instance_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            instance_config,
            states={"binary_sensor.weather_safe": "on"},
        )
        client = HomeAssistantClient(instance_config)
        state = await client.get_state("binary_sensor.weather_safe")
        assert state.state.state == "on"


@pytest.mark.asyncio
async def test_get_state_not_found(instance_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, instance_config)
        router.get(
            url__regex=rf"^{instance_config.url.rstrip('/')}/api/states/missing\.entity$"
        ).mock(return_value=httpx.Response(404))
        client = HomeAssistantClient(instance_config)
        with pytest.raises(HomeAssistantEntityNotFoundError):
            await client.get_state("missing.entity")


@pytest.mark.asyncio
async def test_call_service(instance_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, instance_config)
        client = HomeAssistantClient(instance_config)
        from alpaca_bridge.config import ServiceCallConfig, ServiceTarget

        await client.call_service(
            ServiceCallConfig(
                domain="cover",
                service="open_cover",
                target=ServiceTarget(entity_id="cover.roof"),
            )
        )
        service_calls = [
            call.request.url.path
            for call in router.calls
            if call.request.method == "POST"
        ]
        assert "/api/services/cover/open_cover" in service_calls
