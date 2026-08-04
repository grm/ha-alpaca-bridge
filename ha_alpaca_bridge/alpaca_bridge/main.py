"""Add-on entry point."""

from __future__ import annotations

import asyncio
import os

import uvicorn

from alpaca_bridge.app.server import create_app
from alpaca_bridge.config import load_addon_config
from alpaca_bridge.discovery import start_discovery_responder
from alpaca_bridge.logging import setup_logging


async def _run() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    config = load_addon_config()
    app = create_app(config)

    discovery_transport = None
    if config.server.discovery_enabled:
        discovery_transport = await start_discovery_responder(
            config.server.port, host=config.server.host
        )

    server = uvicorn.Server(
        uvicorn.Config(
            app,
            host=config.server.host,
            port=config.server.port,
            log_level=log_level.lower(),
        )
    )
    try:
        await server.serve()
    finally:
        if discovery_transport is not None:
            discovery_transport.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
