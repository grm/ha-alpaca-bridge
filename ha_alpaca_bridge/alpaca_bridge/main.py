"""Add-on entry point."""

from __future__ import annotations

import os

import uvicorn

from alpaca_bridge.app.server import create_app
from alpaca_bridge.config import load_addon_config
from alpaca_bridge.logging import setup_logging


def main() -> None:
    log_level = os.environ.get("LOG_LEVEL", "INFO")
    setup_logging(log_level)

    config = load_addon_config()
    app = create_app(config)

    uvicorn.run(
        app,
        host=config.server.host,
        port=config.server.port,
        log_level=log_level.lower(),
    )


if __name__ == "__main__":
    main()
