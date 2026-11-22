# Analytics rules

## Tariff

| Window | Rate (USD/kWh) |
| --- | ---: |
| `off-peak` | 0.09 |
| `mid-peak` | 0.16 |
| `peak` | 0.28 |

Default schedule by hour: 00-06 and 22-23 off-peak, 07-15 and 20-21 mid-peak, 16-19 peak.

## Anomalies

| Code | Rule |
| --- | --- |
| `DEMAND_SPIKE` | `power_kw` exceeds the meter `peak_kw` threshold |
| `VOLTAGE_SAG` | voltage below 380 V |
| `LOW_POWER_FACTOR` | power factor below 0.85 |
| `FREQUENCY_DEVIATION` | frequency outside 49.8-50.2 Hz |

## Estimates

- Energy increment: `power_kw * sample_hours`.
- Cost increment: `energy_kwh * tariff_rate`.
- CO₂: `energy_kwh * 0.42 kg/kWh`.

These are illustrative engineering estimates, not billing or regulatory calculations.
