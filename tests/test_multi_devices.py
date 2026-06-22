"""Multi-device routing tests."""

from __future__ import annotations

import respx
from fastapi.testclient import TestClient

from alpaca_bridge.app.server import create_app
from tests.helpers import mock_ha


def test_device_numbers_route_to_correct_entities(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            sample_config,
            states={
                "binary_sensor.weather_safe": "on",
                "binary_sensor.weather_safe_secondary": "off",
                "cover.observatory_roof": "open",
                "cover.shed_roof": "closed",
            },
        )
        client = TestClient(create_app(sample_config))

        assert client.get("/api/v1/dome/0/name?ClientTransactionID=1").json()["Value"] == (
            "Main Observatory Roof"
        )
        assert client.get("/api/v1/dome/1/name?ClientTransactionID=2").json()["Value"] == (
            "Secondary Shed Roof"
        )
        assert client.get(
            "/api/v1/safetymonitor/0/name?ClientTransactionID=3"
        ).json()["Value"] == "Main Weather Safety"
        assert client.get(
            "/api/v1/safetymonitor/1/name?ClientTransactionID=4"
        ).json()["Value"] == "Secondary Weather Safety"


def test_domes_can_share_safety_monitor(sample_config) -> None:
    cfg = sample_config.model_copy(deep=True)
    cfg.devices.domes[1].safety_monitor_ref = cfg.devices.domes[0].safety_monitor_ref

    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(
            router,
            cfg,
            states={
                "binary_sensor.weather_safe": "on",
                "cover.observatory_roof": "closed",
                "cover.shed_roof": "closed",
            },
        )

        client = TestClient(create_app(cfg))
        response = client.put(
            "/api/v1/dome/1/openshutter",
            data={"ClientID": 1, "ClientTransactionID": 5},
        )
        assert response.json()["ErrorNumber"] == 0
