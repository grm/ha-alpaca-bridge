# Home Assistant Add-on

Expose Home Assistant weather and roof entities as ASCOM Alpaca `SafetyMonitor`, `Dome`, and `ObservingConditions` devices.

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

### Weather / Observing Conditions

Map Home Assistant numeric sensors to ASCOM `ObservingConditions` (NINA **Weather** tab). Leave a field empty to mark that sensor as not implemented.

| Field | ASCOM property | Expected units |
|-------|----------------|----------------|
| temperature_entity | Temperature | °C |
| humidity_entity | Humidity | % |
| pressure_entity | Pressure | hPa |
| rain_rate_entity | RainRate | mm/h |
| wind_speed_entity | WindSpeed | m/s |
| wind_direction_entity | WindDirection | degrees |
| wind_gust_entity | WindGust | m/s |
| cloud_cover_entity | CloudCover | % |
| dew_point_entity | DewPoint | °C |
| sky_brightness_entity | SkyBrightness | Lux |
| sky_quality_entity | SkyQuality | mag/arcsec² |
| sky_temperature_entity | SkyTemperature | °C |
| star_fwhm_entity | StarFWHM | arcsec |
| average_period | AveragePeriod | seconds (`0` = instantaneous) |

Values are passed through from Home Assistant as floats. Configure HA sensors in the units above (or convert with template sensors).

## Connecting clients

Point ASCOM Alpaca clients to:

```text
http://<home-assistant-host>:11111
```

Use the host IP of your Home Assistant machine and the configured Alpaca port.

### Network discovery (optional)

By default, clients must be configured manually with the host and port above.
Enabling **Enable network discovery** (`alpaca_discovery_enabled`) makes the
add-on respond to Alpaca's UDP broadcast discovery protocol (port 32227), so
compatible clients (NINA, ASCOM Remote, ...) can find it automatically on the
local network.

This option is **off by default**. Only enable it on a trusted local network,
since any device able to reach that UDP port can learn the Alpaca server
address.

In NINA:

- **Safety Monitor** → bridge SafetyMonitor
- **Dome** → bridge Dome
- **Weather** → bridge ObservingConditions

## Fail-safe behaviour

- Home Assistant unreachable → unsafe / not connected
- Unknown or stale states → unsafe / shutter error / ObservingConditions invalid operation
- `OpenShutter` blocked when unsafe
- `CloseShutter` always allowed when Home Assistant is reachable
