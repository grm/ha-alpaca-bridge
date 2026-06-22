"""ASCOM Alpaca Dome device (shutter/roof MVP)."""

from __future__ import annotations

import enum
import logging

from alpaca_bridge.alpaca import errors
from alpaca_bridge.alpaca.devices.base import BaseAlpacaDevice, DeviceContext
from alpaca_bridge.alpaca.devices.safety_monitor import SafetyMonitorDevice
from alpaca_bridge.config import DomeDeviceConfig
from alpaca_bridge.homeassistant.models import (
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
    HomeAssistantError,
)

logger = logging.getLogger(__name__)


class ShutterState(int, enum.Enum):
    """ASCOM ShutterState enumeration (Alpaca returns integer values)."""

    OPEN = 0
    CLOSED = 1
    OPENING = 2
    CLOSING = 3
    ERROR = 4


_HA_TO_SHUTTER: dict[str, ShutterState] = {
    "open": ShutterState.OPEN,
    "closed": ShutterState.CLOSED,
    "opening": ShutterState.OPENING,
    "closing": ShutterState.CLOSING,
    "unknown": ShutterState.ERROR,
    "unavailable": ShutterState.ERROR,
}


def map_ha_cover_state_to_shutter(ha_state: str) -> ShutterState:
    """Map a Home Assistant cover state to ASCOM ShutterState."""
    return _HA_TO_SHUTTER.get(ha_state.lower(), ShutterState.ERROR)


class DomeDevice(BaseAlpacaDevice):
    device_type = "dome"
    alpaca_device_type = "Dome"

    def __init__(
        self,
        device_config: DomeDeviceConfig,
        ctx: DeviceContext,
        safety_monitors: dict[int, SafetyMonitorDevice],
    ) -> None:
        super().__init__(ctx)
        self._config = device_config
        self._safety_monitors = safety_monitors

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
                self._config.shutter_entity,
                force_refresh=True,
            )
            return True
        except (HomeAssistantConnectionError, HomeAssistantEntityNotFoundError):
            return False
        except HomeAssistantError:
            return False

    def get_can_set_shutter(self) -> bool:
        return (
            self._config.open_service is not None and self._config.close_service is not None
        )

    async def get_shutter_status(self) -> ShutterState:
        safety = self.ctx.config.safety
        try:
            cached = await self.ctx.ha_pool.get().get_state(self._config.shutter_entity)
        except HomeAssistantError:
            return ShutterState.ERROR

        if cached.age_seconds > safety.max_state_age_seconds:
            return ShutterState.ERROR

        return map_ha_cover_state_to_shutter(cached.state.state)

    async def _check_open_allowed(self) -> None:
        safety_cfg = self.ctx.config.safety
        ref = self._config.safety_monitor_ref

        if ref is None:
            if not safety_cfg.allow_open_without_safety_monitor:
                raise DomeSafetyError(
                    "OpenShutter refused: no safety monitor configured",
                    errors.INVALID_OPERATION,
                )
            return

        monitor = self._safety_monitors.get(ref.device_number)
        if monitor is None:
            raise DomeSafetyError(
                f"OpenShutter refused: safety monitor {ref.device_number} not found",
                errors.INVALID_OPERATION,
            )

        if not await monitor.get_is_safe():
            raise DomeSafetyError(
                "OpenShutter refused: safety monitor reports unsafe conditions",
                errors.INVALID_OPERATION,
            )

    async def open_shutter(self) -> None:
        if not self.get_can_set_shutter():
            raise DomeSafetyError(
                "OpenShutter not available: shutter control not fully configured",
                errors.ACTION_NOT_IMPLEMENTED,
            )
        if self.ctx.client_disconnected:
            raise DomeSafetyError("Device is not connected", errors.NOT_CONNECTED)

        await self._check_open_allowed()

        open_service = self._config.open_service
        assert open_service is not None
        try:
            await self.ctx.ha_pool.get().call_service(open_service)
        except HomeAssistantConnectionError as exc:
            raise DomeSafetyError(str(exc), errors.NOT_CONNECTED) from exc
        except HomeAssistantError as exc:
            raise DomeSafetyError(str(exc), errors.INVALID_OPERATION) from exc

    async def close_shutter(self) -> None:
        if not self.get_can_set_shutter():
            raise DomeSafetyError(
                "CloseShutter not available: shutter control not fully configured",
                errors.ACTION_NOT_IMPLEMENTED,
            )
        if self.ctx.client_disconnected:
            raise DomeSafetyError("Device is not connected", errors.NOT_CONNECTED)

        close_service = self._config.close_service
        assert close_service is not None
        try:
            await self.ctx.ha_pool.get().call_service(close_service)
        except HomeAssistantConnectionError as exc:
            raise DomeSafetyError(str(exc), errors.NOT_CONNECTED) from exc
        except HomeAssistantError as exc:
            raise DomeSafetyError(str(exc), errors.INVALID_OPERATION) from exc


class DomeSafetyError(Exception):
    def __init__(self, message: str, error_number: int) -> None:
        super().__init__(message)
        self.error_number = error_number
