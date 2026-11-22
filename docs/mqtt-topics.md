# MQTT topics

| Topic | Payload | Retained |
| --- | --- | --- |
| `plant/energy/meter/{meter_id}/telemetry` | Telemetry JSON | Yes |
| `plant/energy/gateway/status` | Gateway status JSON | Yes |
| `plant/energy/gateway/events` | Event JSON | No |
| `plant/energy/analytics/summary` | Summary JSON | Yes |

## Broker behavior

- `publish(topic, payload)` increments the topic counter.
- Retained topics return the last payload to new subscribers.
- Subscribers are plain Python callables: `callback(topic, payload)`.

## Example

```python
broker.subscribe('plant/energy/meter/LINE-01/telemetry', print)
broker.publish('plant/energy/meter/LINE-01/telemetry', {'power_kw': 28.4})
```

The bridge is intentionally in-memory; no network listener or MQTT client library is used.
