"""Configuration models and add-on options loading."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

LOCAL_HA_INSTANCE_ID = "local"
_NO_SAFETY_MONITOR = -1


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 11111
    name: str = "Home Assistant Alpaca Bridge"
    manufacturer: str = "ha-alpaca-bridge"
    version: str = "0.1.0"
    location: str = ""


class CacheConfig(BaseModel):
    enabled: bool = True
    ttl_seconds: float = Field(default=5.0, ge=0.0)


class HomeAssistantInstanceConfig(BaseModel):
    id: str = LOCAL_HA_INSTANCE_ID
    url: str
    token: str
    timeout_seconds: float = 5.0

    @field_validator("url")
    @classmethod
    def strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")


class SafetyConfig(BaseModel):
    fail_safe_on_ha_error: bool = True
    fail_safe_on_unknown_state: bool = True
    max_state_age_seconds: float = Field(default=60.0, ge=0.0)
    allow_open_without_safety_monitor: bool = False


class SafetyMonitorRef(BaseModel):
    device_type: Literal["safetymonitor"] = "safetymonitor"
    device_number: int = Field(ge=0)


class ServiceTarget(BaseModel):
    entity_id: str | list[str]


class ServiceCallConfig(BaseModel):
    domain: str
    service: str
    target: ServiceTarget | None = None
    data: dict[str, Any] = Field(default_factory=dict)


class SafetyMonitorDeviceConfig(BaseModel):
    device_number: int = Field(ge=0)
    name: str
    description: str
    unique_id: str
    entity: str
    safe_state: str = "on"


class DomeDeviceConfig(BaseModel):
    device_number: int = Field(ge=0)
    name: str
    description: str
    unique_id: str
    shutter_entity: str
    safety_monitor_ref: SafetyMonitorRef | None = None
    open_service: ServiceCallConfig | None = None
    close_service: ServiceCallConfig | None = None


class DevicesConfig(BaseModel):
    safety_monitors: list[SafetyMonitorDeviceConfig] = Field(default_factory=list)
    domes: list[DomeDeviceConfig] = Field(default_factory=list)


class HomeAssistantConfig(BaseModel):
    instance: HomeAssistantInstanceConfig


class AppConfig(BaseModel):
    server: ServerConfig = Field(default_factory=ServerConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)
    home_assistant: HomeAssistantConfig
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    devices: DevicesConfig = Field(default_factory=DevicesConfig)

    @model_validator(mode="after")
    def validate_references(self) -> AppConfig:
        _check_unique_device_numbers(
            self.devices.safety_monitors, "safety_monitors", lambda d: d.device_number
        )
        _check_unique_device_numbers(self.devices.domes, "domes", lambda d: d.device_number)

        safety_numbers = {sm.device_number for sm in self.devices.safety_monitors}

        for dome in self.devices.domes:
            if dome.safety_monitor_ref is not None:
                ref = dome.safety_monitor_ref
                if ref.device_number not in safety_numbers:
                    raise ValueError(
                        f"Dome '{dome.name}' references unknown safety monitor "
                        f"device_number {ref.device_number}"
                    )

        return self


def _check_unique_device_numbers(
    devices: list[Any], label: str, number_getter: Any,
) -> None:
    seen: set[int] = set()
    for device in devices:
        number = number_getter(device)
        if number in seen:
            raise ValueError(f"Duplicate device_number {number} in {label}")
        seen.add(number)


def load_addon_config(
    options_path: str | Path | None = None,
    *,
    ha_url: str | None = None,
    ha_token: str | None = None,
) -> AppConfig:
    """Load configuration from Home Assistant add-on options JSON."""
    path = Path(options_path or os.environ.get("HA_ALPACA_OPTIONS", "/data/options.json"))
    raw_options = json.loads(path.read_text(encoding="utf-8"))
    return app_config_from_addon_options(
        raw_options,
        ha_url=ha_url or os.environ.get("HA_URL", "http://supervisor/core"),
        ha_token=ha_token or os.environ.get("SUPERVISOR_TOKEN", ""),
    )


def app_config_from_addon_options(
    options: dict[str, Any],
    *,
    ha_url: str,
    ha_token: str,
) -> AppConfig:
    """Convert Home Assistant add-on UI options to ``AppConfig``."""
    if not ha_token:
        raise ValueError("SUPERVISOR_TOKEN is required")

    safety_monitors = [
        SafetyMonitorDeviceConfig(
            device_number=item["device_number"],
            name=item["name"],
            description=item.get("description") or item["name"],
            unique_id=item["unique_id"],
            entity=item["entity"],
            safe_state=item.get("safe_state", "on"),
        )
        for item in options.get("safety_monitors", [])
    ]

    domes: list[DomeDeviceConfig] = []
    for item in options.get("domes", []):
        safety_ref = None
        monitor_number = int(item.get("safety_monitor_device_number", _NO_SAFETY_MONITOR))
        if monitor_number >= 0:
            safety_ref = SafetyMonitorRef(device_number=monitor_number)

        shutter_entity = item["shutter_entity"]
        domes.append(
            DomeDeviceConfig(
                device_number=item["device_number"],
                name=item["name"],
                description=item.get("description") or item["name"],
                unique_id=item["unique_id"],
                shutter_entity=shutter_entity,
                safety_monitor_ref=safety_ref,
                open_service=ServiceCallConfig(
                    domain=item.get("open_service_domain", "cover"),
                    service=item.get("open_service_service", "open_cover"),
                    target=ServiceTarget(entity_id=shutter_entity),
                ),
                close_service=ServiceCallConfig(
                    domain=item.get("close_service_domain", "cover"),
                    service=item.get("close_service_service", "close_cover"),
                    target=ServiceTarget(entity_id=shutter_entity),
                ),
            )
        )

    return AppConfig(
        server=ServerConfig(
            port=int(options.get("alpaca_port", 11111)),
            name=str(options.get("alpaca_name", "Home Assistant Alpaca Bridge")),
            location=str(options.get("alpaca_location", "")),
        ),
        cache=CacheConfig(
            enabled=bool(options.get("cache_enabled", True)),
            ttl_seconds=float(options.get("cache_ttl_seconds", 5)),
        ),
        home_assistant=HomeAssistantConfig(
            instance=HomeAssistantInstanceConfig(
                url=ha_url.rstrip("/"),
                token=ha_token,
                timeout_seconds=float(options.get("homeassistant_timeout_seconds", 5)),
            )
        ),
        safety=SafetyConfig(
            fail_safe_on_ha_error=bool(options.get("fail_safe_on_ha_error", True)),
            fail_safe_on_unknown_state=bool(options.get("fail_safe_on_unknown_state", True)),
            max_state_age_seconds=float(options.get("max_state_age_seconds", 60)),
            allow_open_without_safety_monitor=bool(
                options.get("allow_open_without_safety_monitor", False)
            ),
        ),
        devices=DevicesConfig(safety_monitors=safety_monitors, domes=domes),
    )
