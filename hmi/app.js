const $ = (id) => document.getElementById(id);
let history = [];

async function api(path, options = {}) {
  const response = await fetch(path, {
    method: options.method || 'GET',
    headers: { 'Content-Type': 'application/json' },
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  return response.json();
}

function drawChart() {
  const canvas = $('chart');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#0b1220';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  if (!history.length) return;
  const max = Math.max(...history, 10);
  ctx.strokeStyle = '#243650';
  ctx.beginPath();
  ctx.moveTo(40, 10); ctx.lineTo(40, canvas.height - 25); ctx.lineTo(canvas.width - 10, canvas.height - 25);
  ctx.stroke();
  ctx.fillStyle = '#91a7c4';
  ctx.font = '12px Segoe UI';
  ctx.fillText(`${max.toFixed(0)} kW`, 45, 20);
  ctx.fillText('now', canvas.width - 45, canvas.height - 8);
  ctx.strokeStyle = '#4cc9f0';
  ctx.lineWidth = 2;
  ctx.beginPath();
  history.forEach((value, index) => {
    const x = 40 + index * (canvas.width - 55) / Math.max(1, history.length - 1);
    const y = canvas.height - 25 - value * (canvas.height - 45) / max;
    index ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
  });
  ctx.stroke();
}

function render(state) {
  const s = state.summary;
  $('demand').textContent = s.total_kw.toFixed(1);
  $('energy').textContent = s.energy_kwh.toFixed(2);
  $('cost').textContent = s.cost_usd.toFixed(3);
  $('co2').textContent = s.co2_kg.toFixed(2);
  $('peak').textContent = s.demand_peak_kw.toFixed(1);
  $('anomalies').textContent = s.anomaly_count;
  $('tariff').textContent = s.tariff.toUpperCase();
  $('tariff').className = `tariff tariff-${s.tariff}`;
  $('messages').textContent = state.broker.messages;
  $('topics').textContent = state.broker.topics.length;
  $('topicList').innerHTML = state.broker.topics.map((t) => `<div>${t}</div>`).join('');
  $('meters').innerHTML = s.meters.map((m) => `<tr><td>${m.meter_id}</td><td>${m.power_kw}</td><td>${m.voltage_v}</td><td>${m.power_factor}</td><td>${m.anomalies.join(', ') || 'OK'}</td></tr>`).join('');
  $('events').innerHTML = state.events.length
    ? state.events.slice(0, 10).map((e) => `<li><strong>${e.meter_id}</strong> ${e.anomalies.join(', ')} <small>t=${e.ts}s</small></li>`).join('')
    : '<li>No anomalies</li>';
  history.push(s.total_kw);
  history = history.slice(-80);
  drawChart();
}

async function refresh() {
  render(await api('/api/state'));
}

const injections = {
  spike: { power_kw: 900 },
  sag: { voltage_v: 360 },
  pf: { power_factor: 0.70 },
  freq: { frequency_hz: 49.5 },
};

document.querySelectorAll('[data-inject]').forEach((button) => {
  button.onclick = async () => {
    await api('/api/inject', { method: 'POST', body: { meter_id: 'LINE-01', values: injections[button.dataset.inject] } });
    refresh();
  };
});
$('clear').onclick = () => api('/api/clear', { method: 'POST', body: {} }).then(refresh);
$('reset').onclick = async () => { await api('/api/reset', { method: 'POST', body: {} }); history = []; refresh(); };

refresh();
setInterval(refresh, 1000);
