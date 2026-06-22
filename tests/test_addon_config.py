"""Home Assistant add-on configuration tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpaca_bridge.config import AppConfig, app_config_from_addon_options, load_addon_config
from tests.conftest import TEST_HA_URL


def test_app_config_from_addon_options(addon_options) -> None:
    config = app_config_from_addon_options(
        addon_options,
        ha_url="http://supervisor/core",
        ha_token="supervisor-token",
    )
    assert config.server.port == 11111
    assert config.cache.ttl_seconds == 5
    assert config.home_assistant.instance.url == "http://supervisor/core"
    assert config.home_assistant.instance.token == "supervisor-token"
    assert len(config.devices.safety_monitors) == 1 or len(config.devices.safety_monitors) == 2
    assert len(config.devices.domes) >= 1


def test_addon_options_without_safety_monitor_ref(addon_options) -> None:
    options = json.loads(json.dumps(addon_options))
    options["domes"][0]["safety_monitor_device_number"] = -1
    config = app_config_from_addon_options(
        options,
        ha_url=TEST_HA_URL,
        ha_token="token",
    )
    assert config.devices.domes[0].safety_monitor_ref is None


def test_load_addon_config_from_file(tmp_path: Path, addon_options, monkeypatch) -> None:
    options_path = tmp_path / "options.json"
    options_path.write_text(json.dumps(addon_options), encoding="utf-8")
    monkeypatch.setenv("SUPERVISOR_TOKEN", "token-from-env")

    config = load_addon_config(options_path, ha_url=TEST_HA_URL)
    assert isinstance(config, AppConfig)
    assert config.home_assistant.instance.token == "token-from-env"


def test_load_addon_config_requires_token(addon_options, tmp_path: Path) -> None:
    options_path = tmp_path / "options.json"
    options_path.write_text(json.dumps(addon_options), encoding="utf-8")
    with pytest.raises(ValueError, match="SUPERVISOR_TOKEN"):
        load_addon_config(options_path, ha_url=TEST_HA_URL, ha_token="")
