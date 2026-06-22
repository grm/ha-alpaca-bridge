"""Standard ASCOM Alpaca JSON response builders."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class AlpacaResponse(BaseModel):
    """Base Alpaca transaction response."""

    model_config = ConfigDict(populate_by_name=True)

    ClientTransactionID: int
    ServerTransactionID: int
    ErrorNumber: int = 0
    ErrorMessage: str = ""


class AlpacaValueResponse(AlpacaResponse):
    Value: Any


def success_response(
    value: Any,
    *,
    client_transaction_id: int,
    server_transaction_id: int,
) -> dict[str, Any]:
    return AlpacaValueResponse(
        Value=value,
        ClientTransactionID=client_transaction_id,
        ServerTransactionID=server_transaction_id,
        ErrorNumber=0,
        ErrorMessage="",
    ).model_dump(exclude_none=True)


def method_success_response(
    *,
    client_transaction_id: int,
    server_transaction_id: int,
) -> dict[str, Any]:
    return AlpacaResponse(
        ClientTransactionID=client_transaction_id,
        ServerTransactionID=server_transaction_id,
        ErrorNumber=0,
        ErrorMessage="",
    ).model_dump(exclude_none=True)


def error_response(
    *,
    error_number: int,
    error_message: str,
    client_transaction_id: int,
    server_transaction_id: int,
) -> dict[str, Any]:
    return AlpacaResponse(
        ClientTransactionID=client_transaction_id,
        ServerTransactionID=server_transaction_id,
        ErrorNumber=error_number,
        ErrorMessage=error_message,
    ).model_dump(exclude_none=True)
