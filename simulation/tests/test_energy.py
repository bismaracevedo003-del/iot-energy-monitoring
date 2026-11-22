import json
import sys
import time
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from analytics import (  # noqa: E402
    AnalyticsEngine,
    TARIFF_RATES,
    detect_anomalies,
    tariff_for_hour,
    tariff_rate,
)
from energy_gateway import TOPIC_PREFIX, EnergyGateway  # noqa: E402
from energy_meter import EnergyMeter  # noqa: E402
from energy_server import EnergyApplication  # noqa: E402
from mqtt_broker import MQTTBroker  # noqa: E402


def sample(meter_id='LINE-01', **overrides):
    payload = {
        'meter_id': meter_id,
        'location': 'Assembly line',
        'ts': 1.0,
        'voltage_v': 400.0,
        'current_a': 50.0,
        'power_kw': 80.0,
        'energy_kwh': 1.0,
        'power_factor': 0.92,
        'frequency_hz': 50.0,
        'tariff': 'mid-peak',
        'peak_kw': 130.0,
    }
    payload.update(overrides)
    return payload


class BrokerTests(unittest.TestCase):
    def test_publish_subscribe(self):
        broker = MQTTBroker()
        received = []
        broker.subscribe('a/b', lambda topic, payload: received.append((topic, payload)))
        broker.publish('a/b', {'v': 1})
        self.assertEqual(received, [('a/b', {'v': 1})])

    def test_retained_message(self):
        broker = MQTTBroker()
        broker.publish('a/b', {'v': 7})
        received = []
        broker.subscribe('a/b', lambda topic, payload: received.append(payload))
        self.assertEqual(received, [{'v': 7}])

    def test_counters_and_topics(self):
        broker = MQTTBroker()
        broker.publish('a/b', 1)
        broker.publish('a/b', 2)
        broker.publish('c/d', 3)
        self.assertEqual(broker.count('a/b'), 2)
        self.assertEqual(broker.count(), 3)
        self.assertEqual(broker.topics(), ['a/b', 'c/d'])

    def test_clear(self):
        broker = MQTTBroker()
        broker.subscribe('a/b', lambda topic, payload: None)
        broker.publish('a/b', 1)
        broker.clear()
        self.assertEqual(broker.count(), 0)
        self.assertEqual(broker.retained('a/b'), None)


class MeterTests(unittest.TestCase):
    def test_sample_fields(self):
        meter = EnergyMeter('FEEDER-01')
        data = meter.sample(3600, 'off-peak')
        self.assertEqual(data['meter_id'], 'FEEDER-01')
        self.assertGreater(data['power_kw'], 0)
        self.assertGreater(data['current_a'], 0)
        self.assertLess(data['voltage_v'], 410)
        self.assertEqual(data['tariff'], 'off-peak')

    def test_profiles_differ(self):
        feeder = EnergyMeter('FEEDER-01').sample(12 * 3600, 'mid-peak')['power_kw']
        hvac = EnergyMeter('HVAC-01').sample(12 * 3600, 'mid-peak')['power_kw']
        self.assertGreater(feeder, hvac)

    def test_injection_override(self):
        meter = EnergyMeter('LINE-01')
        meter.set_injection(power_kw=500, voltage_v=360)
        data = meter.sample(1, 'peak')
        self.assertEqual(data['power_kw'], 500)
        self.assertEqual(data['voltage_v'], 360)
        meter.clear_injection()
        self.assertNotEqual(meter.sample(1, 'peak')['voltage_v'], 360)


class AnalyticsTests(unittest.TestCase):
    def test_tariff_schedule(self):
        self.assertEqual(tariff_for_hour(3), 'off-peak')
        self.assertEqual(tariff_for_hour(10), 'mid-peak')
        self.assertEqual(tariff_for_hour(18), 'peak')
        self.assertEqual(tariff_for_hour(25), 'off-peak')

    def test_tariff_rates(self):
        self.assertEqual(tariff_rate('peak'), TARIFF_RATES['peak'])
        self.assertEqual(tariff_rate('unknown'), TARIFF_RATES['off-peak'])

    def test_anomaly_rules(self):
        payload = sample(power_kw=500, voltage_v=360, power_factor=0.7, frequency_hz=49.4)
        self.assertEqual(detect_anomalies(payload), [
            'DEMAND_SPIKE', 'VOLTAGE_SAG', 'LOW_POWER_FACTOR', 'FREQUENCY_DEVIATION',
        ])

    def test_no_anomaly_normal(self):
        self.assertEqual(detect_anomalies(sample()), [])

    def test_record_and_summary(self):
        engine = AnalyticsEngine()
        engine.record(sample('FEEDER-01'))
        engine.record(sample('LINE-01', power_kw=200))
        summary = engine.summary()
        self.assertEqual(summary['total_kw'], 280)
        self.assertGreater(summary['energy_kwh'], 0)
        self.assertEqual(len(summary['meters']), 2)
        self.assertEqual(summary['demand_peak_kw'], 200)

    def test_bounded_events(self):
        engine = AnalyticsEngine(max_events=3)
        for index in range(5):
            engine.record(sample(ts=index))
        self.assertEqual(len(engine.events), 3)
        self.assertEqual(engine.events[-1]['ts'], 4)

    def test_reset(self):
        engine = AnalyticsEngine()
        engine.record(sample())
        engine.reset()
        self.assertEqual(engine.summary()['energy_kwh'], 0)
        self.assertEqual(engine.anomaly_count, 0)


class GatewayTests(unittest.TestCase):
    def test_tick_publishes(self):
        gateway = EnergyGateway()
        gateway.tick()
        self.assertEqual(gateway.broker.count(f'{TOPIC_PREFIX}/meter/FEEDER-01/telemetry'), 1)
        self.assertEqual(gateway.broker.count(f'{TOPIC_PREFIX}/meter/HVAC-01/telemetry'), 1)
        self.assertEqual(gateway.broker.count(f'{TOPIC_PREFIX}/meter/LINE-01/telemetry'), 1)
        self.assertIsNotNone(gateway.broker.retained(f'{TOPIC_PREFIX}/analytics/summary'))

    def test_state_shape(self):
        state = EnergyGateway().start().state()
        self.assertIn('gateway', state)
        self.assertIn('summary', state)
        self.assertIn('broker', state)
        self.assertIn('events', state)

    def test_injection_creates_event(self):
        gateway = EnergyGateway()
        gateway.inject('LINE-01', power_kw=500)
        gateway.tick()
        anomalies = [item for event in gateway.state()['events'] for item in event['anomalies']]
        self.assertIn('DEMAND_SPIKE', anomalies)

    def test_gateway_reset(self):
        gateway = EnergyGateway()
        gateway.tick()
        gateway.reset()
        self.assertEqual(gateway.ts, 0)
        self.assertEqual(gateway.broker.count(), 0)

    def test_unknown_meter(self):
        with self.assertRaises(ValueError):
            EnergyGateway().inject('BAD', power_kw=10)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.app = EnergyApplication(port=0).start()
        time.sleep(1.2)

    def tearDown(self):
        self.app.stop()

    def get(self, path):
        with urllib.request.urlopen(f'http://127.0.0.1:{self.app.port}{path}') as response:
            return json.loads(response.read())

    def post(self, path, payload):
        request = urllib.request.Request(
            f'http://127.0.0.1:{self.app.port}{path}',
            data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read())

    def test_hmi_and_assets(self):
        for path, token in (('/', b'IoT Energy Monitoring'), ('/app.js', b'fetch'), ('/styles.css', b'canvas')):
            with urllib.request.urlopen(f'http://127.0.0.1:{self.app.port}{path}') as response:
                self.assertEqual(response.status, 200)
                self.assertIn(token, response.read())

    def test_api_summary(self):
        summary = self.get('/api/summary')
        self.assertIn('total_kw', summary)
        self.assertEqual(len(summary['meters']), 3)

    def test_api_inject_and_reset(self):
        self.post('/api/inject', {'meter_id': 'LINE-01', 'values': {'power_kw': 500}})
        time.sleep(1.2)
        events = self.get('/api/events')
        self.assertTrue(any('DEMAND_SPIKE' in event['anomalies'] for event in events))
        self.post('/api/reset', {})
        self.assertEqual(self.get('/api/events'), [])


if __name__ == '__main__':
    unittest.main()
