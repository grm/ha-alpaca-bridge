# CLAUDE.md — ha-alpaca-bridge

## Purpose

Home Assistant **add-on only**. Exposes local HA entities as ASCOM Alpaca `SafetyMonitor` and `Dome` (shutter/roof MVP).

## Structure

```
ha_alpaca_bridge/           # Supervisor add-on folder
  config.yaml               # manifest + options schema
  Dockerfile, run.sh, build.yaml
  requirements.txt
  alpaca_bridge/            # Python package
tests/
```

Configuration comes **only** from `/data/options.json` (add-on UI). No standalone YAML mode.

## Conventions

- Python 3.12+, async I/O, FastAPI, Pydantic v2, httpx
- Alpaca JSON field casing: `ClientTransactionID`, `Value`, etc.
- HTTP 200 for handled Alpaca transactions
- English for all user-facing text

## Security rules

1. Never return safe by default
2. Do not change fail-safe without tests
3. `OpenShutter` requires safety monitor unless explicitly allowed
4. `CloseShutter` allowed when unsafe (except HA unreachable)
5. Respect `max_state_age_seconds` for stale states

## Commands

```bash
pip install -r ha_alpaca_bridge/requirements.txt -r requirements-dev.txt
pytest
```

Inside the add-on container: `python3 -m alpaca_bridge`
