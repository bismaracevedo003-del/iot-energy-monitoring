import math
import random

METER_CONFIG = {
    'FEEDER-01': {'location': 'Main switchgear', 'base_kw': 120.0, 'peak_kw': 180.0, 'profile': 'feeder'},
    'HVAC-01': {'location': 'Utility room', 'base_kw': 45.0, 'peak_kw': 75.0, 'profile': 'hvac'},
    'LINE-01': {'location': 'Assembly line', 'base_kw': 80.0, 'peak_kw': 130.0, 'profile': 'production'},
}


class EnergyMeter:
    def __init__(self, meter_id, config=None, sample_interval=1.0, seed=7):
        self.meter_id = meter_id
        self.config = config or METER_CONFIG[meter_id]
        self.sample_interval = float(sample_interval)
        self.random = random.Random(f'{meter_id}:{seed}')
        self.energy_kwh = 0.0
        self.injection = {}

    def set_injection(self, **values):
        self.injection.update(values)

    def clear_injection(self):
        self.injection.clear()

    def _profile_factor(self, ts):
        hour = (ts / 3600.0) % 24.0
        if self.config['profile'] == 'hvac':
            return 0.55 + 0.45 * max(0.0, math.sin(math.pi * (hour - 6) / 12))
        if self.config['profile'] == 'production':
            return 0.35 if hour < 6 or hour >= 22 else 0.85 + 0.15 * math.sin(math.pi * (hour - 6) / 12)
        return 0.75 + 0.25 * max(0.0, math.sin(math.pi * (hour - 5) / 14))

    def sample(self, ts, tariff):
        power_kw = self.config['base_kw'] * self._profile_factor(ts)
        power_kw *= 1.0 + self.random.uniform(-0.03, 0.03)
        voltage_v = 400.0 + self.random.uniform(-2.0, 2.0)
        power_factor = 0.92 + self.random.uniform(-0.02, 0.02)
        frequency_hz = 50.0 + self.random.uniform(-0.03, 0.03)
        values = {
            'power_kw': power_kw,
            'voltage_v': voltage_v,
            'power_factor': max(0.5, min(1.0, power_factor)),
            'frequency_hz': frequency_hz,
        }
        values.update(self.injection)
        power_kw = max(0.0, float(values['power_kw']))
        voltage_v = max(0.0, float(values['voltage_v']))
        power_factor = max(0.1, min(1.0, float(values['power_factor'])))
        current_a = power_kw * 1000.0 / (math.sqrt(3) * voltage_v * power_factor) if voltage_v else 0.0
        self.energy_kwh += power_kw * self.sample_interval / 3600.0
        return {
            'meter_id': self.meter_id,
            'location': self.config['location'],
            'ts': round(float(ts), 2),
            'voltage_v': round(voltage_v, 2),
            'current_a': round(current_a, 2),
            'power_kw': round(power_kw, 2),
            'energy_kwh': round(self.energy_kwh, 4),
            'power_factor': round(power_factor, 3),
            'frequency_hz': round(float(values['frequency_hz']), 3),
            'tariff': tariff,
            'peak_kw': self.config['peak_kw'],
        }
