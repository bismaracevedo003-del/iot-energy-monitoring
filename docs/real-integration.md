# Energy gateway real-mode integration

## Default behavior (unchanged)

With `MODE` unset (or `MODE=simulation`), `create_gateway_parts()` creates the three simulated
meters and the in-memory `MQTTBroker`. The REST API, HMI, analytics and all existing tests are
unchanged.

## Activating real transports

```powershell
pip install -r requirements-real.txt
$env:MODE='real'
$env:MQTT_HOST='broker.example.internal'
$env:MODBUS_HOST='192.168.1.30'
# set MODBUS_METERS from config/real.env.example with the real register map
python simulation/energy_server.py
```

In `MODE=real` the gateway requires:

- `MQTT_HOST` and `MODBUS_HOST`, plus a valid `MODBUS_METERS` JSON object.
- `paho-mqtt` and `pymodbus`, imported lazily inside `connect()`. Missing packages, connection
  failures or unreadable registers raise a clear startup error. There is no in-memory fallback.
- With `REAL_STRICT=true` and `MQTT_TLS=true`, `MQTT_TLS_CA` is mandatory.

`RealMqttPublisher` publishes the same topics as the simulator (`<MQTT_TOPIC_PREFIX>/meter/...`,
`/gateway/events`, `/analytics/summary`, `/gateway/status`) with configurable QoS and retain flag.
`ModbusEnergyMeter` reads input (or holding) registers per meter unit and produces the same
sample contract as `EnergyMeter`. The local in-memory broker is kept as a cache for the HMI, while
a real broker receives every MQTT message.

Real mode rejects fault injection (`/api/inject`, `/api/clear`) and does not reset real meter
energy counters on `/api/reset`; only the analytics window is reset.

## Real HMI/SCADA deployment

| Item | Recommendation for this repo |
| --- | --- |
| Host/port | Run the gateway on an edge host that can reach Modbus TCP devices on port 502. Python serves the HMI/API on `127.0.0.1:4050`; expose only the reverse proxy to users. |
| TLS / reverse proxy | Terminate HTTPS on nginx/Traefik (443) and proxy `/` and `/api/*` to 4050. Use `MQTT_TLS=true` with port 8883 and a CA file. Keep Modbus TCP inside an isolated OT VLAN or tunnel it through a secured protocol converter. |
| Authentication | Enforce SSO/basic auth at the reverse proxy. Use a dedicated MQTT service account with write access limited to `MQTT_TOPIC_PREFIX`, and restrict `POST /api/*` to operator roles. |
| Safety | These are read-only energy meters; no actuator writes are implemented. Billing-grade accuracy and safety interlocks must remain in certified meters/relays, not in this Python gateway. |

## Verification without hardware or broker

```powershell
python -m unittest discover -s simulation/tests -v
```

Tests leave `MODE` unset, use the in-memory broker and do not import optional packages.
To verify strict behavior, set `MODE=real` without `MQTT_HOST` and confirm startup fails instead
of starting the simulated meters.
