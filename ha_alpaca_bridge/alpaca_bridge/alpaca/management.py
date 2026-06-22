"""ASCOM Alpaca Management API endpoints."""

from __future__ import annotations

from typing import Any

from alpaca_bridge.alpaca.devices.registry import DeviceRegistry
from alpaca_bridge.alpaca.responses import success_response
from alpaca_bridge.alpaca.transaction import TransactionContext, TransactionManager
from alpaca_bridge.config import AppConfig


def handle_apiversions(
    tx: TransactionContext,
    transaction_manager: TransactionManager,
) -> dict[str, Any]:
    server_tx = transaction_manager.next_server_transaction_id()
    return success_response(
        [1],
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


def handle_description(
    config: AppConfig,
    tx: TransactionContext,
    transaction_manager: TransactionManager,
) -> dict[str, Any]:
    server_tx = transaction_manager.next_server_transaction_id()
    return success_response(
        {
            "ServerName": config.server.name,
            "Manufacturer": config.server.manufacturer,
            "ManufacturerVersion": config.server.version,
            "Location": config.server.location,
        },
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


def handle_configured_devices(
    registry: DeviceRegistry,
    tx: TransactionContext,
    transaction_manager: TransactionManager,
) -> dict[str, Any]:
    server_tx = transaction_manager.next_server_transaction_id()
    return success_response(
        registry.configured_devices(),
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )
