"""ASCOM Alpaca UDP discovery protocol.

Alpaca clients (NINA, ASCOM Remote, ...) locate servers by broadcasting the
ASCII string ``alpacadiscovery1`` on UDP port 32227. A compliant server
listens on that port and replies directly to the sender with
``{"AlpacaPort": <port>}``, where ``<port>`` is the TCP port serving the
Alpaca device API.

This responder is opt-in: it is only started when the add-on option
``alpaca_discovery_enabled`` is set.
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

DISCOVERY_PORT = 32227
_DISCOVERY_REQUEST = b"alpacadiscovery1"


class AlpacaDiscoveryProtocol(asyncio.DatagramProtocol):
    """Replies to Alpaca discovery broadcasts with the configured Alpaca port."""

    def __init__(self, alpaca_port: int) -> None:
        self._alpaca_port = alpaca_port
        self._transport: asyncio.DatagramTransport | None = None

    def connection_made(self, transport: asyncio.BaseTransport) -> None:
        self._transport = transport  # type: ignore[assignment]

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        if not data.startswith(_DISCOVERY_REQUEST):
            return
        if self._transport is None:
            return
        response = json.dumps({"AlpacaPort": self._alpaca_port}).encode("utf-8")
        logger.debug(
            "Alpaca discovery request from %s, replying with port %s", addr, self._alpaca_port
        )
        self._transport.sendto(response, addr)

    def error_received(self, exc: Exception) -> None:
        logger.warning("Alpaca discovery socket error: %s", exc)


async def start_discovery_responder(
    alpaca_port: int,
    *,
    host: str = "0.0.0.0",
) -> asyncio.DatagramTransport:
    """Start the UDP discovery responder and return its transport for later shutdown."""
    loop = asyncio.get_running_loop()
    transport, _protocol = await loop.create_datagram_endpoint(
        lambda: AlpacaDiscoveryProtocol(alpaca_port),
        local_addr=(host, DISCOVERY_PORT),
        allow_broadcast=True,
    )
    logger.info("Alpaca discovery responder listening on UDP %s:%s", host, DISCOVERY_PORT)
    return transport
