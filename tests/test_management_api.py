"""Management API tests."""

from __future__ import annotations

import respx
from fastapi.testclient import TestClient

from alpaca_bridge.app.server import create_app
from tests.helpers import mock_ha


def test_apiversions(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states={}, reachable=True)
        client = TestClient(create_app(sample_config))
        response = client.get(
            "/management/apiversions?ClientID=1&ClientTransactionID=42"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["Value"] == [1]
        assert data["ClientTransactionID"] == 42
        assert data["ServerTransactionID"] >= 1
        assert data["ErrorNumber"] == 0


def test_description(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config)
        client = TestClient(create_app(sample_config))
        response = client.get("/management/v1/description?ClientTransactionID=1")
        data = response.json()
        assert data["Value"]["ServerName"] == sample_config.server.name
        assert data["Value"]["Manufacturer"] == sample_config.server.manufacturer


def test_configured_devices(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config)
        client = TestClient(create_app(sample_config))
        response = client.get("/management/v1/configureddevices?ClientTransactionID=2")
        data = response.json()
        devices = data["Value"]
        assert len(devices) == 4
        types = {(d["DeviceType"], d["DeviceNumber"]) for d in devices}
        assert ("Dome", 0) in types
        assert ("Dome", 1) in types
        assert ("SafetyMonitor", 0) in types
        assert ("SafetyMonitor", 1) in types
