"""Shared test fixtures."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import respx

from alpaca_bridge.config import AppConfig, app_config_from_addon_options

FIXTURES_DIR = Path(__file__).parent / "fixtures"
TEST_HA_URL = "http://ha.test:8123"
TEST_HA_TOKEN = "test-token"


@pytest.fixture
def addon_options() -> dict:
    return json.loads((FIXTURES_DIR / "options.json").read_text(encoding="utf-8"))


@pytest.fixture
def sample_config(addon_options: dict) -> AppConfig:
    return app_config_from_addon_options(
        addon_options,
        ha_url=TEST_HA_URL,
        ha_token=TEST_HA_TOKEN,
    )


@pytest.fixture
def addon_options_copy(addon_options: dict) -> dict:
    return deepcopy(addon_options)


@pytest.fixture
def respx_router():
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        yield router
