"""Shared device abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from alpaca_bridge.config import LOCAL_HA_INSTANCE_ID, AppConfig
from alpaca_bridge.homeassistant.client import HomeAssistantPool
from alpaca_bridge.homeassistant.models import (
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
)


@dataclass
class DeviceContext:
    config: AppConfig
    ha_pool: HomeAssistantPool
    client_disconnected: bool = False


class BaseAlpacaDevice(ABC):
    device_type: str
    alpaca_device_type: str

    def __init__(self, ctx: DeviceContext) -> None:
        self.ctx = ctx

    @property
    @abstractmethod
    def device_number(self) -> int: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...

    @property
    @abstractmethod
    def unique_id(self) -> str: ...

    @property
    def ha_instance_id(self) -> str:
        return LOCAL_HA_INSTANCE_ID

    @property
    def driver_info(self) -> str:
        return (
            f"{self.ctx.config.server.manufacturer} Home Assistant Alpaca Bridge "
            f"v{self.ctx.config.server.version}"
        )

    @property
    def driver_version(self) -> str:
        return self.ctx.config.server.version

    @property
    def interface_version(self) -> int:
        return 1

    @property
    def supported_actions(self) -> list[str]:
        return []

    async def get_connected(self) -> bool:
        if self.ctx.client_disconnected:
            return False
        ha = self.ctx.ha_pool.get()
        if not await ha.ping():
            return False
        return await self._primary_entity_readable()

    @abstractmethod
    async def _primary_entity_readable(self) -> bool: ...

    async def set_connected(self, connected: bool) -> None:
        if not connected:
            self.ctx.client_disconnected = True
            return

        ha = self.ctx.ha_pool.get()
        if not await ha.ping():
            raise HomeAssistantConnectionError("Cannot connect: Home Assistant is unreachable")
        if not await self._primary_entity_readable():
            raise HomeAssistantEntityNotFoundError(
                f"Cannot connect: primary entity not readable for {self.name}"
            )
        self.ctx.client_disconnected = False

    def configured_device_entry(self) -> dict[str, Any]:
        return {
            "DeviceName": self.name,
            "DeviceType": self.alpaca_device_type,
            "DeviceNumber": self.device_number,
            "UniqueID": self.unique_id,
        }
