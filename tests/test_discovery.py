"""Alpaca UDP discovery protocol tests."""

from __future__ import annotations

import asyncio
import json

from alpaca_bridge.discovery import DISCOVERY_PORT, AlpacaDiscoveryProtocol, start_discovery_responder


class _RecordingClient(asyncio.DatagramProtocol):
    def __init__(self) -> None:
        self.received: list[bytes] = []
        self.first_datagram: asyncio.Future[bytes] = asyncio.get_event_loop().create_future()

    def datagram_received(self, data: bytes, addr: tuple[str, int]) -> None:
        self.received.append(data)
        if not self.first_datagram.done():
            self.first_datagram.set_result(data)


async def test_responds_to_discovery_request() -> None:
    loop = asyncio.get_running_loop()
    server_transport, _server_protocol = await loop.create_datagram_endpoint(
        lambda: AlpacaDiscoveryProtocol(11111),
        local_addr=("127.0.0.1", 0),
    )
    client_protocol = _RecordingClient()
    client_transport, _ = await loop.create_datagram_endpoint(
        lambda: client_protocol,
        local_addr=("127.0.0.1", 0),
    )
    try:
        server_addr = server_transport.get_extra_info("sockname")
        client_transport.sendto(b"alpacadiscovery1", server_addr)
        data = await asyncio.wait_for(client_protocol.first_datagram, timeout=2)
        assert json.loads(data.decode("utf-8")) == {"AlpacaPort": 11111}
    finally:
        client_transport.close()
        server_transport.close()


async def test_ignores_unrelated_payload() -> None:
    loop = asyncio.get_running_loop()
    server_transport, _server_protocol = await loop.create_datagram_endpoint(
        lambda: AlpacaDiscoveryProtocol(11111),
        local_addr=("127.0.0.1", 0),
    )
    client_protocol = _RecordingClient()
    client_transport, _ = await loop.create_datagram_endpoint(
        lambda: client_protocol,
        local_addr=("127.0.0.1", 0),
    )
    try:
        server_addr = server_transport.get_extra_info("sockname")
        client_transport.sendto(b"not-a-discovery-request", server_addr)
        await asyncio.sleep(0.2)
        assert client_protocol.received == []
    finally:
        client_transport.close()
        server_transport.close()


async def test_start_discovery_responder_binds_alpaca_discovery_port(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _DummyTransport:
        def close(self) -> None:
            captured["closed"] = True

    async def fake_create_datagram_endpoint(protocol_factory, *, local_addr, allow_broadcast):
        captured["local_addr"] = local_addr
        captured["allow_broadcast"] = allow_broadcast
        protocol = protocol_factory()
        return _DummyTransport(), protocol

    loop = asyncio.get_running_loop()
    monkeypatch.setattr(loop, "create_datagram_endpoint", fake_create_datagram_endpoint)

    transport = await start_discovery_responder(11111, host="0.0.0.0")

    assert captured["local_addr"] == ("0.0.0.0", DISCOVERY_PORT)
    assert captured["allow_broadcast"] is True
    assert isinstance(transport, _DummyTransport)
