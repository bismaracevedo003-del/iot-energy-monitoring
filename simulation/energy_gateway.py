import time

from analytics import AnalyticsEngine, tariff_for_hour
from energy_meter import METER_CONFIG, EnergyMeter
from mqtt_broker import MQTTBroker

TOPIC_PREFIX = 'plant/energy'


class EnergyGateway:
    def __init__(self, sample_interval=1.0, start_hour=8):
        self.broker = MQTTBroker()
        self.analytics = AnalyticsEngine(sample_interval=sample_interval)
        self.sample_interval = float(sample_interval)
        self.start_hour = start_hour
        self.ts = 0.0
        self.running = False
        self.meters = {
            meter_id: EnergyMeter(meter_id, sample_interval=sample_interval)
            for meter_id in METER_CONFIG
        }

    def telemetry_topic(self, meter_id):
        return f'{TOPIC_PREFIX}/meter/{meter_id}/telemetry'

    def subscribe(self, topic, callback):
        self.broker.subscribe(topic, callback)

    def start(self):
        self.running = True
        return self

    def stop(self):
        self.running = False

    def tick(self):
        self.ts += self.sample_interval
        hour = (self.start_hour + self.ts / 3600.0) % 24
        tariff = tariff_for_hour(hour)
        for meter_id, meter in self.meters.items():
            payload = meter.sample(self.ts, tariff)
            topic = self.telemetry_topic(meter_id)
            self.broker.publish(topic, payload)
            event = self.analytics.record(payload)
            if event['anomalies']:
                self.broker.publish(f'{TOPIC_PREFIX}/gateway/events', event)
        summary = self.analytics.summary()
        self.broker.publish(f'{TOPIC_PREFIX}/analytics/summary', summary)
        self.broker.publish(f'{TOPIC_PREFIX}/gateway/status', {
            'running': self.running,
            'ts': round(self.ts, 2),
            'hour': round(hour, 2),
            'tariff': tariff,
            'meters': len(self.meters),
            'messages': self.broker.count(),
        })
        return summary

    def inject(self, meter_id, **values):
        if meter_id not in self.meters:
            raise ValueError(f'unknown meter: {meter_id}')
        self.meters[meter_id].set_injection(**values)

    def clear_injection(self, meter_id=None):
        if meter_id is None:
            for meter in self.meters.values():
                meter.clear_injection()
            return
        if meter_id not in self.meters:
            raise ValueError(f'unknown meter: {meter_id}')
        self.meters[meter_id].clear_injection()

    def reset(self):
        self.ts = 0.0
        self.analytics.reset()
        self.broker.clear()
        for meter in self.meters.values():
            meter.energy_kwh = 0.0
            meter.clear_injection()

    def state(self):
        return {
            'gateway': self.broker.retained(f'{TOPIC_PREFIX}/gateway/status') or {
                'running': self.running, 'ts': 0.0, 'hour': self.start_hour,
                'tariff': tariff_for_hour(self.start_hour), 'meters': len(self.meters), 'messages': 0,
            },
            'summary': self.analytics.summary(),
            'broker': {
                'topics': self.broker.topics(),
                'messages': self.broker.count(),
            },
            'events': list(self.analytics.events)[-30:][::-1],
            'source': 'simulator',
        }


def run_demo(seconds=10):
    gateway = EnergyGateway().start()
    try:
        for _ in range(int(seconds)):
            summary = gateway.tick()
            print(f"{summary['total_kw']:7.2f} kW  {summary['cost_usd']:.4f} USD  {summary['anomaly_count']} anomalies")
            time.sleep(1)
    finally:
        gateway.stop()


if __name__ == '__main__':
    run_demo()
