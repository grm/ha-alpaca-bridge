"""Device registry and factory."""

from __future__ import annotations

from dataclasses import dataclass, field

from alpaca_bridge.alpaca.devices.base import BaseAlpacaDevice, DeviceContext
from alpaca_bridge.alpaca.devices.dome import DomeDevice
from alpaca_bridge.alpaca.devices.safety_monitor import SafetyMonitorDevice
from alpaca_bridge.config import AppConfig
from alpaca_bridge.homeassistant.client import HomeAssistantPool


@dataclass
class DeviceRegistry:
    config: AppConfig
    ha_pool: HomeAssistantPool
    safety_monitors: dict[int, SafetyMonitorDevice] = field(default_factory=dict)
    domes: dict[int, DomeDevice] = field(default_factory=dict)
    _contexts: dict[tuple[str, int], DeviceContext] = field(default_factory=dict)

    @classmethod
    def from_config(cls, config: AppConfig, ha_pool: HomeAssistantPool) -> DeviceRegistry:
        registry = cls(config=config, ha_pool=ha_pool)

        for sm_cfg in config.devices.safety_monitors:
            ctx = registry._context_for("safetymonitor", sm_cfg.device_number)
            registry.safety_monitors[sm_cfg.device_number] = SafetyMonitorDevice(
                sm_cfg, ctx
            )

        for dome_cfg in config.devices.domes:
            ctx = registry._context_for("dome", dome_cfg.device_number)
            registry.domes[dome_cfg.device_number] = DomeDevice(
                dome_cfg, ctx, registry.safety_monitors
            )

        return registry

    def _context_for(self, device_type: str, device_number: int) -> DeviceContext:
        key = (device_type, device_number)
        if key not in self._contexts:
            self._contexts[key] = DeviceContext(config=self.config, ha_pool=self.ha_pool)
        return self._contexts[key]

    def get_device(self, device_type: str, device_number: int) -> BaseAlpacaDevice:
        device_type = device_type.lower()
        if device_type == "safetymonitor":
            try:
                return self.safety_monitors[device_number]
            except KeyError as exc:
                raise KeyError(f"Unknown safetymonitor device number {device_number}") from exc
        if device_type == "dome":
            try:
                return self.domes[device_number]
            except KeyError as exc:
                raise KeyError(f"Unknown dome device number {device_number}") from exc
        raise KeyError(f"Unsupported device type '{device_type}'")

    def configured_devices(self) -> list[dict]:
        devices: list[BaseAlpacaDevice] = [
            *self.safety_monitors.values(),
            *self.domes.values(),
        ]
        devices.sort(key=lambda d: (d.alpaca_device_type, d.device_number))
        return [device.configured_device_entry() for device in devices]
