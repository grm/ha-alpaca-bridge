"""Dome device tests."""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from alpaca_bridge.alpaca import errors
from alpaca_bridge.alpaca.devices.dome import ShutterState, map_ha_cover_state_to_shutter
from alpaca_bridge.alpaca.devices.registry import DeviceRegistry
from alpaca_bridge.app.server import create_app
from alpaca_bridge.homeassistant.client import HomeAssistantPool
from tests.helpers import mock_ha


@pytest.mark.parametrize(
    ("ha_state", "expected"),
    [
        ("open", ShutterState.OPEN),
        ("closed", ShutterState.CLOSED),
        ("opening", ShutterState.OPENING),
        ("closing", ShutterState.CLOSING),
        ("unknown", ShutterState.ERROR),
        ("unavailable", ShutterState.ERROR),
    ],
)
def test_shutter_status_mapping(ha_state, expected) -> None:
    assert map_ha_cover_state_to_shutter(ha_state) == expected


@pytest.mark.asyncio
async def test_can_set_shutter_requires_both_services(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"cover.observatory_roof": "closed"})
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        dome = registry.domes[0]
        assert dome.get_can_set_shutter() is True

        partial_cfg = sample_config.model_copy(deep=True)
        partial_cfg.devices.domes[0].close_service = None
        registry2 = DeviceRegistry.from_config(partial_cfg, pool)
        assert registry2.domes[0].get_can_set_shutter() is False


@pytest.mark.asyncio
async def test_open_shutter_calls_ha_service(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            sample_config,
            states={
                "binary_sensor.weather_safe": "on",
                "cover.observatory_roof": "closed",
            },
        )
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        await registry.domes[0].open_shutter()
        service_calls = [
            call.request.url.path
            for call in router.calls
            if call.request.method == "POST"
        ]
        assert "/api/services/cover/open_cover" in service_calls


@pytest.mark.asyncio
async def test_close_shutter_allowed_when_unsafe(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            sample_config,
            states={
                "binary_sensor.weather_safe": "off",
                "cover.observatory_roof": "open",
            },
        )
        pool = HomeAssistantPool.from_config(sample_config.home_assistant.instance)
        registry = DeviceRegistry.from_config(sample_config, pool)
        await registry.domes[0].close_shutter()
        service_calls = [
            call.request.url.path
            for call in router.calls
            if call.request.method == "POST"
        ]
        assert "/api/services/cover/close_cover" in service_calls


def test_open_shutter_refused_when_unsafe(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            sample_config,
            states={
                "binary_sensor.weather_safe": "off",
                "cover.observatory_roof": "closed",
            },
        )
        client = TestClient(create_app(sample_config))
        response = client.put(
            "/api/v1/dome/0/openshutter",
            data={"ClientID": 1, "ClientTransactionID": 9},
        )
        data = response.json()
        assert data["ErrorNumber"] == errors.INVALID_OPERATION
        assert "unsafe" in data["ErrorMessage"].lower()


def test_open_shutter_refused_without_safety_monitor(sample_config) -> None:
    cfg = sample_config.model_copy(deep=True)
    cfg.devices.domes[0].safety_monitor_ref = None
    cfg.safety.allow_open_without_safety_monitor = False
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, cfg, states={"cover.observatory_roof": "closed"})
        client = TestClient(create_app(cfg))
        response = client.put(
            "/api/v1/dome/0/openshutter",
            data={"ClientID": 1, "ClientTransactionID": 10},
        )
        data = response.json()
        assert data["ErrorNumber"] == errors.INVALID_OPERATION


def test_unsupported_dome_property_returns_alpaca_error(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"cover.observatory_roof": "closed"})
        client = TestClient(create_app(sample_config))
        response = client.get("/api/v1/dome/0/azimuth?ClientTransactionID=1")
        data = response.json()
        assert data["ErrorNumber"] == errors.ACTION_NOT_IMPLEMENTED


def test_unsupported_dome_capability_is_false(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={"cover.observatory_roof": "closed"})
        client = TestClient(create_app(sample_config))
        response = client.get("/api/v1/dome/0/canpark?ClientTransactionID=1")
        assert response.json()["Value"] is False
