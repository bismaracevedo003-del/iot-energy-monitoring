# IoT Energy Monitoring

**MQTT-style telemetry · Edge gateway · Tariff analysis · Anomaly detection · Web dashboard**

> **Nota (ES):** Proyecto de demostración. El broker, los medidores y la nube se simulan en Python; no se conecta a hardware real ni a un servicio MQTT público.

## 1. Goal

Simulate an industrial edge gateway that collects energy telemetry from several meters, publishes it to MQTT-style topics, applies tariff and anomaly rules, and exposes a live HMI with cost, demand, CO₂ and event history.

## 2. Scope

- Three simulated meters: `FEEDER-01`, `HVAC-01`, `LINE-01`.
- MQTT-style in-memory broker with topics, retained messages and subscribers.
- 15-minute tariff windows: off-peak, mid-peak and peak.
- Anomalies: demand spike, voltage sag, low power factor and frequency deviation.
- REST API and static HTML/JS dashboard.
- No external Python packages required.

## 3. Repository layout

```text
iot-energy-monitoring/
├── docs/
│   ├── architecture.md
│   ├── data-model.md
│   ├── mqtt-topics.md
│   ├── analytics-rules.md
│   └── test-plan.md
├── hmi/
│   ├── index.html
│   ├── app.js
│   └── styles.css
├── screenshots/
│   ├── dashboard.svg
│   └── telemetry-flow.svg
└── simulation/
    ├── mqtt_broker.py
    ├── energy_meter.py
    ├── analytics.py
    ├── energy_gateway.py
    ├── energy_server.py
    └── tests/
        └── test_energy.py
```

## 4. Stack

| Layer | Technology |
| --- | --- |
| Simulation | Python standard library |
| Messaging | MQTT-style in-memory broker |
| Analytics | Python tariff/anomaly rules |
| API | Python `http.server` |
| HMI | Static HTML/JS + Canvas |
| Tests | Python `unittest` |

## 5. Run

```powershell
cd "C:\Users\Bismarck Acevedo\Documents\Github\iot-energy-monitoring"
python -m unittest discover -s simulation/tests -v
python simulation/energy_server.py
```

Open `http://127.0.0.1:4050`.

Verified: **22 Python tests OK**; HMI smoke `Page=200`, three meters publishing, tariff/anomaly summary and reset confirmed.

## 6. Documents

- [Architecture](docs/architecture.md)
- [Data model](docs/data-model.md)
- [MQTT topics](docs/mqtt-topics.md)
- [Analytics rules](docs/analytics-rules.md)
- [Test plan](docs/test-plan.md)

## 7. Screenshots

- [Energy dashboard](screenshots/dashboard.svg)
- [Telemetry flow](screenshots/telemetry-flow.svg)
