"""Configuration loading and validation tests."""

from __future__ import annotations

import copy

import pytest

from alpaca_bridge.config import AppConfig, app_config_from_addon_options
from tests.conftest import TEST_HA_TOKEN, TEST_HA_URL


def test_addon_options_build_valid_config(addon_options) -> None:
    config = app_config_from_addon_options(
        addon_options,
        ha_url=TEST_HA_URL,
        ha_token=TEST_HA_TOKEN,
    )
    assert config.server.port == 11111
    assert config.cache.ttl_seconds == 5
    assert len(config.devices.safety_monitors) == 2
    assert len(config.devices.domes) == 2


def test_duplicate_safety_monitor_device_number(addon_options_copy) -> None:
    addon_options_copy["safety_monitors"].append(
        copy.deepcopy(addon_options_copy["safety_monitors"][0])
    )
    with pytest.raises(ValueError, match="Duplicate device_number"):
        app_config_from_addon_options(
            addon_options_copy,
            ha_url=TEST_HA_URL,
            ha_token=TEST_HA_TOKEN,
        )


def test_duplicate_dome_device_number(addon_options_copy) -> None:
    addon_options_copy["domes"].append(copy.deepcopy(addon_options_copy["domes"][0]))
    with pytest.raises(ValueError, match="Duplicate device_number"):
        app_config_from_addon_options(
            addon_options_copy,
            ha_url=TEST_HA_URL,
            ha_token=TEST_HA_TOKEN,
        )


def test_unknown_safety_monitor_reference(addon_options_copy) -> None:
    addon_options_copy["domes"][0]["safety_monitor_device_number"] = 99
    with pytest.raises(ValueError, match="unknown safety monitor"):
        app_config_from_addon_options(
            addon_options_copy,
            ha_url=TEST_HA_URL,
            ha_token=TEST_HA_TOKEN,
        )
