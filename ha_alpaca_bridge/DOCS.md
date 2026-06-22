# Home Assistant Add-on

Expose Home Assistant weather and roof entities as ASCOM Alpaca `SafetyMonitor` and `Dome` devices.

## Configuration

All settings are managed from the add-on **Configuration** tab in Home Assistant.

### Safety Monitors

Map a `binary_sensor` (or any entity) to Alpaca `IsSafe`:

| Field | Description |
|-------|-------------|
| device_number | Alpaca device index (0, 1, …) |
| name | Display name in Alpaca clients |
| unique_id | Stable identifier |
| entity | Home Assistant entity id |
| safe_state | Entity state meaning “safe” (usually `on`) |

### Domes / Roofs

Map a `cover` entity to Alpaca shutter control:

| Field | Description |
|-------|-------------|
| shutter_entity | Cover entity for roof state |
| safety_monitor_device_number | Linked monitor (`-1` = none) |
| open/close service | Defaults to `cover.open_cover` / `cover.close_cover` |

## Connecting clients

Point ASCOM Alpaca clients to:

```text
http://<home-assistant-host>:11111
```

Use the host IP of your Home Assistant machine and the configured Alpaca port.

## Fail-safe behaviour

- Home Assistant unreachable → unsafe / not connected
- Unknown or stale states → unsafe / shutter error
- `OpenShutter` blocked when unsafe
- `CloseShutter` always allowed when Home Assistant is reachable
