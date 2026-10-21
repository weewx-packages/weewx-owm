import http.server
import json
import queue
import threading

import pytest
import weewx
import owm


def test_station_id_and_measurements_reach_local_receiver():
    received = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            received.append((self.path, self.headers['Content-Type'], json.loads(self.rfile.read(int(self.headers['Content-Length'])))))
            self.send_response(204)
            self.end_headers()

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1',0), Handler)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    try:
        worker = owm.OpenWeatherMapThread(queue.Queue(), 'local-key', 50, 8, 100, '583436dd9643a9000196b8d6', None, server_url='http://127.0.0.1:%d/measurements'%server.server_port)
        worker.process_record({'dateTime':1700000000,'usUnits':weewx.US,'outTemp':32,'windSpeed':0,'outHumidity':None},None)
        path, content, records = received[0]
        assert path == '/measurements?appid=local-key'
        assert content == 'application/json'
        assert records[0]['station_id'] == '583436dd9643a9000196b8d6'
        assert records[0]['temperature'] == pytest.approx(0)
        assert records[0]['wind_speed'] == 0
        assert 'humidity' not in records[0]
    finally:
        server.shutdown()
        thread.join()
        server.server_close()


def test_default_endpoint_uses_tls():
    assert owm.OpenWeatherMapThread._SERVER_URL.startswith('https://')
