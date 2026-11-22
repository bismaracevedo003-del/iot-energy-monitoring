# Test plan

| ID | Case | Expected | Status |
| --- | --- | --- | --- |
| T-01 | Broker publish/subscribe | Callback receives topic and payload | Pass |
| T-02 | Retained message | New subscriber gets last value | Pass |
| T-03 | Topic counters | Counters match publish count | Pass |
| T-04 | Meter sampling | Telemetry fields in range | Pass |
| T-05 | Meter profiles | Load differs by profile | Pass |
| T-06 | Tariff schedule | Correct tariff by hour | Pass |
| T-07 | Tariff rates | Cost uses active rate | Pass |
| T-08 | Energy accumulation | kWh increases with power | Pass |
| T-09 | Demand spike | Anomaly raised over threshold | Pass |
| T-10 | Voltage sag | Anomaly raised below 380 V | Pass |
| T-11 | Low power factor | Anomaly raised below 0.85 | Pass |
| T-12 | Frequency deviation | Anomaly raised outside band | Pass |
| T-13 | Summary aggregation | Totals include all meters | Pass |
| T-14 | Event history | Bounded deque keeps newest events | Pass |
| T-15 | Gateway tick | Publishes one message per meter | Pass |
| T-16 | Gateway summary | Summary exposed by API | Pass |
| T-17 | HMI page | HTTP 200 with dashboard title | Pass |
| T-18 | Static assets | JS and CSS served | Pass |
| T-19 | Inject telemetry | Anomaly appears in events | Pass |
| T-20 | Reset | Counters and events cleared | Pass |
| T-21 | Normal telemetry | No anomaly flags | Pass |
| T-22 | Gateway reset | Timestamp, broker and analytics cleared | Pass |

## Run

```powershell
python -m unittest discover -s simulation/tests -v
```

## Hardware validation

Not performed. Real deployment requires calibrated meters, secure MQTT broker, time synchronization and validated tariff inputs.
