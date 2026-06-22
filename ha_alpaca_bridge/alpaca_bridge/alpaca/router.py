"""ASCOM Alpaca Device API routing."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qs

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from alpaca_bridge.alpaca import errors
from alpaca_bridge.alpaca.devices.base import BaseAlpacaDevice
from alpaca_bridge.alpaca.devices.dome import DomeDevice, DomeSafetyError
from alpaca_bridge.alpaca.devices.registry import DeviceRegistry
from alpaca_bridge.alpaca.devices.safety_monitor import SafetyMonitorDevice
from alpaca_bridge.alpaca.responses import error_response, method_success_response, success_response
from alpaca_bridge.alpaca.transaction import TransactionContext, TransactionManager
from alpaca_bridge.homeassistant.models import (
    HomeAssistantConnectionError,
    HomeAssistantEntityNotFoundError,
)

logger = logging.getLogger(__name__)

# Common read-only properties supported by all ASCOM devices in this bridge.
_COMMON_READ_PROPERTIES = frozenset(
    {
        "connected",
        "description",
        "driverinfo",
        "driverversion",
        "interfaceversion",
        "name",
        "supportedactions",
    }
)

_SAFETY_MONITOR_PROPERTIES = _COMMON_READ_PROPERTIES | {"issafe"}

_DOME_READ_PROPERTIES = _COMMON_READ_PROPERTIES | {
    "cansetshutter",
    "shutterstatus",
}

_DOME_METHODS = frozenset({"openshutter", "closeshutter"})

# Unsupported dome capabilities return false when queried (extensible for future work).
_UNSUPPORTED_DOME_BOOL_PROPERTIES = frozenset(
    {
        "canfindhome",
        "canpark",
        "cansetaltitude",
        "cansetazimuth",
        "cansetpark",
        "canslave",
        "cansyncazimuth",
    }
)


def parse_transaction_context(request: Request, body: dict[str, Any] | None = None) -> TransactionContext:
    query = parse_qs(str(request.url.query), keep_blank_values=True)
    client_id = _first_int(query.get("ClientID") or query.get("clientid"), default=0)
    client_tx = _first_int(
        query.get("ClientTransactionID") or query.get("clienttransactionid"),
        default=0,
    )
    if body:
        client_id = _first_int([str(body.get("ClientID", client_id))], default=client_id)
        client_tx = _first_int(
            [str(body.get("ClientTransactionID", client_tx))],
            default=client_tx,
        )
    return TransactionContext(client_id=client_id, client_transaction_id=client_tx)


def _first_int(values: list[str] | None, *, default: int) -> int:
    if not values:
        return default
    try:
        return int(values[0])
    except (TypeError, ValueError):
        return default


async def parse_put_body(request: Request) -> dict[str, Any]:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        data = await request.json()
        return data if isinstance(data, dict) else {}
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        form = await request.form()
        return {k: _coerce_form_value(v) for k, v in form.items()}
    return {}


def _coerce_form_value(value: Any) -> Any:
    if isinstance(value, str):
        lower = value.lower()
        if lower == "true":
            return True
        if lower == "false":
            return False
        try:
            return int(value)
        except ValueError:
            return value
    return value


def create_device_router(registry: DeviceRegistry, transaction_manager: TransactionManager) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/{device_type}/{device_number}/{command}")
    @router.put("/api/v1/{device_type}/{device_number}/{command}")
    async def device_endpoint(
        device_type: str,
        device_number: int,
        command: str,
        request: Request,
    ) -> Response:
        command_lower = command.lower()
        body: dict[str, Any] | None = None
        if request.method == "PUT":
            body = await parse_put_body(request)

        tx = parse_transaction_context(request, body)
        server_tx = transaction_manager.next_server_transaction_id()

        try:
            device = registry.get_device(device_type, device_number)
        except KeyError as exc:
            return JSONResponse(
                error_response(
                    error_number=errors.INVALID_VALUE,
                    error_message=str(exc),
                    client_transaction_id=tx.client_transaction_id,
                    server_transaction_id=server_tx,
                ),
                status_code=400,
            )

        try:
            payload = await _dispatch(
                request.method,
                device_type.lower(),
                command_lower,
                device,
                body,
                tx,
                server_tx,
            )
            return JSONResponse(payload, status_code=200)
        except DomeSafetyError as exc:
            return JSONResponse(
                error_response(
                    error_number=exc.error_number,
                    error_message=str(exc),
                    client_transaction_id=tx.client_transaction_id,
                    server_transaction_id=server_tx,
                ),
                status_code=200,
            )
        except (HomeAssistantConnectionError, HomeAssistantEntityNotFoundError) as exc:
            return JSONResponse(
                error_response(
                    error_number=errors.NOT_CONNECTED,
                    error_message=str(exc),
                    client_transaction_id=tx.client_transaction_id,
                    server_transaction_id=server_tx,
                ),
                status_code=200,
            )
        except NotImplementedError as exc:
            return JSONResponse(
                error_response(
                    error_number=errors.ACTION_NOT_IMPLEMENTED,
                    error_message=str(exc),
                    client_transaction_id=tx.client_transaction_id,
                    server_transaction_id=server_tx,
                ),
                status_code=200,
            )

    return router


async def _dispatch(
    method: str,
    device_type: str,
    command: str,
    device: BaseAlpacaDevice,
    body: dict[str, Any] | None,
    tx: TransactionContext,
    server_tx: int,
) -> dict[str, Any]:
    if command == "connected":
        return await _handle_connected(method, device, body, tx, server_tx)

    if method == "PUT":
        return await _handle_put_method(device_type, command, device, tx, server_tx)

    if device_type == "safetymonitor":
        return await _handle_safety_monitor_get(command, device, tx, server_tx)
    if device_type == "dome":
        return await _handle_dome_get(command, device, tx, server_tx)

    raise NotImplementedError(f"Unsupported device type '{device_type}'")


async def _handle_connected(
    method: str,
    device: BaseAlpacaDevice,
    body: dict[str, Any] | None,
    tx: TransactionContext,
    server_tx: int,
) -> dict[str, Any]:
    if method == "GET":
        return success_response(
            await device.get_connected(),
            client_transaction_id=tx.client_transaction_id,
            server_transaction_id=server_tx,
        )

    if body is None:
        raise NotImplementedError("PUT connected requires a request body")

    connected = body.get("Connected")
    if connected is None:
        raise NotImplementedError("PUT connected requires Connected parameter")

    await device.set_connected(bool(connected))
    return method_success_response(
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


async def _handle_put_method(
    device_type: str,
    command: str,
    device: BaseAlpacaDevice,
    tx: TransactionContext,
    server_tx: int,
) -> dict[str, Any]:
    if device_type != "dome" or command not in _DOME_METHODS:
        raise NotImplementedError(f"PUT {command} is not implemented")

    assert isinstance(device, DomeDevice)
    if command == "openshutter":
        await device.open_shutter()
    elif command == "closeshutter":
        await device.close_shutter()

    return method_success_response(
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


async def _handle_safety_monitor_get(
    command: str,
    device: BaseAlpacaDevice,
    tx: TransactionContext,
    server_tx: int,
) -> dict[str, Any]:
    if command not in _SAFETY_MONITOR_PROPERTIES:
        raise NotImplementedError(f"Property '{command}' is not implemented for SafetyMonitor")

    assert isinstance(device, SafetyMonitorDevice)
    value = await _read_common_or_specific(command, device)
    return success_response(
        value,
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


async def _handle_dome_get(
    command: str,
    device: BaseAlpacaDevice,
    tx: TransactionContext,
    server_tx: int,
) -> dict[str, Any]:
    if command in _UNSUPPORTED_DOME_BOOL_PROPERTIES:
        return success_response(
            False,
            client_transaction_id=tx.client_transaction_id,
            server_transaction_id=server_tx,
        )

    if command not in _DOME_READ_PROPERTIES:
        raise NotImplementedError(f"Property '{command}' is not implemented for Dome")

    assert isinstance(device, DomeDevice)
    if command == "cansetshutter":
        value: Any = device.get_can_set_shutter()
    elif command == "shutterstatus":
        value = (await device.get_shutter_status()).value
    else:
        value = await _read_common_or_specific(command, device)

    return success_response(
        value,
        client_transaction_id=tx.client_transaction_id,
        server_transaction_id=server_tx,
    )


async def _read_common_or_specific(command: str, device: BaseAlpacaDevice) -> Any:
    if command == "connected":
        return await device.get_connected()
    if command == "description":
        return device.description
    if command == "driverinfo":
        return device.driver_info
    if command == "driverversion":
        return device.driver_version
    if command == "interfaceversion":
        return device.interface_version
    if command == "name":
        return device.name
    if command == "supportedactions":
        return device.supported_actions
    if command == "issafe":
        assert isinstance(device, SafetyMonitorDevice)
        return await device.get_is_safe()
    raise NotImplementedError(f"Property '{command}' is not implemented")
