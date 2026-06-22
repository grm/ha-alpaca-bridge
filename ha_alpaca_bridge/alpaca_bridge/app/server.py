"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from alpaca_bridge.alpaca.devices.registry import DeviceRegistry
from alpaca_bridge.alpaca.management import (
    handle_apiversions,
    handle_configured_devices,
    handle_description,
)
from alpaca_bridge.alpaca.router import create_device_router, parse_transaction_context
from alpaca_bridge.alpaca.transaction import TransactionManager
from alpaca_bridge.config import AppConfig
from alpaca_bridge.homeassistant.client import HomeAssistantPool


def create_app(config: AppConfig) -> FastAPI:
    ha_pool = HomeAssistantPool.from_config(
        config.home_assistant.instance,
        config.cache,
    )
    registry = DeviceRegistry.from_config(config, ha_pool)
    transaction_manager = TransactionManager()

    app = FastAPI(
        title=config.server.name,
        version=config.server.version,
        description="Home Assistant ASCOM Alpaca bridge",
    )

    @app.get("/management/apiversions")
    async def apiversions(request: Request) -> JSONResponse:
        tx = parse_transaction_context(request)
        payload = handle_apiversions(tx, transaction_manager)
        return JSONResponse(payload)

    @app.get("/management/v1/description")
    async def description(request: Request) -> JSONResponse:
        tx = parse_transaction_context(request)
        payload = handle_description(config, tx, transaction_manager)
        return JSONResponse(payload)

    @app.get("/management/v1/configureddevices")
    async def configureddevices(request: Request) -> JSONResponse:
        tx = parse_transaction_context(request)
        payload = handle_configured_devices(registry, tx, transaction_manager)
        return JSONResponse(payload)

    app.include_router(create_device_router(registry, transaction_manager))
    return app
