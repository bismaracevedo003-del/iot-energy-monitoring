# Data model

## Telemetry payload

```json
{
  "meter_id": "LINE-01",
  "ts": 12.0,
  "voltage_v": 400.1,
  "current_a": 42.3,
  "power_kw": 28.4,
  "energy_kwh": 9.84,
  "power_factor": 0.91,
  "frequency_hz": 50.01,
  "tariff": "mid-peak"
}
```

## Meter

| Field | Meaning |
| --- | --- |
| `meter_id` | Unique meter identifier |
| `location` | Physical area label |
| `base_kw` | Normalized base load |
| `profile` | Load profile name |
| `peak_kw` | Demand alarm threshold |

## Event

An event is a telemetry message enriched with tariff, cost and anomaly flags. Events are kept in a bounded deque (default 500) for the dashboard and tests.

## Summary

The summary contains total power, accumulated energy, estimated cost, CO₂, demand peak, anomaly count and one entry per meter.
