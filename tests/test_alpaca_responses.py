"""Alpaca response format tests."""

from __future__ import annotations

from alpaca_bridge.alpaca.responses import error_response, method_success_response, success_response


def test_success_response_includes_value_and_transactions() -> None:
    payload = success_response(True, client_transaction_id=10, server_transaction_id=20)
    assert payload["Value"] is True
    assert payload["ClientTransactionID"] == 10
    assert payload["ServerTransactionID"] == 20
    assert payload["ErrorNumber"] == 0
    assert payload["ErrorMessage"] == ""


def test_error_response_omits_value() -> None:
    payload = error_response(
        error_number=1031,
        error_message="not connected",
        client_transaction_id=3,
        server_transaction_id=4,
    )
    assert "Value" not in payload
    assert payload["ErrorNumber"] == 1031
    assert payload["ErrorMessage"] == "not connected"


def test_method_success_response() -> None:
    payload = method_success_response(client_transaction_id=1, server_transaction_id=2)
    assert "Value" not in payload
    assert payload["ErrorNumber"] == 0
