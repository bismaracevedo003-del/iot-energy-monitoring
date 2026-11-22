import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from energy_gateway import EnergyGateway

HMI_ROOT = Path(__file__).resolve().parent.parent / 'hmi'


class EnergyApplication:
    def __init__(self, port=4050):
        self.gateway = EnergyGateway().start()
        self.http = ThreadingHTTPServer(('127.0.0.1', port), EnergyHandler)
        self.http.app = self
        self.stop_event = threading.Event()

    @property
    def port(self):
        return self.http.server_address[1]

    def start(self):
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        threading.Thread(target=self._simulation_loop, daemon=True).start()
        return self

    def stop(self):
        self.stop_event.set()
        self.gateway.stop()
        self.http.shutdown()
        self.http.server_close()

    def _simulation_loop(self):
        while not self.stop_event.is_set():
            self.gateway.tick()
            time.sleep(self.gateway.sample_interval)


class EnergyHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filename):
        path = HMI_ROOT / filename
        if not path.is_file():
            self.send_error(404)
            return
        content = path.read_bytes()
        content_type = {
            '.html': 'text/html; charset=utf-8',
            '.js': 'text/javascript; charset=utf-8',
            '.css': 'text/css; charset=utf-8',
        }.get(path.suffix, 'application/octet-stream')
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self):
        gateway = self.server.app.gateway
        if self.path == '/api/state':
            self._send_json(gateway.state())
            return
        if self.path == '/api/summary':
            self._send_json(gateway.analytics.summary())
            return
        if self.path == '/api/meters':
            self._send_json(gateway.analytics.summary()['meters'])
            return
        if self.path == '/api/events':
            self._send_json(list(gateway.analytics.events)[-30:][::-1])
            return
        if self.path == '/api/topics':
            self._send_json({
                'topics': gateway.broker.topics(),
                'messages': gateway.broker.count(),
            })
            return
        if self.path in ('/', '/index.html'):
            self._send_file('index.html')
            return
        if self.path == '/app.js':
            self._send_file('app.js')
            return
        if self.path == '/styles.css':
            self._send_file('styles.css')
            return
        self.send_error(404)

    def do_POST(self):
        length = int(self.headers.get('Content-Length', 0))
        try:
            body = json.loads(self.rfile.read(length) or b'{}')
        except json.JSONDecodeError:
            self._send_json({'error': 'invalid JSON'}, 400)
            return
        gateway = self.server.app.gateway
        try:
            if self.path == '/api/inject':
                gateway.inject(body['meter_id'], **body['values'])
            elif self.path == '/api/clear':
                gateway.clear_injection(body.get('meter_id'))
            elif self.path == '/api/reset':
                gateway.reset()
            else:
                self.send_error(404)
                return
        except (KeyError, ValueError, TypeError) as error:
            self._send_json({'error': str(error)}, 400)
            return
        self._send_json(gateway.state())


def main():
    import argparse

    parser = argparse.ArgumentParser(description='IoT energy monitoring simulator')
    parser.add_argument('--port', type=int, default=4050)
    args = parser.parse_args()
    app = EnergyApplication(port=args.port).start()
    print(f'Energy dashboard: http://127.0.0.1:{app.port}')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        app.stop()


if __name__ == '__main__':
    main()
