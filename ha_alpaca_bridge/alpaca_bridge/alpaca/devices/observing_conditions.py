"""ASCOM Alpaca ObservingConditions device backed by Home Assistant sensors."""

from __future__ import annotations

import logging

from alpaca_bridge.alpaca import errors
from alpaca_bridge.alpaca.devices.base import BaseAlpacaDevice, DeviceContext
from alpaca_bridge.config import OC_SENSOR_ATTRS, ObservingConditionsDeviceConfig
from alpaca_bridge.homeassistant.models import (
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
    HomeAssistantError,
)

logger = logging.getLogger(__name__)

_UNKNOWN_STATES = frozenset({"unknown", "unavailable", "none", ""})

# Alpaca property path → ASCOM sensor name used by TimeSinceLastUpdate / SensorDescription.
_PROPERTY_TO_SENSOR: dict[str, str] = {
    "cloudcover": "cloudcover",
    "dewpoint": "dewpoint",
    "humidity": "humidity",
    "pressure": "pressure",
    "rainrate": "rainrate",
    "skybrightness": "skybrightness",
    "skyquality": "skyquality",
    "skytemperature": "skytemperature",
    "starfwhm": "starfwhm",
    "temperature": "temperature",
    "winddirection": "winddirection",
    "windgust": "windgust",
    "windspeed": "windspeed",
}


class ObservingConditionsError(Exception):
    def __init__(self, message: str, error_number: int) -> None:
        super().__init__(message)
        self.error_number = error_number


class ObservingConditionsDevice(BaseAlpacaDevice):
    device_type = "observingconditions"
    alpaca_device_type = "ObservingConditions"

    def __init__(
        self,
        device_config: ObservingConditionsDeviceConfig,
        ctx: DeviceContext,
    ) -> None:
        super().__init__(ctx)
        self._config = device_config
        self._average_period = device_config.average_period

    @property
    def device_number(self) -> int:
        return self._config.device_number

    @property
    def name(self) -> str:
        return self._config.name

    @property
    def description(self) -> str:
        return self._config.description

    @property
    def unique_id(self) -> str:
        return self._config.unique_id

    async def _primary_entity_readable(self) -> bool:
        entities = list(self._config.configured_entities().values())
        if not entities:
            return True
        try:
            await self.ctx.ha_pool.get().get_state(entities[0], force_refresh=True)
            return True
        except (HomeAssistantConnectionError, HomeAssistantEntityNotFoundError):
            return False
        except HomeAssistantError:
            return False

    def get_average_period(self) -> float:
        return self._average_period

    def set_average_period(self, value: float) -> None:
        if value < 0:
            raise ObservingConditionsError(
                "AveragePeriod must be >= 0",
                errors.INVALID_VALUE,
            )
        self._average_period = value

    async def refresh(self) -> None:
        if self.ctx.client_disconnected:
            raise ObservingConditionsError("Device is not connected", errors.NOT_CONNECTED)
        client = self.ctx.ha_pool.get()
        for entity_id in self._config.configured_entities().values():
            await client.get_state(entity_id, force_refresh=True)

    async def get_sensor_value(self, property_name: str) -> float:
        sensor = _PROPERTY_TO_SENSOR.get(property_name.lower())
        if sensor is None:
            raise NotImplementedError(
                f"Property '{property_name}' is not implemented for ObservingConditions"
            )
        entity_id = self._config.entity_for_sensor(sensor)
        if not entity_id:
            raise NotImplementedError(
                f"Property '{property_name}' is not configured for ObservingConditions"
            )
        if self.ctx.client_disconnected:
            raise ObservingConditionsError("Device is not connected", errors.NOT_CONNECTED)

        cached = await self._read_entity(entity_id)
        return self._parse_float(cached.state.state, property_name)

    async def get_time_since_last_update(self, sensor_name: str) -> float:
        if self.ctx.client_disconnected:
            raise ObservingConditionsError("Device is not connected", errors.NOT_CONNECTED)

        configured = self._config.configured_entities()
        if not sensor_name:
            if not configured:
                raise ObservingConditionsError(
                    "No ObservingConditions sensors are configured",
                    errors.INVALID_OPERATION,
                )
            ages: list[float] = []
            for entity_id in configured.values():
                cached = await self._read_entity(entity_id)
                ages.append(cached.age_seconds)
            return min(ages)

        key = sensor_name.lower()
        if key not in OC_SENSOR_ATTRS:
            raise ObservingConditionsError(
                f"Unknown ObservingConditions sensor '{sensor_name}'",
                errors.INVALID_VALUE,
            )
        entity_id = self._config.entity_for_sensor(key)
        if not entity_id:
            raise NotImplementedError(
                f"Sensor '{sensor_name}' is not configured for ObservingConditions"
            )
        cached = await self._read_entity(entity_id)
        return cached.age_seconds

    def get_sensor_description(self, sensor_name: str) -> str:
        if not sensor_name:
            raise ObservingConditionsError(
                "SensorDescription requires SensorName",
                errors.INVALID_VALUE,
            )
        key = sensor_name.lower()
        if key not in OC_SENSOR_ATTRS:
            raise ObservingConditionsError(
                f"Unknown ObservingConditions sensor '{sensor_name}'",
                errors.INVALID_VALUE,
            )
        entity_id = self._config.entity_for_sensor(key)
        if not entity_id:
            raise NotImplementedError(
                f"Sensor '{sensor_name}' is not configured for ObservingConditions"
            )
        return entity_id

    async def _read_entity(self, entity_id: str):
        safety = self.ctx.config.safety
        try:
            cached = await self.ctx.ha_pool.get().get_state(entity_id)
        except HomeAssistantError as exc:
            logger.warning("ObservingConditions cannot read %s: %s", entity_id, exc)
            raise ObservingConditionsError(str(exc), errors.NOT_CONNECTED) from exc

        if cached.age_seconds > safety.max_state_age_seconds:
            raise ObservingConditionsError(
                f"State for {entity_id} is stale ({cached.age_seconds:.1f}s)",
                errors.INVALID_OPERATION,
            )

        state = cached.state.state.lower()
        if state in _UNKNOWN_STATES:
            raise ObservingConditionsError(
                f"State for {entity_id} is {cached.state.state}",
                errors.INVALID_OPERATION,
            )
        return cached

    @staticmethod
    def _parse_float(raw: str, property_name: str) -> float:
        try:
            return float(raw)
        except (TypeError, ValueError) as exc:
            raise ObservingConditionsError(
                f"Cannot parse {property_name} value '{raw}' as float",
                errors.INVALID_VALUE,
            ) from exc
