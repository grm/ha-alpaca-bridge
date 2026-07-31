"""ObservingConditions device tests."""

from __future__ import annotations

import pytest
import respx
from fastapi.testclient import TestClient

from alpaca_bridge.alpaca import errors
from alpaca_bridge.app.server import create_app
from tests.helpers import mock_ha

_OC_STATES = {
    "sensor.weather_temperature": "12.5",
    "sensor.weather_humidity": "45.0",
    "sensor.weather_pressure": "1013.2",
    "sensor.weather_rain_rate": "0.0",
    "sensor.weather_wind_speed": "2.5",
}


def test_temperature_and_humidity(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))

        temp = client.get(
            "/api/v1/observingconditions/0/temperature",
            params={"ClientID": 1, "ClientTransactionID": 1},
        ).json()
        assert temp["ErrorNumber"] == 0
        assert temp["Value"] == 12.5

        humidity = client.get(
            "/api/v1/observingconditions/0/humidity",
            params={"ClientID": 1, "ClientTransactionID": 2},
        ).json()
        assert humidity["ErrorNumber"] == 0
        assert humidity["Value"] == 45.0


def test_unconfigured_sensor_not_implemented(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))
        data = client.get(
            "/api/v1/observingconditions/0/cloudcover",
            params={"ClientID": 1, "ClientTransactionID": 3},
        ).json()
        assert data["ErrorNumber"] == errors.ACTION_NOT_IMPLEMENTED


def test_sensor_description(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))
        data = client.get(
            "/api/v1/observingconditions/0/sensordescription",
            params={
                "ClientID": 1,
                "ClientTransactionID": 4,
                "SensorName": "Temperature",
            },
        ).json()
        assert data["ErrorNumber"] == 0
        assert data["Value"] == "sensor.weather_temperature"


def test_time_since_last_update(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))
        data = client.get(
            "/api/v1/observingconditions/0/timesincelastupdate",
            params={
                "ClientID": 1,
                "ClientTransactionID": 5,
                "SensorName": "Humidity",
            },
        ).json()
        assert data["ErrorNumber"] == 0
        assert isinstance(data["Value"], (int, float))
        assert data["Value"] >= 0


def test_average_period_get_put(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))

        before = client.get(
            "/api/v1/observingconditions/0/averageperiod",
            params={"ClientID": 1, "ClientTransactionID": 6},
        ).json()
        assert before["ErrorNumber"] == 0
        assert before["Value"] == 0

        put = client.put(
            "/api/v1/observingconditions/0/averageperiod",
            data={"ClientID": 1, "ClientTransactionID": 7, "AveragePeriod": "30"},
        ).json()
        assert put["ErrorNumber"] == 0

        after = client.get(
            "/api/v1/observingconditions/0/averageperiod",
            params={"ClientID": 1, "ClientTransactionID": 8},
        ).json()
        assert after["Value"] == 30.0


def test_refresh(sample_config) -> None:
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=_OC_STATES)
        client = TestClient(create_app(sample_config))
        data = client.put(
            "/api/v1/observingconditions/0/refresh",
            data={"ClientID": 1, "ClientTransactionID": 9},
        ).json()
        assert data["ErrorNumber"] == 0


def test_unknown_state_is_invalid_operation(sample_config) -> None:
    states = {**_OC_STATES, "sensor.weather_temperature": "unavailable"}
    with respx.mock(assert_all_mocked=False, assert_all_called=False) as router:
        mock_ha(router, sample_config, states=states)
        client = TestClient(create_app(sample_config))
        data = client.get(
            "/api/v1/observingconditions/0/temperature",
            params={"ClientID": 1, "ClientTransactionID": 10},
        ).json()
        assert data["ErrorNumber"] == errors.INVALID_OPERATION


def test_duplicate_observing_conditions_device_number(addon_options_copy) -> None:
    from alpaca_bridge.config import app_config_from_addon_options
    from tests.conftest import TEST_HA_TOKEN, TEST_HA_URL

    addon_options_copy["observing_conditions"].append(
        {**addon_options_copy["observing_conditions"][0]}
    )
    with pytest.raises(ValueError, match="Duplicate device_number"):
        app_config_from_addon_options(
            addon_options_copy,
            ha_url=TEST_HA_URL,
            ha_token=TEST_HA_TOKEN,
        )
