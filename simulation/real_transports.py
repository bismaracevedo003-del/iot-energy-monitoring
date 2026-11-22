import json
import os
import math

from energy_meter import EnergyMeter, METER_CONFIG
from mqtt_broker import MQTTBroker

MQTT_DEFAULTS = {
    'MQTT_PORT': '1883',
    'MQTT_QOS': '1',
    'MQTT_RETAIN': 'false',
    'MQTT_TIMEOUT': '5',
    'MQTT_TOPIC_PREFIX': 'plant/energy',
}
MODBUS_DEFAULTS = {
    'MODBUS_PORT': '502',
    'MODBUS_TIMEOUT': '3',
    'MODBUS_REGISTER_TYPE': 'input',
}


def topic_prefix():
    return os.environ.get('MQTT_TOPIC_PREFIX', 'plant/energy')


def _boolean(name, default):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ('true', '1', 'yes', 'on')


def read_mqtt_settings():
    settings = {name: os.environ.get(name, default) for name, default in MQTT_DEFAULTS.items()}
    settings.update({
        'host': os.environ.get('MQTT_HOST'),
        'user': os.environ.get('MQTT_USER'),
        'password': os.environ.get('MQTT_PASSWORD'),
        'tls': _boolean('MQTT_TLS', False),
        'tls_ca': os.environ.get('MQTT_TLS_CA'),
        'client_id': os.environ.get('MQTT_CLIENT_ID', 'energy-gateway'),
    })
    return {
        'host': settings['host'],
        'port': int(settings['MQTT_PORT']),
        'user': settings['user'],
        'password': settings['password'],
        'tls': settings['tls'],
        'tls_ca': settings['tls_ca'],
        'client_id': settings['client_id'],
        'topic_prefix': settings['MQTT_TOPIC_PREFIX'],
        'qos': int(settings['MQTT_QOS']),
        'retain': _boolean('MQTT_RETAIN', False),
        'timeout': float(settings['MQTT_TIMEOUT']),
    }


def read_modbus_settings():
    raw = os.environ.get('MODBUS_METERS')
    if not raw:
        raise RuntimeError('MODE=real requires MODBUS_METERS with the register map per meter')
    try:
        meters = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f'MODE=real invalid MODBUS_METERS JSON: {error}') from error
    if not isinstance(meters, dict) or not meters:
        raise RuntimeError('MODE=real MODBUS_METERS must be a non-empty JSON object')

    for meter_id, config in meters.items():
        if meter_id not in METER_CONFIG:
            raise RuntimeError(f'MODE=real MODBUS_METERS has unknown meter: {meter_id}')
        if not isinstance(config, dict) or 'unit_id' not in config or 'registers' not in config:
            raise RuntimeError(f'MODE=real MODBUS_METERS[{meter_id}] needs unit_id and registers')
        if not isinstance(config['registers'], dict) or not config['registers']:
            raise RuntimeError(f'MODE=real MODBUS_METERS[{meter_id}].registers must be non-empty')

    settings = {name: os.environ.get(name, default) for name, default in MODBUS_DEFAULTS.items()}
    return {
        'host': os.environ.get('MODBUS_HOST'),
        'port': int(settings['MODBUS_PORT']),
        'timeout': float(settings['MODBUS_TIMEOUT']),
        'register_type': settings['MODBUS_REGISTER_TYPE'].strip().lower(),
        'meters': meters,
    }


class RealMqttPublisher:
    def __init__(self, settings):
        self.settings = settings
        self.mqtt = None
        self.client = None
        self.connected = False

    def connect(self):
        if not self.settings['host']:
            raise RuntimeError('MODE=real requires MQTT_HOST; real mode never uses the in-memory broker')
        if self.settings['tls'] and _boolean('REAL_STRICT', True) and not self.settings['tls_ca']:
            raise RuntimeError('MODE=real with MQTT_TLS=true and REAL_STRICT=true requires MQTT_TLS_CA')
        try:
            import paho.mqtt.client as mqtt
        except ImportError as error:
            raise RuntimeError(
                'MODE=real MQTT transport requires paho-mqtt; install it with: '
                'pip install -r requirements-real.txt'
            ) from error
        self.mqtt = mqtt
        self.client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2, client_id=self.settings['client_id']
        )
        if self.settings['user']:
            self.client.username_pw_set(self.settings['user'], self.settings['password'])
        if self.settings['tls']:
            self.client.tls_set(ca_certs=self.settings['tls_ca'])
        try:
            self.client.connect(self.settings['host'], self.settings['port'], keepalive=60)
            self.client.loop_start()
        except Exception as error:
            raise RuntimeError(f'MODE=real MQTT connection failed: {error}') from error
        self.connected = True
        return self

    def publish(self, topic, payload):
        if not self.connected:
            raise RuntimeError('RealMqttPublisher is not connected')
        info = self.client.publish(
            topic,
            json.dumps(payload),
            qos=self.settings['qos'],
            retain=self.settings['retain'],
        )
        info.wait_for_publish(timeout=self.settings['timeout'])
        if info.rc != self.mqtt.MQTT_ERR_SUCCESS:
            raise RuntimeError(f'MODE=real MQTT publish failed with code {info.rc}')

    def close(self):
        if self.client is not None:
            self.client.loop_stop()
            self.client.disconnect()
            self.client = None
        self.connected = False


class ModbusEnergyMeter:
    def __init__(self, meter_id, config, client, settings):
        self.meter_id = meter_id
        self.config = METER_CONFIG[meter_id]
        self.client = client
        self.unit_id = int(config['unit_id'])
        self.registers = config['registers']
        self.register_type = settings['register_type']

    def read_values(self):
        values = {}
        for field, definition in self.registers.items():
            if not isinstance(definition, dict) or 'address' not in definition:
                raise RuntimeError(f'MODBUS_METERS[{self.meter_id}].{field} needs an address')
            result = self._read_register(int(definition['address']))
            values[field] = float(result.registers[0]) * float(definition.get('scale', 1))
        return values

    def sample(self, ts, tariff):
        values = self.read_values()
        voltage = max(0.0, float(values.get('voltage_v', 400.0)))
        power = max(0.0, float(values.get('power_kw', 0.0)))
        power_factor = max(0.1, min(1.0, float(values.get('power_factor', 0.95))))
        current = float(values.get('current_a', 0.0))
        if 'current_a' not in values and voltage:
            current = power * 1000.0 / (math.sqrt(3) * voltage * power_factor)
        return {
            'meter_id': self.meter_id,
            'location': self.config['location'],
            'ts': round(float(ts), 2),
            'voltage_v': round(voltage, 2),
            'current_a': round(current, 2),
            'power_kw': round(power, 2),
            'energy_kwh': round(float(values.get('energy_kwh', 0.0)), 4),
            'power_factor': round(power_factor, 3),
            'frequency_hz': round(float(values.get('frequency_hz', 50.0)), 3),
            'tariff': tariff,
            'peak_kw': self.config['peak_kw'],
        }

    def _read_register(self, address):
        method = (
            self.client.read_input_registers
            if self.register_type == 'input'
            else self.client.read_holding_registers
        )
        result = method(address, count=1, slave=self.unit_id)
        if result.isError():
            raise RuntimeError(
                f'MODE=real Modbus read failed for {self.meter_id} at register {address}: {result}'
            )
        return result


def create_gateway_parts(sample_interval):
    mode = (os.environ.get('MODE') or 'simulation').strip().lower()
    if mode == 'simulation':
        meters = {
            meter_id: EnergyMeter(meter_id, sample_interval=sample_interval)
            for meter_id in METER_CONFIG
        }
        return meters, MQTTBroker(), None, None
    if mode != 'real':
        raise RuntimeError(f'Unsupported MODE: {mode} (use simulation or real)')

    publisher = RealMqttPublisher(read_mqtt_settings()).connect()
    try:
        modbus = read_modbus_settings()
        if not modbus['host']:
            raise RuntimeError('MODE=real requires MODBUS_HOST; real mode never uses simulated meters')
        if modbus['register_type'] not in ('input', 'holding'):
            raise RuntimeError(f"MODE=real invalid MODBUS_REGISTER_TYPE: {modbus['register_type']}")
        try:
            from pymodbus.client import ModbusTcpClient
        except ImportError as error:
            raise RuntimeError(
                'MODE=real Modbus meters require pymodbus; install it with: '
                'pip install -r requirements-real.txt'
            ) from error
        client = ModbusTcpClient(modbus['host'], port=modbus['port'], timeout=modbus['timeout'])
        if not client.connect():
            raise RuntimeError(
                f"MODE=real Modbus connection failed: {modbus['host']}:{modbus['port']}"
            )
        meters = {
            meter_id: ModbusEnergyMeter(meter_id, config, client, modbus)
            for meter_id, config in modbus['meters'].items()
        }
        for meter in meters.values():
            meter.read_values()
    except Exception:
        publisher.close()
        raise
    return meters, MQTTBroker(), publisher, client
