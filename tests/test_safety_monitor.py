"""SafetyMonitor device tests."""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from alpaca_bridge.alpaca.devices.registry import DeviceRegistry
from alpaca_bridge.app.server import create_app
from alpaca_bridge.homeassistant.client import HomeAssistantPool
from tests.helpers import mock_ha


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "expected"),
    [
        ("on", True),
        ("off", False),
        ("unknown", False),
        ("unavailable", False),
    ],
)
async def test_is_safe_states(sample_config, state, expected) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"binary_sensor.weather_safe": state})
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        monitor = registry.safety_monitors[0]
        assert await monitor.get_is_safe() is expected


@pytest.mark.asyncio
async def test_is_safe_when_ha_unreachable(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, reachable=False)
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        monitor = registry.safety_monitors[0]
        assert await monitor.get_is_safe() is False


@pytest.mark.asyncio
async def test_connected_true_when_entity_readable(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"binary_sensor.weather_safe": "on"})
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        assert await registry.safety_monitors[0].get_connected() is True


@pytest.mark.asyncio
async def test_connected_false_when_ha_unreachable(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, reachable=False)
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        assert await registry.safety_monitors[0].get_connected() is False


def test_issafe_endpoint(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"binary_sensor.weather_safe": "on"})
        client = TestClient(create_app(sample_config))
        response = client.get(
            "/api/v1/safetymonitor/0/issafe?ClientID=1&ClientTransactionID=5"
        )
        data = response.json()
        assert data["Value"] is True
        assert data["ClientTransactionID"] == 5
        assert data["ErrorNumber"] == 0
