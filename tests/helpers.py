"""Test helpers for mocked Home Assistant."""

from __future__ import annotations

import re

import httpx
import respx

from alpaca_bridge.config import AppConfig, HomeAssistantInstanceConfig
from alpaca_bridge.homeassistant.client import HomeAssistantClient


def ha_instance(config: AppConfig) -> HomeAssistantInstanceConfig:
    return config.home_assistant.instance


def _resolve_instance(config: AppConfig | HomeAssistantInstanceConfig) -> HomeAssistantInstanceConfig:
    if isinstance(config, AppConfig):
        return config.home_assistant.instance
    return config


def mock_ha(
    router: respx.MockRouter,
    config: AppConfig | HomeAssistantInstanceConfig,
    *,
    states: dict[str, str] | None = None,
    reachable: bool = True,
) -> None:
    """Register respx routes for the add-on Home Assistant instance."""
    instance = _resolve_instance(config)
    states = states or {}
    base = re.escape(instance.url.rstrip("/"))

    if not reachable:
        router.get(url__regex=rf"^{base}/api/?$").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        router.get(url__regex=rf"^{base}/api/states/.+").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        router.post(url__regex=rf"^{base}/api/services/.+").mock(
            side_effect=httpx.ConnectError("connection refused")
        )
        return

    router.get(url__regex=rf"^{base}/api/?$").mock(
        return_value=httpx.Response(200, json={"message": "API running."})
    )

    for entity_id, state in states.items():
        router.get(url__regex=rf"^{base}/api/states/{re.escape(entity_id)}$").mock(
            return_value=httpx.Response(
                200,
                json={
                    "entity_id": entity_id,
                    "state": state,
                    "attributes": {},
                },
            )
        )

    router.post(url__regex=rf"^{base}/api/services/.+").mock(
        return_value=httpx.Response(200, json=[])
    )


def client_for(instance: HomeAssistantInstanceConfig) -> HomeAssistantClient:
    return HomeAssistantClient(instance)
