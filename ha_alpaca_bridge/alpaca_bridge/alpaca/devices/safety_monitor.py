"""ASCOM Alpaca SafetyMonitor device backed by Home Assistant."""

from __future__ import annotations

import logging

from alpaca_bridge.alpaca.devices.base import BaseAlpacaDevice, DeviceContext
from alpaca_bridge.config import SafetyMonitorDeviceConfig
from alpaca_bridge.homeassistant.models import (
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
    HomeAssistantError,
)

logger = logging.getLogger(__name__)

_UNKNOWN_STATES = frozenset({"unknown", "unavailable"})


class SafetyMonitorDevice(BaseAlpacaDevice):
    device_type = "safetymonitor"
    alpaca_device_type = "SafetyMonitor"

    def __init__(self, device_config: SafetyMonitorDeviceConfig, ctx: DeviceContext) -> None:
        super().__init__(ctx)
        self._config = device_config

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
        try:
            await self.ctx.ha_pool.get().get_state(
                self._config.entity,
                force_refresh=True,
            )
            return True
        except (HomeAssistantConnectionError, HomeAssistantEntityNotFoundError):
            return False
        except HomeAssistantError:
            return False

    async def get_is_safe(self) -> bool:
        """Return True only when the HA entity matches safe_state (fail-safe)."""
        safety = self.ctx.config.safety
        try:
            cached = await self.ctx.ha_pool.get().get_state(self._config.entity)
        except HomeAssistantError as exc:
            logger.warning(
                "Safety monitor %s cannot read %s: %s",
                self.device_number,
                self._config.entity,
                exc,
            )
            if safety.fail_safe_on_ha_error:
                return False
            raise

        if cached.age_seconds > safety.max_state_age_seconds:
            logger.warning(
                "Safety monitor %s state for %s is stale (%.1fs)",
                self.device_number,
                self._config.entity,
                cached.age_seconds,
            )
            return False

        entity_state = cached.state.state.lower()
        if entity_state in _UNKNOWN_STATES:
            if safety.fail_safe_on_unknown_state:
                return False
            return False

        return entity_state == self._config.safe_state.lower()
