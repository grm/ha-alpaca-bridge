"""Home Assistant connectivity tests."""

from __future__ import annotations

import respx
from fastapi.testclient import TestClient

from alpaca_bridge.app.server import create_app
from tests.helpers import mock_ha


def test_ha_unreachable_marks_all_devices_unsafe(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, reachable=False)
        client = TestClient(create_app(sample_config))

        safe = client.get("/api/v1/safetymonitor/0/issafe?ClientTransactionID=1").json()
        connected = client.get("/api/v1/dome/0/connected?ClientTransactionID=2").json()

        assert safe["Value"] is False
        assert connected["Value"] is False
