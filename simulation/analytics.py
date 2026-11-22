from collections import deque

TARIFF_RATES = {'off-peak': 0.09, 'mid-peak': 0.16, 'peak': 0.28}
CO2_KG_PER_KWH = 0.42


def tariff_for_hour(hour):
    hour = int(hour) % 24
    if 16 <= hour <= 19:
        return 'peak'
    if 7 <= hour <= 15 or 20 <= hour <= 21:
        return 'mid-peak'
    return 'off-peak'


def tariff_rate(tariff):
    return TARIFF_RATES.get(tariff, TARIFF_RATES['off-peak'])


def detect_anomalies(payload):
    anomalies = []
    if payload['power_kw'] > payload['peak_kw']:
        anomalies.append('DEMAND_SPIKE')
    if payload['voltage_v'] < 380.0:
        anomalies.append('VOLTAGE_SAG')
    if payload['power_factor'] < 0.85:
        anomalies.append('LOW_POWER_FACTOR')
    if not 49.8 <= payload['frequency_hz'] <= 50.2:
        anomalies.append('FREQUENCY_DEVIATION')
    return anomalies


class AnalyticsEngine:
    def __init__(self, max_events=500, sample_interval=1.0):
        self.events = deque(maxlen=max_events)
        self.sample_interval = float(sample_interval)
        self.latest = {}
        self.energy_total_kwh = 0.0
        self.cost_total = 0.0
        self.demand_peak_kw = 0.0
        self.anomaly_count = 0

    def record(self, payload):
        tariff = payload.get('tariff', 'off-peak')
        increment_kwh = payload['power_kw'] * self.sample_interval / 3600.0
        cost = increment_kwh * tariff_rate(tariff)
        anomalies = detect_anomalies(payload)
        event = dict(payload)
        event.update({
            'increment_kwh': round(increment_kwh, 5),
            'cost': round(cost, 5),
            'anomalies': anomalies,
        })
        self.events.append(event)
        self.latest[payload['meter_id']] = event
        self.energy_total_kwh += increment_kwh
        self.cost_total += cost
        self.demand_peak_kw = max(self.demand_peak_kw, payload['power_kw'])
        self.anomaly_count += len(anomalies)
        return event

    def summary(self):
        meters = []
        for meter_id in sorted(self.latest):
            event = self.latest[meter_id]
            meters.append({
                'meter_id': meter_id,
                'location': event['location'],
                'power_kw': event['power_kw'],
                'voltage_v': event['voltage_v'],
                'current_a': event['current_a'],
                'power_factor': event['power_factor'],
                'frequency_hz': event['frequency_hz'],
                'energy_kwh': event['energy_kwh'],
                'tariff': event['tariff'],
                'anomalies': event['anomalies'],
            })
        return {
            'source': 'simulator',
            'total_kw': round(sum(item['power_kw'] for item in meters), 2),
            'energy_kwh': round(self.energy_total_kwh, 4),
            'cost_usd': round(self.cost_total, 4),
            'co2_kg': round(self.energy_total_kwh * CO2_KG_PER_KWH, 4),
            'demand_peak_kw': round(self.demand_peak_kw, 2),
            'anomaly_count': self.anomaly_count,
            'tariff': tariff_for_hour(0) if not meters else meters[0]['tariff'],
            'meters': meters,
        }

    def reset(self):
        self.events.clear()
        self.latest.clear()
        self.energy_total_kwh = 0.0
        self.cost_total = 0.0
        self.demand_peak_kw = 0.0
        self.anomaly_count = 0
