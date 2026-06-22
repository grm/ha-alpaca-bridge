#!/usr/bin/with-contenv bashio
set -e

export LOG_LEVEL="$(bashio::config 'log_level')"

echo "Starting HA Alpaca Bridge on port $(bashio::config 'alpaca_port')..."
exec python3 -m alpaca_bridge
