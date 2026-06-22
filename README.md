# ha-alpaca-bridge

Home Assistant add-on that exposes observatory entities as **ASCOM Alpaca** `SafetyMonitor` and `Dome` devices for NINA, Voyager, ASCOM Remote, and other Alpaca clients.

```
NINA / ASCOM Alpaca client
        |
        v
HA Alpaca Bridge add-on (inside Home Assistant)
        |
        v
Home Assistant entities (binary_sensor, cover, services)
```

## Install

1. **Settings → Add-ons → Add-on store → ⋮ → Repositories**
2. Add the repository URL:

   ```text
   https://github.com/grm/ha-alpaca-bridge
   ```

3. Install **HA Alpaca Bridge**
4. Configure from the **Configuration** tab
5. Start the add-on

Point Alpaca clients to:

```text
http://<home-assistant-host>:11111
```

## Project structure

```text
repository.yaml
ha_alpaca_bridge/              # add-on directory (Supervisor build context)
  config.yaml                  # manifest + UI schema
  Dockerfile
  run.sh
  build.yaml
  requirements.txt
  translations/en.yaml
  DOCS.md
  alpaca_bridge/               # Python application
tests/                         # pytest suite (dev)
pytest.ini
requirements-dev.txt
```

This follows the [standard Home Assistant add-on layout](https://developers.home-assistant.io/docs/add-ons/configuration/).

## Configuration (UI)

All settings are managed from the add-on **Configuration** tab:

| Section | Purpose |
|---------|---------|
| Alpaca port / name | Server identity for clients |
| Status cache | `cache_enabled`, `cache_ttl_seconds` |
| Safety | fail-safe rules, `max_state_age_seconds` |
| Safety monitors | List of weather/safety entities |
| Domes | List of roof/shutter devices |

See `ha_alpaca_bridge/DOCS.md` for field details.

## MVP scope

**Supported:** Management API, `SafetyMonitor`, `Dome` (shutter/roof), status cache, fail-safe behaviour.

**Not supported:** rotating dome, `ObservingConditions`, external Home Assistant instances.

## Development

```bash
pip install -r ha_alpaca_bridge/requirements.txt -r requirements-dev.txt
pytest
```

Tests use `tests/fixtures/options.json` (same format as `/data/options.json` in the add-on).

## Fail-safe behaviour

| Situation | Behaviour |
|-----------|-----------|
| Home Assistant unreachable | `Connected=false`, `IsSafe=false` |
| Unknown / unavailable state | `IsSafe=false`, `ShutterStatus=error` |
| Stale cached state | `IsSafe=false`, `ShutterStatus=error` |
| Unsafe weather | `OpenShutter` refused |
| No safety monitor (default) | `OpenShutter` refused |
| Unsafe weather | `CloseShutter` still allowed |

## License

MIT
